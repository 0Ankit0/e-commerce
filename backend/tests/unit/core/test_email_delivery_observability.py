import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core import security
from src.apps.communications.delivery_observability import create_queued_message, reconcile_webhook_event
from src.apps.communications.models import EmailMessageLifecycleStatus
from tests.factories import UserFactory


async def _make_user(db: AsyncSession, **kwargs):
    defaults = dict(
        username="sysadmin",
        email="sysadmin@example.com",
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
async def test_reconcile_webhook_deduplicates_and_ignores_out_of_order(db_session):
    message = await create_queued_message(
        db_session,
        subject="Subject",
        template_name="welcome",
        recipients=[{"email": "a@example.com", "name": "A"}],
        context={"x": 1},
        max_attempts=3,
    )
    message.provider = "resend"
    message.provider_message_id = "msg_1"
    message.status = EmailMessageLifecycleStatus.SENT
    db_session.add(message)
    await db_session.commit()

    delivered_event, duplicate = await reconcile_webhook_event(
        db_session,
        provider="resend",
        provider_event_id="evt_1",
        provider_message_id="msg_1",
        status=EmailMessageLifecycleStatus.DELIVERED,
        occurred_at=None,
        payload={"status": "delivered"},
        failure_reason=None,
    )
    assert duplicate is False
    assert delivered_event.out_of_order is False

    # Out-of-order event should not roll status back from delivered to sent
    out_of_order_event, duplicate = await reconcile_webhook_event(
        db_session,
        provider="resend",
        provider_event_id="evt_2",
        provider_message_id="msg_1",
        status=EmailMessageLifecycleStatus.SENT,
        occurred_at=None,
        payload={"status": "sent"},
        failure_reason=None,
    )
    assert duplicate is False
    assert out_of_order_event.out_of_order is True

    # Retry from provider with same event id should be deduplicated
    duplicate_event, duplicate = await reconcile_webhook_event(
        db_session,
        provider="resend",
        provider_event_id="evt_2",
        provider_message_id="msg_1",
        status=EmailMessageLifecycleStatus.SENT,
        occurred_at=None,
        payload={"status": "sent"},
        failure_reason=None,
    )
    assert duplicate is True
    assert duplicate_event.duplicate is True


@pytest.mark.asyncio
async def test_email_webhook_endpoint_normalizes_provider_statuses(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, username="webhookadmin", email="webhookadmin@example.com")
    token = await _login(client, "webhookadmin")
    headers = {"Authorization": f"Bearer {token}"}

    message = await create_queued_message(
        db_session,
        subject="Subject",
        template_name="welcome",
        recipients=[{"email": "a@example.com", "name": "A"}],
        context={"x": 1},
        max_attempts=3,
    )
    message.provider = "resend"
    message.provider_message_id = "msg_provider_1"
    db_session.add(message)
    await db_session.commit()

    response = await client.post(
        "/api/v1/system/webhooks/email/resend/",
        headers=headers,
        json={
            "event_id": "evt_provider_1",
            "message_id": "msg_provider_1",
            "status": "hard_bounced",
            "payload": {"status": "hard_bounced"},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["out_of_order"] is False


@pytest.mark.asyncio
async def test_email_webhook_endpoint_marks_duplicates_and_out_of_order(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, username="dedupeadmin", email="dedupeadmin@example.com")
    token = await _login(client, "dedupeadmin")
    headers = {"Authorization": f"Bearer {token}"}

    message = await create_queued_message(
        db_session,
        subject="Status flow",
        template_name="welcome",
        recipients=[{"email": "flow@example.com", "name": "Flow"}],
        context={"x": 2},
        max_attempts=3,
    )
    message.provider = "resend"
    message.provider_message_id = "msg_flow_1"
    message.status = EmailMessageLifecycleStatus.SENT
    db_session.add(message)
    await db_session.commit()

    delivered = await client.post(
        "/api/v1/system/webhooks/email/resend/",
        headers=headers,
        json={
            "event_id": "evt_flow_delivered",
            "message_id": "msg_flow_1",
            "status": "delivered",
            "payload": {"status": "delivered"},
        },
    )
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["out_of_order"] is False

    out_of_order = await client.post(
        "/api/v1/system/webhooks/email/resend/",
        headers=headers,
        json={
            "event_id": "evt_flow_sent",
            "message_id": "msg_flow_1",
            "status": "sent",
            "payload": {"status": "sent"},
        },
    )
    assert out_of_order.status_code == 200, out_of_order.text
    assert out_of_order.json()["duplicate"] is False
    assert out_of_order.json()["out_of_order"] is True

    duplicate = await client.post(
        "/api/v1/system/webhooks/email/resend/",
        headers=headers,
        json={
            "event_id": "evt_flow_sent",
            "message_id": "msg_flow_1",
            "status": "sent",
            "payload": {"status": "sent"},
        },
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["duplicate"] is True
