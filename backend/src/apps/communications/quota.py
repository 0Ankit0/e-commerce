from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.communications.models import ChannelQuotaPolicy, ChannelQuotaUsage, QuotaScope
from src.apps.core.time import utc_now


class QuotaExceededError(Exception):
    def __init__(self, *, retry_after_seconds: int, violated_policy_ids: list[int], detail: str) -> None:
        super().__init__(detail)
        self.retry_after_seconds = retry_after_seconds
        self.violated_policy_ids = violated_policy_ids
        self.detail = detail


@dataclass
class QuotaContext:
    tenant_id: int | None = None
    user_id: int | None = None
    channel: str = "sms"


@dataclass
class UsageSnapshot:
    policy_id: int
    usage_count: int
    limit_count: int
    window_start: datetime
    window_end: datetime


@dataclass
class QuotaEvaluation:
    snapshots: list[UsageSnapshot]
    violations: list[UsageSnapshot]
    now: datetime


def _window_bounds(*, now: datetime, window_seconds: int, timezone_name: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone)
    local_epoch = datetime(1970, 1, 1, tzinfo=zone)
    elapsed = (local_now - local_epoch).total_seconds()
    bucket_index = floor(elapsed / window_seconds)
    bucket_start_local = local_epoch + timedelta(seconds=bucket_index * window_seconds)
    bucket_end_local = bucket_start_local + timedelta(seconds=window_seconds)
    return bucket_start_local.astimezone(UTC), bucket_end_local.astimezone(UTC)


async def list_matching_policies(db: AsyncSession, *, context: QuotaContext) -> list[ChannelQuotaPolicy]:
    query = (
        select(ChannelQuotaPolicy)
        .where(ChannelQuotaPolicy.channel == context.channel)
        .where(ChannelQuotaPolicy.enabled.is_(True))
    )
    tenant_match = ChannelQuotaPolicy.tenant_id.is_(None)
    user_match = ChannelQuotaPolicy.user_id.is_(None)
    if context.tenant_id is not None:
        tenant_match = or_(ChannelQuotaPolicy.tenant_id.is_(None), ChannelQuotaPolicy.tenant_id == context.tenant_id)
    if context.user_id is not None:
        user_match = or_(ChannelQuotaPolicy.user_id.is_(None), ChannelQuotaPolicy.user_id == context.user_id)
    query = query.where(tenant_match).where(user_match)
    rows = (await db.execute(query.order_by(ChannelQuotaPolicy.window_seconds.asc()))).scalars().all()
    return list(rows)


def _retry_after_seconds(*, violations: list[UsageSnapshot], now: datetime) -> int:
    return max(1, min(int((item.window_end - now).total_seconds()) for item in violations))


async def evaluate_quota(
    db: AsyncSession,
    *,
    context: QuotaContext,
    increment: int = 1,
    now: datetime | None = None,
) -> QuotaEvaluation:
    current = now or utc_now()
    policies = await list_matching_policies(db, context=context)
    if not policies:
        return QuotaEvaluation(snapshots=[], violations=[], now=current)

    snapshots: list[UsageSnapshot] = []
    violations: list[UsageSnapshot] = []

    for policy in policies:
        window_start, window_end = _window_bounds(
            now=current,
            window_seconds=policy.window_seconds,
            timezone_name=policy.timezone,
        )
        usage = (
            (
                await db.execute(
                    select(ChannelQuotaUsage)
                    .where(ChannelQuotaUsage.policy_id == policy.id)
                    .where(ChannelQuotaUsage.window_start == window_start)
                )
            )
            .scalars()
            .first()
        )
        projected = (usage.usage_count if usage else 0) + increment
        snapshot = UsageSnapshot(
            policy_id=int(policy.id),
            usage_count=projected,
            limit_count=policy.limit_count,
            window_start=window_start,
            window_end=window_end,
        )
        snapshots.append(snapshot)
        if projected > policy.limit_count:
            violations.append(snapshot)

    return QuotaEvaluation(snapshots=snapshots, violations=violations, now=current)


async def enforce_and_record_quota(
    db: AsyncSession,
    *,
    context: QuotaContext,
    increment: int = 1,
    now: datetime | None = None,
) -> list[UsageSnapshot]:
    current = now or utc_now()
    policies = await list_matching_policies(db, context=context)
    if not policies:
        return []

    snapshots: list[UsageSnapshot] = []
    violations: list[UsageSnapshot] = []

    for policy in policies:
        window_start, window_end = _window_bounds(
            now=current,
            window_seconds=policy.window_seconds,
            timezone_name=policy.timezone,
        )
        usage = (
            (
                await db.execute(
                    select(ChannelQuotaUsage)
                    .where(ChannelQuotaUsage.policy_id == policy.id)
                    .where(ChannelQuotaUsage.window_start == window_start)
                    .with_for_update()
                )
            )
            .scalars()
            .first()
        )
        if usage is None:
            try:
                async with db.begin_nested():
                    usage = ChannelQuotaUsage(
                        policy_id=int(policy.id),
                        window_start=window_start,
                        window_end=window_end,
                        usage_count=0,
                    )
                    db.add(usage)
                    await db.flush()
            except IntegrityError:
                usage = (
                    (
                        await db.execute(
                            select(ChannelQuotaUsage)
                            .where(ChannelQuotaUsage.policy_id == policy.id)
                            .where(ChannelQuotaUsage.window_start == window_start)
                            .with_for_update()
                        )
                    )
                    .scalars()
                    .first()
                )
        if usage is None:
            continue

        projected = usage.usage_count + increment
        snapshot = UsageSnapshot(
            policy_id=int(policy.id),
            usage_count=projected,
            limit_count=policy.limit_count,
            window_start=window_start,
            window_end=window_end,
        )
        snapshots.append(snapshot)
        if projected > policy.limit_count:
            violations.append(snapshot)

    if violations:
        raise QuotaExceededError(
            retry_after_seconds=_retry_after_seconds(violations=violations, now=current),
            violated_policy_ids=[item.policy_id for item in violations],
            detail="SMS quota exceeded",
        )

    for snapshot in snapshots:
        usage_row = (
            (
                await db.execute(
                    select(ChannelQuotaUsage)
                    .where(ChannelQuotaUsage.policy_id == snapshot.policy_id)
                    .where(ChannelQuotaUsage.window_start == snapshot.window_start)
                    .with_for_update()
                )
            )
            .scalars()
            .first()
        )
        if usage_row is None:
            continue
        usage_row.usage_count = snapshot.usage_count
        usage_row.updated_at = current
        db.add(usage_row)

    await db.flush()
    return snapshots


def derive_scope(*, tenant_id: int | None, user_id: int | None) -> QuotaScope:
    if tenant_id is not None and user_id is not None:
        return QuotaScope.TENANT_USER
    if tenant_id is not None:
        return QuotaScope.TENANT
    if user_id is not None:
        return QuotaScope.USER
    return QuotaScope.GLOBAL
