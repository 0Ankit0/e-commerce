from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.communications.models import ChannelQuotaOverrideAudit, ChannelQuotaPolicy, QuotaScope
from src.apps.communications.quota import QuotaContext, QuotaExceededError, enforce_and_record_quota


@pytest.mark.asyncio
async def test_sms_quota_exhaustion(db_session: AsyncSession) -> None:
    policy = ChannelQuotaPolicy(
        channel="sms",
        scope=QuotaScope.GLOBAL,
        limit_count=2,
        window_seconds=60,
        timezone="UTC",
        enabled=True,
    )
    db_session.add(policy)
    await db_session.commit()

    now = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)
    await enforce_and_record_quota(db_session, context=QuotaContext(channel="sms"), now=now)
    await enforce_and_record_quota(db_session, context=QuotaContext(channel="sms"), now=now + timedelta(seconds=1))

    with pytest.raises(QuotaExceededError) as exc:
        await enforce_and_record_quota(db_session, context=QuotaContext(channel="sms"), now=now + timedelta(seconds=2))

    assert exc.value.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_sms_quota_resets_after_window(db_session: AsyncSession) -> None:
    policy = ChannelQuotaPolicy(
        channel="sms",
        scope=QuotaScope.GLOBAL,
        limit_count=1,
        window_seconds=60,
        timezone="UTC",
        enabled=True,
    )
    db_session.add(policy)
    await db_session.commit()

    start = datetime(2026, 4, 9, 10, 0, 30, tzinfo=UTC)
    await enforce_and_record_quota(db_session, context=QuotaContext(channel="sms"), now=start)

    with pytest.raises(QuotaExceededError):
        await enforce_and_record_quota(db_session, context=QuotaContext(channel="sms"), now=start + timedelta(seconds=20))

    await enforce_and_record_quota(db_session, context=QuotaContext(channel="sms"), now=start + timedelta(seconds=70))


@pytest.mark.asyncio
async def test_quota_override_writes_audit_log(db_session: AsyncSession) -> None:
    policy = ChannelQuotaPolicy(
        channel="sms",
        scope=QuotaScope.GLOBAL,
        limit_count=1,
        window_seconds=60,
        timezone="UTC",
        enabled=True,
    )
    db_session.add(policy)
    await db_session.commit()
    await db_session.refresh(policy)

    audit = ChannelQuotaOverrideAudit(
        policy_id=policy.id,
        actor_user_id=None,
        action="manual_override",
        reason="incident response",
        before_json={"limit_count": 1},
        after_json={"limit_count": 10},
        metadata_json={"ticket": "INC-42"},
    )
    db_session.add(audit)
    await db_session.commit()

    rows = (await db_session.execute(select(ChannelQuotaOverrideAudit).where(ChannelQuotaOverrideAudit.policy_id == policy.id))).scalars().all()
    assert len(rows) == 1
    assert rows[0].reason == "incident response"
