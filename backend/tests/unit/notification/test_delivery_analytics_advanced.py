from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core import security
from src.apps.core.time import utc_now
from src.apps.notification.models.notification import Notification, NotificationType
from src.apps.notification.models.notification_delivery import (
    NotificationDelivery,
    NotificationDeliveryChannel,
    NotificationDeliveryEvent,
    NotificationDeliveryEventType,
    NotificationFailureBucket,
    NotificationDeliveryStatus,
)
from src.apps.notification.services.delivery_analytics import (
    get_notification_delivery_analytics,
    normalize_delivery_failure,
    summarize_and_prune_delivery_events,
)
from tests.factories import UserFactory


async def _make_user(db: AsyncSession, **kwargs):
    defaults = dict(
        username="notifadv",
        email="notifadv@example.com",
        hashed_password=security.get_password_hash("TestPass123"),
        is_active=True,
        is_confirmed=True,
        is_superuser=True,
    )
    defaults.update(kwargs)
    user = UserFactory.build(**defaults)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, username: str, password: str = "TestPass123") -> str:
    resp = await client.post(
        "/api/v1/auth/login/?set_cookie=false",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access"]


@pytest.mark.asyncio
async def test_failure_taxonomy_normalization():
    code, bucket = normalize_delivery_failure(code="429", reason="Provider rate limited")
    assert code == "rate_limited"
    assert bucket.value == "rate_limited"

    code2, bucket2 = normalize_delivery_failure(code="503", reason="Service unavailable")
    assert code2 == "provider_unavailable"
    assert bucket2.value == "provider_outage"


@pytest.mark.asyncio
async def test_advanced_delivery_analytics_include_p95_retry_and_failure_buckets(db_session: AsyncSession):
    user = await _make_user(db_session, username="notifadv2", email="notifadv2@example.com")
    note = Notification(user_id=user.id, title="Metrics", body="Body", type=NotificationType.INFO)
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    queued = utc_now() - timedelta(minutes=5)
    deliveries = [
        NotificationDelivery(
            notification_id=note.id,
            user_id=user.id,
            channel=NotificationDeliveryChannel.EMAIL,
            status=NotificationDeliveryStatus.DELIVERED,
            target="user:a",
            dedup_key="adv-1",
            provider="resend",
            attempt_count=1,
            queued_at=queued,
            delivered_at=queued + timedelta(seconds=1),
        ),
        NotificationDelivery(
            notification_id=note.id,
            user_id=user.id,
            channel=NotificationDeliveryChannel.EMAIL,
            status=NotificationDeliveryStatus.DELIVERED,
            target="user:b",
            dedup_key="adv-2",
            provider="resend",
            attempt_count=3,
            queued_at=queued,
            delivered_at=queued + timedelta(seconds=4),
        ),
        NotificationDelivery(
            notification_id=note.id,
            user_id=user.id,
            channel=NotificationDeliveryChannel.SMS,
            status=NotificationDeliveryStatus.DEAD_LETTER,
            target="user:c",
            dedup_key="adv-3",
            provider="twilio",
            attempt_count=3,
            queued_at=queued,
        ),
    ]
    db_session.add_all(deliveries)
    await db_session.commit()
    for delivery in deliveries:
        await db_session.refresh(delivery)

    db_session.add(
        NotificationDeliveryEvent(
            delivery_id=deliveries[2].id,
            notification_id=note.id,
            user_id=user.id,
            channel=NotificationDeliveryChannel.SMS,
            event_type=NotificationDeliveryEventType.DEAD_LETTERED,
            status_before=NotificationDeliveryStatus.FAILED,
            status_after=NotificationDeliveryStatus.DEAD_LETTER,
            provider="twilio",
            provider_response_code="429",
            normalized_error_code="rate_limited",
            failure_bucket=NotificationFailureBucket.RATE_LIMITED,
            error_reason="provider throttled",
            attempt_count=3,
        )
    )
    await db_session.commit()

    result = await get_notification_delivery_analytics(db_session)
    assert result["total"] == 3
    assert result["delivered"] == 2
    assert result["failed"] == 1
    assert result["p95_latency_ms"] >= 1000
    assert result["retry_success_curve"]
    assert result["failure_root_causes"][0]["bucket"] == "rate_limited"


@pytest.mark.asyncio
async def test_dashboard_api_and_retention_policy(client: AsyncClient, db_session: AsyncSession):
    admin = await _make_user(db_session, username="notifadvadmin", email="notifadvadmin@example.com")
    token = await _login(client, admin.username)
    headers = {"Authorization": f"Bearer {token}"}

    note = Notification(user_id=admin.id, title="Old", body="Event", type=NotificationType.SYSTEM)
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    delivery = NotificationDelivery(
        notification_id=note.id,
        user_id=admin.id,
        channel=NotificationDeliveryChannel.EMAIL,
        status=NotificationDeliveryStatus.DELIVERED,
        target="user:retention",
        dedup_key="retention-key",
        provider="resend",
    )
    db_session.add(delivery)
    await db_session.commit()
    await db_session.refresh(delivery)

    old_event = NotificationDeliveryEvent(
        delivery_id=delivery.id,
        notification_id=note.id,
        user_id=admin.id,
        channel=NotificationDeliveryChannel.EMAIL,
        event_type=NotificationDeliveryEventType.DELIVERED,
        status_before=NotificationDeliveryStatus.SENT,
        status_after=NotificationDeliveryStatus.DELIVERED,
        provider="resend",
        attempt_count=1,
        latency_ms=42,
        event_metadata_json={"template": "system"},
        occurred_at=utc_now() - timedelta(days=45),
    )
    db_session.add(old_event)
    await db_session.commit()

    dashboard_resp = await client.get("/api/v1/analytics/notifications/delivery/dashboard", headers=headers)
    assert dashboard_resp.status_code == 200, dashboard_resp.text
    assert "comparison" in dashboard_resp.json()
    assert "drilldowns" in dashboard_resp.json()

    retention_resp = await client.post("/api/v1/analytics/notifications/delivery/events/retention", headers=headers)
    assert retention_resp.status_code == 200, retention_resp.text
    payload = retention_resp.json()
    assert payload["pruned_events"] >= 1

    retention_result = await summarize_and_prune_delivery_events(db_session)
    assert retention_result["pruned_events"] >= 0
