"""SMS delivery helpers with configurable quota enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor

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
    ip_address: str | None = None
    provider: str = "default"
    privileged_override: bool = False


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
    ip_address: str | None,
    window_start: datetime,
    window_end: datetime,
    increment: int = 1,
) -> SmsQuotaCounter:
    counter = (
        (
            await db.execute(
                select(SmsQuotaCounter)
                .where(SmsQuotaCounter.counter_key == counter_key)
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )
    if counter is None:
        try:
            async with db.begin_nested():
                counter = SmsQuotaCounter(
                    counter_key=counter_key,
                    scope=scope,
                    provider=provider,
                    user_id=user_id,
                    ip_address=ip_address,
                    window_start=window_start,
                    window_end=window_end,
                    usage_count=0,
                )
                db.add(counter)
                await db.flush()
        except IntegrityError:
            counter = (
                (
                    await db.execute(
                        select(SmsQuotaCounter)
                        .where(SmsQuotaCounter.counter_key == counter_key)
                        .with_for_update()
                    )
                )
                .scalars()
                .first()
            )
    if counter is None:
        raise RuntimeError("failed to lock quota counter")
    counter.usage_count += increment
    counter.updated_at = utc_now()
    db.add(counter)
    await db.flush()
    return counter


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
    ip_address: str | None,
    provider: str,
    override_applied: bool,
    reason: str,
) -> None:
    db.add(
        SmsQuotaViolationEvent(
            config_id=config.id,
            scope=scope,
            provider=provider,
            user_id=user_id,
            ip_address=ip_address,
            limit_count=limit_count,
            attempted_count=attempted_count,
            window_start=window_start,
            window_end=window_end,
            override_applied=override_applied,
            reason=reason,
        )
    )
    await db.flush()


async def enforce_sms_quota(
    db: AsyncSession,
    *,
    context: SmsQuotaCheckContext,
    increment: int = 1,
    now: datetime | None = None,
) -> None:
    current = now or utc_now()
    config = await get_or_create_quota_config(db, provider=context.provider)

    checks: list[tuple[str, int, str, datetime, datetime, int | None, str | None]] = []
    daily_start, daily_end = _daily_bounds(current)

    if config.per_user_daily_limit is not None and context.user_id is not None:
        checks.append(
            (
                "user_daily",
                config.per_user_daily_limit,
                f"user:{context.user_id}:{daily_start.date().isoformat()}",
                daily_start,
                daily_end,
                context.user_id,
                None,
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
                context.ip_address,
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
            )
        )

    for scope, limit_count, counter_key, window_start, window_end, user_id, ip_address in checks:
        counter = await _increment_counter(
            db,
            counter_key=counter_key,
            scope=scope,
            provider=context.provider,
            user_id=user_id,
            ip_address=ip_address,
            window_start=window_start,
            window_end=window_end,
            increment=increment,
        )
        if counter.usage_count > limit_count:
            override = bool(context.privileged_override and config.privileged_override_enabled)
            await _record_violation(
                db,
                config=config,
                scope=scope,
                attempted_count=counter.usage_count,
                limit_count=limit_count,
                window_start=window_start,
                window_end=window_end,
                user_id=context.user_id,
                ip_address=context.ip_address,
                provider=context.provider,
                override_applied=override,
                reason="privileged_override" if override else "quota_exceeded",
            )
            if not override:
                raise SmsQuotaExceededError(
                    scope=scope,
                    retry_after_seconds=max(1, int((window_end - current).total_seconds())),
                    limit_count=limit_count,
                    attempted_count=counter.usage_count,
                )


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
