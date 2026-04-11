import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import select

from src.apps.notification.models.sms_quota import SmsQuotaConfig, SmsQuotaCounter, SmsQuotaViolationEvent
from src.apps.notification.services.sms_service import SmsQuotaCheckContext, SmsQuotaExceededError, enforce_sms_quota


@pytest.mark.asyncio
async def test_enforces_user_ip_and_provider_caps(db_session: AsyncSession) -> None:
    db_session.add(
        SmsQuotaConfig(
            provider="default",
            per_user_daily_limit=1,
            per_ip_window_limit=1,
            ip_window_seconds=300,
            global_provider_daily_limit=5,
        )
    )
    await db_session.commit()

    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    await enforce_sms_quota(db_session, context=SmsQuotaCheckContext(user_id=42, ip_address="1.1.1.1"), now=now)

    with pytest.raises(SmsQuotaExceededError) as exc:
        await enforce_sms_quota(db_session, context=SmsQuotaCheckContext(user_id=42, ip_address="2.2.2.2"), now=now)

    assert exc.value.scope == "user_daily"


@pytest.mark.asyncio
async def test_quota_rollover_uses_new_window(db_session: AsyncSession) -> None:
    db_session.add(SmsQuotaConfig(provider="default", per_user_daily_limit=1, per_ip_window_limit=None, global_provider_daily_limit=None))
    await db_session.commit()

    await enforce_sms_quota(
        db_session,
        context=SmsQuotaCheckContext(user_id=7),
        now=datetime(2026, 4, 10, 23, 59, tzinfo=UTC),
    )
    await enforce_sms_quota(
        db_session,
        context=SmsQuotaCheckContext(user_id=7),
        now=datetime(2026, 4, 11, 0, 0, tzinfo=UTC),
    )

    counters = (await db_session.execute(select(SmsQuotaCounter).where(SmsQuotaCounter.scope == "user_daily"))).scalars().all()
    assert len(counters) == 2


@pytest.mark.asyncio
async def test_race_condition_allows_only_one_at_limit(db_session: AsyncSession) -> None:
    db_session.add(SmsQuotaConfig(provider="default", per_user_daily_limit=1, per_ip_window_limit=None, global_provider_daily_limit=None))
    await db_session.commit()
    now = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)

    maker = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def _attempt() -> str:
        async with maker() as worker:
            try:
                await enforce_sms_quota(worker, context=SmsQuotaCheckContext(user_id=999), now=now)
                await worker.commit()
                return "allowed"
            except SmsQuotaExceededError:
                await worker.rollback()
                return "blocked"

    outcomes = await asyncio.gather(_attempt(), _attempt())
    assert outcomes.count("allowed") == 1
    assert outcomes.count("blocked") == 1


@pytest.mark.asyncio
async def test_privileged_override_records_violation_event(db_session: AsyncSession) -> None:
    db_session.add(
        SmsQuotaConfig(
            provider="default",
            per_user_daily_limit=1,
            per_ip_window_limit=None,
            global_provider_daily_limit=None,
            privileged_override_enabled=True,
        )
    )
    await db_session.commit()

    now = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)
    await enforce_sms_quota(db_session, context=SmsQuotaCheckContext(user_id=22), now=now)
    await enforce_sms_quota(
        db_session,
        context=SmsQuotaCheckContext(user_id=22, privileged_override=True),
        now=now,
    )

    events = (await db_session.execute(select(SmsQuotaViolationEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].override_applied is True
