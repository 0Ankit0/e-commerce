"""Notification-specific Celery tasks (email copy, push, SMS)."""
import asyncio
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

from celery import shared_task
from sqlalchemy import select

from src.apps.core.celery_app import celery_app  # noqa: F401 — bind tasks to configured app
from src.apps.core.time import utc_now
from src.apps.notification.models.notification_delivery import (
    NotificationDelivery,
    NotificationDeliveryStatus,
)
from src.apps.notification.models.notification_device import NotificationDevice
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

NOTIFICATION_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")

RETRYABLE_ERROR_MARKERS = (
    "timeout",
    "temporarily",
    "503",
    "502",
    "connection",
    "unavailable",
    "rate limit",
)
INVALID_TOKEN_MARKERS = (
    "invalid registration",
    "invalid token",
    "unregistered",
    "notregistered",
)


@shared_task(name="send_notification_email_task")
def send_notification_email_task(
    recipients: List[Dict[str, str]],
    subject: str,
    context: Dict[str, Any],
) -> bool:
    from src.apps.core.tasks import send_email_task

    return send_email_task(
        subject=subject,
        recipients=recipients,
        template_name="notification",
        context=context,
        template_dir=NOTIFICATION_TEMPLATE_DIR,
    )


@shared_task(name="send_push_notification_task")
def send_push_notification_task(payload: Dict[str, Any]) -> bool:
    from src.apps.communications import get_communications_service

    result = get_communications_service().send_push(payload)
    return result.success


@shared_task(name="send_sms_notification_task")
def send_sms_notification_task(to_number: str, body: str) -> bool:
    from src.apps.communications import get_communications_service

    result = get_communications_service().send_sms(to_number=to_number, body=body)
    return result.success


@shared_task(bind=True, name="dispatch_notification_delivery_task")
def dispatch_notification_delivery_task(self, delivery_id: int) -> bool:
    return asyncio.run(_dispatch_notification_delivery(delivery_id))


async def _dispatch_notification_delivery(delivery_id: int) -> bool:
    from src.apps.communications import get_communications_service
    from src.apps.iam.models.user import User, UserProfile
    from src.apps.notification.models.notification import Notification
    from src.apps.notification.models.notification_preference import NotificationPreference
    from src.apps.multitenancy.models.tenant import TenantMember
    from src.apps.communications.quota import QuotaContext, QuotaExceededError, enforce_and_record_quota

    async with async_session_factory() as db:
        delivery = await db.get(NotificationDelivery, delivery_id)
        if not delivery:
            return True
        if delivery.status in {NotificationDeliveryStatus.DELIVERED, NotificationDeliveryStatus.DEAD_LETTER}:
            return True

        notification = await db.get(Notification, delivery.notification_id)
        if notification is None:
            delivery.status = NotificationDeliveryStatus.SKIPPED
            delivery.last_error_reason = "Notification no longer exists"
            delivery.updated_at = utc_now()
            db.add(delivery)
            await db.commit()
            return True

        pref = (
            await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == delivery.user_id))
        ).scalars().first()

        should_send = True
        if pref:
            if delivery.channel.value == "email":
                should_send = pref.email_enabled
            elif delivery.channel.value == "push":
                should_send = pref.push_enabled
            elif delivery.channel.value == "sms":
                should_send = pref.sms_enabled

        if not should_send:
            delivery.status = NotificationDeliveryStatus.SKIPPED
            delivery.last_error_reason = "Channel disabled by user preference"
            delivery.updated_at = utc_now()
            db.add(delivery)
            await db.commit()
            return True

        delivery.attempt_count = delivery.attempt_count + 1
        delivery.last_attempt_at = utc_now()
        delivery.updated_at = utc_now()
        db.add(delivery)
        await db.commit()

        try:
            comms = get_communications_service()
            if delivery.channel.value == "email":
                user = (await db.execute(select(User).where(User.id == delivery.user_id))).scalars().first()
                if not user:
                    raise RuntimeError("Email recipient user not found")
                result = comms.send_email(
                    subject=notification.title,
                    recipients=[{"name": user.username, "email": user.email}],
                    template_name="notification",
                    context={
                        "user": {"email": user.email, "first_name": user.username},
                        "notification": {
                            "title": notification.title,
                            "body": notification.body,
                            "type": notification.type,
                        },
                    },
                    template_dir=NOTIFICATION_TEMPLATE_DIR,
                )
            elif delivery.channel.value == "push":
                device_id = int(delivery.target.split(":", 1)[1]) if delivery.target and delivery.target.startswith("device:") else None
                device = await db.get(NotificationDevice, device_id) if device_id else None
                if not device or not device.is_active:
                    delivery.status = NotificationDeliveryStatus.SKIPPED
                    delivery.last_error_reason = "Target device no longer active"
                    delivery.updated_at = utc_now()
                    db.add(delivery)
                    await db.commit()
                    return True
                result = comms.send_push(
                    {
                        "provider": device.provider.value,
                        "platform": device.platform.value,
                        "title": notification.title,
                        "body": notification.body,
                        "data": notification.extra_data if isinstance(notification.extra_data, dict) else None,
                        "token": device.token,
                        "endpoint": device.endpoint,
                        "p256dh": device.p256dh,
                        "auth": device.auth,
                        "subscription_id": device.subscription_id,
                    }
                )
            elif delivery.channel.value == "sms":
                profile = (
                    await db.execute(select(UserProfile).where(UserProfile.user_id == delivery.user_id))
                ).scalars().first()
                if not profile or not profile.phone:
                    delivery.status = NotificationDeliveryStatus.SKIPPED
                    delivery.last_error_reason = "No phone number"
                    delivery.updated_at = utc_now()
                    db.add(delivery)
                    await db.commit()
                    return True
                membership = (
                    await db.execute(
                        select(TenantMember)
                        .where(TenantMember.user_id == delivery.user_id)
                        .where(TenantMember.is_active.is_(True))
                        .order_by(TenantMember.joined_at.asc())
                    )
                ).scalars().first()
                tenant_id = int(membership.tenant_id) if membership and membership.tenant_id is not None else None
                try:
                    await enforce_and_record_quota(
                        db,
                        context=QuotaContext(channel="sms", tenant_id=tenant_id, user_id=delivery.user_id),
                    )
                except QuotaExceededError as quota_exc:
                    delivery.status = NotificationDeliveryStatus.FAILED
                    delivery.last_error_code = "quota_exceeded"
                    delivery.last_error_reason = (
                        f"SMS quota exceeded. Retry after {quota_exc.retry_after_seconds} seconds "
                        f"(policies: {quota_exc.violated_policy_ids})."
                    )
                    delivery.next_attempt_at = utc_now() + timedelta(seconds=quota_exc.retry_after_seconds)
                    delivery.updated_at = utc_now()
                    db.add(delivery)
                    await db.commit()
                    return False

                result = comms.send_sms(to_number=profile.phone, body=f"{notification.title}: {notification.body}")
            else:
                raise RuntimeError(f"Unsupported channel {delivery.channel}")

            if not result.success:
                raise RuntimeError(result.error or "Provider reported failure")

            delivery.provider = result.provider
            delivery.status = NotificationDeliveryStatus.DELIVERED
            delivery.delivered_at = utc_now()
            delivery.last_error_reason = None
            delivery.last_error_code = None
            delivery.next_attempt_at = None
            delivery.updated_at = utc_now()
            db.add(delivery)
            await db.commit()
            return True
        except Exception as exc:
            message = str(exc)
            msg_l = message.lower()
            retryable = any(token in msg_l for token in RETRYABLE_ERROR_MARKERS)
            invalid_token = any(token in msg_l for token in INVALID_TOKEN_MARKERS)

            if invalid_token:
                delivery.last_error_code = "invalid_device_token"
                device_id = int(delivery.target.split(":", 1)[1]) if delivery.target and delivery.target.startswith("device:") else None
                device = await db.get(NotificationDevice, device_id) if device_id else None
                if device:
                    device.is_active = False
                    device.updated_at = utc_now()
                    db.add(device)
                retryable = False
            else:
                delivery.last_error_code = "provider_error"

            delivery.last_error_reason = message[:1024]
            delivery.updated_at = utc_now()

            if retryable and delivery.attempt_count < delivery.max_attempts:
                # Exponential backoff with small deterministic jitter
                countdown = min(300, (2 ** max(0, delivery.attempt_count - 1)) + (delivery_id % 3))
                delivery.status = NotificationDeliveryStatus.RETRYING
                delivery.next_attempt_at = utc_now()
                db.add(delivery)
                await db.commit()
                dispatch_notification_delivery_task.apply_async(args=[delivery_id], countdown=countdown)
                return False

            delivery.status = NotificationDeliveryStatus.DEAD_LETTER
            delivery.dead_lettered_at = utc_now()
            delivery.next_attempt_at = None
            db.add(delivery)
            await db.commit()
            logger.warning(
                "Notification delivery dead-lettered id=%s notification=%s channel=%s reason=%s",
                delivery.id,
                delivery.notification_id,
                delivery.channel,
                message,
            )
            return False
