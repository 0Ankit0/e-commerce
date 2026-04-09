import pytest

from src.apps.communications.delivery_observability import create_queued_message, reconcile_webhook_event
from src.apps.communications.models import EmailMessageLifecycleStatus


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
