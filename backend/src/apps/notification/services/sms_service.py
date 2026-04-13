"""SMS delivery helpers with configurable quota enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from hashlib import sha256

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from src.apps.communications import get_communications_service
from src.apps.core.time import utc_now
from src.apps.notification.models.sms_quota import SmsQuotaConfig, SmsQuotaCounter, SmsQuotaViolationEvent


class SmsQuotaExceededError(Exception):
    def __init__(
        self,
        *,
        scope: str,
        retry_after_seconds: int,
        limit_count: int,
        attempted_count: int,
    ) -> None:
        self.scope = scope
        self.retry_after_seconds = retry_after_seconds
        self.limit_count = limit_count
        self.attempted_count = attempted_count
        super().__init__(f"SMS quota exceeded for scope={scope}")


@dataclass
class SmsQuotaCheckContext:
    user_id: int | None = None
    tenant_id: int | None = None
    ip_address: str | None = None
    device_fingerprint: str | None = None
    phone_number: str | None = None
    provider: str = "default"
    entry_point: str = "transactional_sms"
    privileged_override: bool = False
    trusted_flow: bool = False


@dataclass
class SmsQuotaDecision:
    allowed: bool = True
    blocked: bool = False
    challenge_required: bool = False
    delay_seconds: int = 0
    scope: str | None = None
    severity: str | None = None
    action: str | None = None
    cooldown_until: datetime | None = None


@dataclass
class SmsQuotaCounterReservation:
    usage_count: int
    attempted_count: int
    allowed: bool


def _daily_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    return start, start + timedelta(days=1)


def _window_bounds(now: datetime, window_seconds: int) -> tuple[datetime, datetime]:
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    elapsed = (now - epoch).total_seconds()
    bucket_index = floor(elapsed / window_seconds)
    start = epoch + timedelta(seconds=bucket_index * window_seconds)
    return start, start + timedelta(seconds=window_seconds)


async def get_or_create_quota_config(db: AsyncSession, *, provider: str = "default") -> SmsQuotaConfig:
    row = (
        await db.execute(
            select(SmsQuotaConfig)
            .where(SmsQuotaConfig.provider == provider)
            .order_by(SmsQuotaConfig.updated_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if row is not None:
        return row
    row = SmsQuotaConfig(provider=provider)
    db.add(row)
    await db.flush()
    return row


async def _increment_counter(
    db: AsyncSession,
    *,
    counter_key: str,
    scope: str,
    provider: str | None,
    user_id: int | None,
    tenant_id: int | None,
    ip_address: str | None,
    phone_number_hash: str | None,
    device_fingerprint_hash: str | None,
    window_start: datetime,
    window_end: datetime,
    limit_count: int,
    increment: int = 1,
) -> SmsQuotaCounterReservation:
    updated_at = utc_now()

    updated = await db.execute(
        update(SmsQuotaCounter)
        .where(
            SmsQuotaCounter.counter_key == counter_key,
            SmsQuotaCounter.usage_count + increment <= limit_count,
        )
        .values(usage_count=SmsQuotaCounter.usage_count + increment, updated_at=updated_at)
    )
    if updated.rowcount:
        current_count = (
            await db.execute(
                select(SmsQuotaCounter.usage_count).where(SmsQuotaCounter.counter_key == counter_key)
            )
        ).scalar_one()
        return SmsQuotaCounterReservation(
            usage_count=int(current_count),
            attempted_count=int(current_count),
            allowed=True,
        )

    if increment <= limit_count:
        try:
            async with db.begin_nested():
                db.add(
                    SmsQuotaCounter(
                        counter_key=counter_key,
                        scope=scope,
                        provider=provider,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        ip_address=ip_address,
                        phone_number_hash=phone_number_hash,
                        device_fingerprint_hash=device_fingerprint_hash,
                        window_start=window_start,
                        window_end=window_end,
                        usage_count=increment,
                        updated_at=updated_at,
                    )
                )
                await db.flush()
            return SmsQuotaCounterReservation(
                usage_count=increment,
                attempted_count=increment,
                allowed=True,
            )
        except IntegrityError:
            pass

    current_count = (
        await db.execute(select(SmsQuotaCounter.usage_count).where(SmsQuotaCounter.counter_key == counter_key))
    ).scalar_one_or_none()
    usage_count = int(current_count or 0)
    return SmsQuotaCounterReservation(
        usage_count=usage_count,
        attempted_count=usage_count + increment,
        allowed=False,
    )


async def _record_violation(
    db: AsyncSession,
    *,
    config: SmsQuotaConfig,
    scope: str,
    attempted_count: int,
    limit_count: int,
    window_start: datetime,
    window_end: datetime,
    user_id: int | None,
    tenant_id: int | None,
    ip_address: str | None,
    phone_number_hash: str | None,
    device_fingerprint_hash: str | None,
    provider: str,
    override_applied: bool,
    severity: str,
    throttle_action: str,
    delay_seconds: int,
    reason: str,
    cooldown_until: datetime | None,
) -> None:
    db.add(
        SmsQuotaViolationEvent(
            config_id=config.id,
            scope=scope,
            provider=provider,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            phone_number_hash=phone_number_hash,
            device_fingerprint_hash=device_fingerprint_hash,
            limit_count=limit_count,
            attempted_count=attempted_count,
            window_start=window_start,
            window_end=window_end,
            override_applied=override_applied,
            severity=severity,
            throttle_action=throttle_action,
            delay_seconds=delay_seconds,
            cooldown_until=cooldown_until,
            reason=reason,
            metadata_json={
                "action": throttle_action,
                "delay_seconds": delay_seconds,
                "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
            },
        )
    )
    await db.flush()


async def enforce_sms_quota(
    db: AsyncSession,
    *,
    context: SmsQuotaCheckContext,
    increment: int = 1,
    now: datetime | None = None,
) -> SmsQuotaDecision:
    current = now or utc_now()
    config = await get_or_create_quota_config(db, provider=context.provider)
    decision = SmsQuotaDecision()

    daily_start, daily_end = _daily_bounds(current)
    phone_hash = sha256((context.phone_number or "").encode("utf-8")).hexdigest() if context.phone_number else None
    device_hash = sha256((context.device_fingerprint or "").encode("utf-8")).hexdigest() if context.device_fingerprint else None
    trusted_entries = set((config.trusted_entry_points_json or {}).get("allow", []))
    trusted_context = context.trusted_flow or context.entry_point in trusted_entries
    checks: list[tuple[str, int, str, datetime, datetime, int | None, int | None, str | None, str | None, str | None, str]] = []

    if config.per_user_daily_limit is not None and context.user_id is not None:
        checks.append(
            (
                "user_daily",
                config.per_user_daily_limit,
                f"user:{context.user_id}:{daily_start.date().isoformat()}",
                daily_start,
                daily_end,
                context.user_id,
                context.tenant_id,
                None,
                None,
                None,
                "hard",
            )
        )
    if config.per_tenant_daily_limit is not None and context.tenant_id is not None:
        checks.append(
            (
                "tenant_daily",
                config.per_tenant_daily_limit,
                f"tenant:{context.tenant_id}:{daily_start.date().isoformat()}",
                daily_start,
                daily_end,
                None,
                context.tenant_id,
                None,
                None,
                None,
                "hard",
            )
        )
    if config.per_phone_window_limit is not None and phone_hash:
        phone_start, phone_end = _window_bounds(current, config.phone_window_seconds)
        checks.append(
            (
                "phone_window",
                config.per_phone_window_limit,
                f"phone:{phone_hash}:{phone_start.isoformat()}:{config.phone_window_seconds}",
                phone_start,
                phone_end,
                None,
                None,
                None,
                phone_hash,
                None,
                "hard",
            )
        )

    if config.per_ip_window_limit is not None and context.ip_address:
        ip_start, ip_end = _window_bounds(current, config.ip_window_seconds)
        checks.append(
            (
                "ip_window",
                config.per_ip_window_limit,
                f"ip:{context.ip_address}:{ip_start.isoformat()}:{config.ip_window_seconds}",
                ip_start,
                ip_end,
                None,
                None,
                context.ip_address,
                None,
                None,
                "hard" if not trusted_context else "soft",
            )
        )

    if config.per_device_window_limit is not None and device_hash:
        device_start, device_end = _window_bounds(current, config.device_window_seconds)
        checks.append(
            (
                "device_window",
                config.per_device_window_limit,
                f"device:{device_hash}:{device_start.isoformat()}:{config.device_window_seconds}",
                device_start,
                device_end,
                None,
                None,
                None,
                None,
                device_hash,
                "hard",
            )
        )

    if config.global_provider_soft_daily_limit is not None:
        checks.append(
            (
                "provider_daily_soft",
                config.global_provider_soft_daily_limit,
                f"provider-soft:{context.provider}:{daily_start.date().isoformat()}",
                daily_start,
                daily_end,
                None,
                None,
                None,
                None,
                None,
                "soft",
            )
        )
    if config.global_provider_daily_limit is not None:
        checks.append(
            (
                "provider_daily",
                config.global_provider_daily_limit,
                f"provider:{context.provider}:{daily_start.date().isoformat()}",
                daily_start,
                daily_end,
                None,
                None,
                None,
                None,
                None,
                "hard" if not trusted_context else "soft",
            )
        )

    for (
        scope,
        limit_count,
        counter_key,
        window_start,
        window_end,
        user_id,
        tenant_id,
        ip_address,
        phone_number_hash,
        device_fingerprint_hash,
        severity,
    ) in checks:
        counter = await _increment_counter(
            db,
            counter_key=counter_key,
            scope=scope,
            provider=context.provider,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            phone_number_hash=phone_number_hash,
            device_fingerprint_hash=device_fingerprint_hash,
            window_start=window_start,
            window_end=window_end,
            limit_count=limit_count,
            increment=increment,
        )
        if not counter.allowed:
            action = config.hard_throttle_action if severity == "hard" else config.soft_throttle_action
            delay_seconds = config.hard_throttle_delay_seconds if severity == "hard" else config.soft_throttle_delay_seconds
            cooldown_until = (
                current + timedelta(seconds=config.hard_cooldown_seconds)
                if action == "cooldown" and config.hard_cooldown_seconds > 0
                else None
            )
            override = bool(context.privileged_override and config.privileged_override_enabled)
            await _record_violation(
                db,
                config=config,
                scope=scope,
                attempted_count=counter.attempted_count,
                limit_count=limit_count,
                window_start=window_start,
                window_end=window_end,
                user_id=context.user_id,
                tenant_id=context.tenant_id,
                ip_address=context.ip_address,
                phone_number_hash=phone_hash,
                device_fingerprint_hash=device_hash,
                provider=context.provider,
                override_applied=override,
                severity=severity,
                throttle_action=action,
                delay_seconds=delay_seconds,
                reason="privileged_override" if override else "quota_exceeded",
                cooldown_until=cooldown_until,
            )
            if override:
                return decision

            decision.allowed = action != "block"
            decision.blocked = action == "block"
            decision.challenge_required = action == "challenge"
            decision.delay_seconds = delay_seconds if action == "delay" else 0
            decision.scope = scope
            decision.severity = severity
            decision.action = action
            decision.cooldown_until = cooldown_until

            if action in {"block", "cooldown"}:
                retry_after = max(1, int((window_end - current).total_seconds()))
                if cooldown_until is not None:
                    retry_after = max(retry_after, int((cooldown_until - current).total_seconds()))
                raise SmsQuotaExceededError(
                    scope=scope,
                    retry_after_seconds=retry_after,
                    limit_count=limit_count,
                    attempted_count=counter.attempted_count,
                )
            return decision
    return decision


async def reset_sms_quota_counters(db: AsyncSession, *, provider: str | None = None) -> int:
    query = delete(SmsQuotaCounter)
    if provider:
        query = query.where(SmsQuotaCounter.provider == provider)
    result = await db.execute(query)
    await db.flush()
    return int(result.rowcount or 0)


def send_sms_notification(to_number: str, body: str) -> bool:
    result = get_communications_service().send_sms(to_number=to_number, body=body)
    return result.success
