from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core.time import utc_now

from .models import (
    EmailDeliveryDeadLetter,
    EmailDeliveryMessage,
    EmailDeliveryWebhookEvent,
    EmailMessageLifecycleStatus,
)

_STATUS_ORDER: dict[EmailMessageLifecycleStatus, int] = {
    EmailMessageLifecycleStatus.QUEUED: 0,
    EmailMessageLifecycleStatus.SENT: 1,
    EmailMessageLifecycleStatus.DELIVERED: 2,
    EmailMessageLifecycleStatus.FAILED: 3,
    EmailMessageLifecycleStatus.BOUNCED: 4,
    EmailMessageLifecycleStatus.COMPLAINED: 5,
}


def _is_out_of_order(current: EmailMessageLifecycleStatus, incoming: EmailMessageLifecycleStatus) -> bool:
    if current == EmailMessageLifecycleStatus.DELIVERED and incoming in {
        EmailMessageLifecycleStatus.BOUNCED,
        EmailMessageLifecycleStatus.COMPLAINED,
        EmailMessageLifecycleStatus.FAILED,
    }:
        return False
    return _STATUS_ORDER[incoming] < _STATUS_ORDER[current]


async def create_queued_message(
    db: AsyncSession,
    *,
    subject: str,
    template_name: str,
    recipients: list[dict[str, str]],
    context: dict[str, Any],
    max_attempts: int,
) -> EmailDeliveryMessage:
    msg = EmailDeliveryMessage(
        subject=subject,
        template_name=template_name,
        recipients_json=recipients,
        context_json=context,
        status=EmailMessageLifecycleStatus.QUEUED,
        max_attempts=max_attempts,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def record_send_attempt(
    db: AsyncSession,
    *,
    message: EmailDeliveryMessage,
    success: bool,
    provider: str,
    provider_message_id: str | None,
    metadata: dict[str, Any],
    error: str | None,
    failure_reason: str | None,
    attempt_count: int,
    next_attempt_at: datetime | None,
    dead_letter: bool,
) -> EmailDeliveryMessage:
    message.attempt_count = attempt_count
    message.last_attempt_at = utc_now()
    message.updated_at = utc_now()
    message.provider = provider
    message.provider_message_id = provider_message_id or message.provider_message_id
    message.provider_metadata_json = metadata or {}
    message.last_error_reason = error
    message.failure_reason = failure_reason
    message.next_attempt_at = next_attempt_at

    if success:
        message.status = EmailMessageLifecycleStatus.SENT
        message.sent_at = utc_now()
        message.finalized_at = None
        message.dead_lettered_at = None
        message.failure_reason = None
    elif dead_letter:
        message.status = EmailMessageLifecycleStatus.FAILED
        message.finalized_at = utc_now()
        message.dead_lettered_at = utc_now()
        dead = EmailDeliveryDeadLetter(
            message_id=message.id,
            reason=failure_reason or "permanent_failure",
            payload_json={
                "provider": provider,
                "provider_message_id": provider_message_id,
                "error": error,
                "attempt_count": attempt_count,
            },
        )
        db.add(dead)

    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def reconcile_webhook_event(
    db: AsyncSession,
    *,
    provider: str,
    provider_event_id: str,
    provider_message_id: str,
    status: EmailMessageLifecycleStatus,
    occurred_at: datetime | None,
    payload: dict[str, Any],
    failure_reason: str | None,
) -> tuple[EmailDeliveryWebhookEvent, bool]:
    existing = (
        await db.execute(
            select(EmailDeliveryWebhookEvent).where(
                EmailDeliveryWebhookEvent.provider == provider,
                EmailDeliveryWebhookEvent.provider_event_id == provider_event_id,
            )
        )
    ).scalars().first()

    if existing:
        existing.duplicate = True
        db.add(existing)
        await db.commit()
        return existing, True

    message = (
        await db.execute(
            select(EmailDeliveryMessage).where(
                EmailDeliveryMessage.provider == provider,
                EmailDeliveryMessage.provider_message_id == provider_message_id,
            )
        )
    ).scalars().first()

    out_of_order = False
    if message:
        out_of_order = _is_out_of_order(message.status, status)
        if not out_of_order:
            message.status = status
            message.updated_at = utc_now()
            message.provider_metadata_json = {**message.provider_metadata_json, "last_webhook": payload}
            if status == EmailMessageLifecycleStatus.DELIVERED:
                message.delivered_at = occurred_at or utc_now()
                message.finalized_at = occurred_at or utc_now()
                message.failure_reason = None
                message.last_error_reason = None
            elif status in {
                EmailMessageLifecycleStatus.FAILED,
                EmailMessageLifecycleStatus.BOUNCED,
                EmailMessageLifecycleStatus.COMPLAINED,
            }:
                message.finalized_at = occurred_at or utc_now()
                message.failure_reason = failure_reason or status.value
                if message.dead_lettered_at is None:
                    message.dead_lettered_at = utc_now()
                dead = EmailDeliveryDeadLetter(
                    message_id=message.id,
                    reason=message.failure_reason,
                    payload_json={"source": "webhook", "payload": payload},
                )
                db.add(dead)
            db.add(message)

    webhook = EmailDeliveryWebhookEvent(
        provider=provider,
        provider_event_id=provider_event_id,
        provider_message_id=provider_message_id,
        status=status,
        occurred_at=occurred_at or utc_now(),
        payload_json=payload,
        duplicate=False,
        out_of_order=out_of_order,
    )
    db.add(webhook)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        dup = (
            await db.execute(
                select(EmailDeliveryWebhookEvent).where(
                    EmailDeliveryWebhookEvent.provider == provider,
                    EmailDeliveryWebhookEvent.provider_event_id == provider_event_id,
                )
            )
        ).scalars().first()
        assert dup is not None
        dup.duplicate = True
        db.add(dup)
        await db.commit()
        return dup, True

    await db.refresh(webhook)
    return webhook, False


async def get_delivery_analytics(db: AsyncSession, *, from_dt: datetime | None, to_dt: datetime | None) -> dict[str, Any]:
    filters = []
    if from_dt:
        filters.append(col(EmailDeliveryMessage.created_at) >= from_dt)
    if to_dt:
        filters.append(col(EmailDeliveryMessage.created_at) <= to_dt)

    total_stmt = select(func.count()).select_from(EmailDeliveryMessage)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).one()[0]

    grouped_stmt = select(EmailDeliveryMessage.status, func.count()).group_by(EmailDeliveryMessage.status)
    if filters:
        grouped_stmt = grouped_stmt.where(*filters)
    grouped = {row[0].value: row[1] for row in (await db.execute(grouped_stmt)).all()}

    failed_stmt = select(EmailDeliveryMessage.failure_reason, func.count()).where(
        EmailDeliveryMessage.failure_reason.is_not(None)
    ).group_by(EmailDeliveryMessage.failure_reason).order_by(func.count().desc()).limit(10)
    if filters:
        failed_stmt = failed_stmt.where(*filters)
    reasons = [
        {"reason": reason or "unknown", "count": count}
        for reason, count in (await db.execute(failed_stmt)).all()
    ]

    delivered = grouped.get(EmailMessageLifecycleStatus.DELIVERED.value, 0)
    bounced = grouped.get(EmailMessageLifecycleStatus.BOUNCED.value, 0)
    failed = grouped.get(EmailMessageLifecycleStatus.FAILED.value, 0)
    complained = grouped.get(EmailMessageLifecycleStatus.COMPLAINED.value, 0)

    denom = max(total, 1)
    return {
        "total": total,
        "status_counts": grouped,
        "delivery_rate": delivered / denom,
        "bounce_rate": bounced / denom,
        "failure_rate": (failed + complained) / denom,
        "failure_reasons": reasons,
    }
