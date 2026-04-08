"""Notification service — persistence plus multi-channel delivery."""
import hashlib
import logging
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.apps.core.time import utc_now
from src.apps.notification.models.notification import Notification
from src.apps.notification.models.notification_delivery import (
    NotificationDelivery,
    NotificationDeliveryChannel,
    NotificationDeliveryStatus,
)
from src.apps.notification.models.notification_device import (
    NotificationDevice,
    NotificationDeviceProvider,
)
from src.apps.notification.models.notification_preference import NotificationPreference
from src.apps.notification.schemas.notification import NotificationCreate, NotificationList, NotificationRead
from src.apps.notification.schemas.notification_device import NotificationDeviceCreate
from src.apps.notification.schemas.notification_preference import NotificationPreferenceRead
from src.apps.notification.tasks import dispatch_notification_delivery_task

log = logging.getLogger(__name__)


async def get_or_create_preference(db: AsyncSession, user_id: int) -> NotificationPreference:
    result = await db.execute(
        select(NotificationPreference).where(col(NotificationPreference.user_id) == user_id)
    )
    pref = result.scalars().first()
    if pref is None:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return pref


async def list_devices(db: AsyncSession, user_id: int) -> list[NotificationDevice]:
    result = await db.execute(
        select(NotificationDevice)
        .where(
            and_(
                col(NotificationDevice.user_id) == user_id,
                col(NotificationDevice.is_active) == True,  # noqa: E712
            )
        )
        .order_by(col(NotificationDevice.updated_at).desc())
    )
    return list(result.scalars().all())


async def get_preference_read(
    db: AsyncSession,
    user_id: int,
) -> NotificationPreferenceRead:
    pref = await get_or_create_preference(db, user_id)
    return await serialize_preference(db, pref)


async def serialize_preference(
    db: AsyncSession,
    pref: NotificationPreference,
) -> NotificationPreferenceRead:
    devices = await list_devices(db, pref.user_id)
    push_providers = sorted({device.provider.value for device in devices})
    payload = NotificationPreferenceRead.model_validate(pref)
    return payload.model_copy(
        update={
            "push_provider": push_providers[0] if len(push_providers) == 1 else None,
            "push_providers": push_providers,
        }
    )


async def register_device(
    db: AsyncSession,
    user_id: int,
    payload: NotificationDeviceCreate,
) -> NotificationDevice:
    existing_query = select(NotificationDevice).where(
        NotificationDevice.user_id == user_id,
        NotificationDevice.provider == payload.provider,
    )
    if payload.provider == NotificationDeviceProvider.WEBPUSH:
        existing_query = existing_query.where(NotificationDevice.endpoint == payload.endpoint)
    elif payload.provider == NotificationDeviceProvider.FCM:
        existing_query = existing_query.where(NotificationDevice.token == payload.token)
    else:
        existing_query = existing_query.where(
            NotificationDevice.subscription_id == payload.subscription_id
        )
    result = await db.execute(existing_query)
    device = result.scalars().first()
    if device is None:
        device = NotificationDevice(user_id=user_id, provider=payload.provider, platform=payload.platform)
    device.token = payload.token
    device.endpoint = payload.endpoint
    device.p256dh = payload.p256dh
    device.auth = payload.auth
    device.subscription_id = payload.subscription_id
    device.device_metadata = payload.device_metadata
    device.is_active = True
    device.last_seen_at = utc_now()
    device.updated_at = utc_now()
    db.add(device)
    await db.commit()
    await db.refresh(device)
    await _sync_preference_push_fields(db, user_id)
    return device


async def remove_device(db: AsyncSession, user_id: int, device_id: int) -> bool:
    device = await db.get(NotificationDevice, device_id)
    if not device or device.user_id != user_id:
        return False
    device.is_active = False
    device.updated_at = utc_now()
    db.add(device)
    await db.commit()
    await _sync_preference_push_fields(db, user_id)
    return True


async def remove_webpush_subscription(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(
        select(NotificationDevice).where(
            NotificationDevice.user_id == user_id,
            NotificationDevice.provider == NotificationDeviceProvider.WEBPUSH,
            NotificationDevice.is_active == True,  # noqa: E712
        )
    )
    for device in result.scalars().all():
        device.is_active = False
        device.updated_at = utc_now()
        db.add(device)
    await db.commit()
    await _sync_preference_push_fields(db, user_id)


async def _sync_preference_push_fields(db: AsyncSession, user_id: int) -> NotificationPreference:
    pref = await get_or_create_preference(db, user_id)
    devices = await list_devices(db, user_id)
    webpush_device = next(
        (device for device in devices if device.provider == NotificationDeviceProvider.WEBPUSH),
        None,
    )
    pref.push_endpoint = webpush_device.endpoint if webpush_device else None
    pref.push_p256dh = webpush_device.p256dh if webpush_device else None
    pref.push_auth = webpush_device.auth if webpush_device else None
    pref.push_enabled = pref.push_enabled if devices else False
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return pref


async def create_notification(
    db: AsyncSession,
    data: NotificationCreate,
    push_ws: bool = True,
) -> Notification:
    notification = Notification(
        user_id=data.user_id,
        title=data.title,
        body=data.body,
        type=data.type,
        extra_data=data.extra_data,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    pref = await get_or_create_preference(db, data.user_id)

    if push_ws and pref.websocket_enabled:
        await _push_to_ws(db, notification)
    if pref.email_enabled:
        await _enqueue_channel_delivery(db, notification, NotificationDeliveryChannel.EMAIL)
    if pref.push_enabled:
        await _enqueue_push_device_deliveries(db, notification)
    if pref.sms_enabled:
        await _enqueue_channel_delivery(db, notification, NotificationDeliveryChannel.SMS)

    return notification


def _event_fanout_key(notification: Notification) -> str:
    if isinstance(notification.extra_data, dict):
        for key in ("fanout_key", "event_id", "event"):
            value = notification.extra_data.get(key)
            if value:
                return str(value)
    return f"notification:{notification.id}"


def _dedup_key(notification: Notification, channel: NotificationDeliveryChannel, target: str) -> str:
    raw = f"{notification.user_id}:{_event_fanout_key(notification)}:{channel.value}:{target}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _enqueue_channel_delivery(
    db: AsyncSession,
    notification: Notification,
    channel: NotificationDeliveryChannel,
    *,
    target: str | None = None,
    max_attempts: int = 4,
) -> NotificationDelivery:
    stable_target = target or f"user:{notification.user_id}"
    key = _dedup_key(notification, channel, stable_target)

    existing = (
        await db.execute(select(NotificationDelivery).where(NotificationDelivery.dedup_key == key))
    ).scalars().first()
    if existing:
        return existing

    delivery = NotificationDelivery(
        notification_id=notification.id,
        user_id=notification.user_id,
        channel=channel,
        status=NotificationDeliveryStatus.PENDING,
        target=stable_target,
        dedup_key=key,
        max_attempts=max_attempts,
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    dispatch_notification_delivery_task.delay(delivery.id)
    return delivery


async def _enqueue_push_device_deliveries(db: AsyncSession, notification: Notification) -> None:
    devices = await list_devices(db, notification.user_id)
    for device in devices:
        await _enqueue_channel_delivery(
            db,
            notification,
            NotificationDeliveryChannel.PUSH,
            target=f"device:{device.id}",
            max_attempts=5,
        )


async def _push_to_ws(db: AsyncSession, notification: Notification) -> None:
    try:
        from src.apps.websocket.manager import manager

        await manager.push_event(
            user_id=notification.user_id,
            event="notification.new",
            data={
                "id": notification.id,
                "title": notification.title,
                "body": notification.body,
                "type": notification.type,
                "is_read": notification.is_read,
                "extra_data": notification.extra_data,
                "created_at": notification.created_at.isoformat(),
            },
        )
        await _record_ws_delivery(db, notification, success=True)
    except Exception as exc:
        log.warning("WS push failed for notification id=%s: %s", notification.id, exc)
        await _record_ws_delivery(db, notification, success=False, reason=str(exc))


async def _record_ws_delivery(
    db: AsyncSession,
    notification: Notification,
    *,
    success: bool,
    reason: str | None = None,
) -> None:
    target = f"user:{notification.user_id}"
    key = _dedup_key(notification, NotificationDeliveryChannel.WEBSOCKET, target)
    existing = (
        await db.execute(select(NotificationDelivery).where(NotificationDelivery.dedup_key == key))
    ).scalars().first()
    if existing:
        return

    delivery = NotificationDelivery(
        notification_id=notification.id,
        user_id=notification.user_id,
        channel=NotificationDeliveryChannel.WEBSOCKET,
        status=NotificationDeliveryStatus.DELIVERED if success else NotificationDeliveryStatus.FAILED,
        target=target,
        dedup_key=key,
        attempt_count=1,
        last_attempt_at=utc_now(),
        delivered_at=utc_now() if success else None,
        last_error_reason=(reason or "")[:1024] if not success else None,
        last_error_code="websocket_push_failed" if not success else None,
    )
    db.add(delivery)
    await db.commit()


async def get_failed_deliveries(
    db: AsyncSession,
    *,
    channel: NotificationDeliveryChannel | None = None,
    status: NotificationDeliveryStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[NotificationDelivery], int]:
    base = select(NotificationDelivery).where(
        NotificationDelivery.status.in_(
            [NotificationDeliveryStatus.FAILED, NotificationDeliveryStatus.DEAD_LETTER, NotificationDeliveryStatus.RETRYING]
        )
    )
    if channel is not None:
        base = base.where(NotificationDelivery.channel == channel)
    if status is not None:
        base = base.where(NotificationDelivery.status == status)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    items = (
        await db.execute(
            base.order_by(col(NotificationDelivery.updated_at).desc()).offset(skip).limit(limit)
        )
    ).scalars().all()
    return list(items), total


async def retry_delivery(db: AsyncSession, delivery_id: int) -> Optional[NotificationDelivery]:
    delivery = await db.get(NotificationDelivery, delivery_id)
    if not delivery:
        return None

    if delivery.status == NotificationDeliveryStatus.DELIVERED:
        return delivery

    delivery.status = NotificationDeliveryStatus.PENDING
    delivery.last_error_reason = None
    delivery.last_error_code = None
    delivery.dead_lettered_at = None
    delivery.next_attempt_at = None
    delivery.updated_at = utc_now()
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    dispatch_notification_delivery_task.delay(delivery.id)
    return delivery


async def get_user_notifications(
    db: AsyncSession,
    user_id: int,
    *,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> NotificationList:
    base_query = select(Notification).where(col(Notification.user_id) == user_id)
    if unread_only:
        base_query = base_query.where(col(Notification.is_read) == False)  # noqa: E712

    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar_one()
    unread_result = await db.execute(
        select(func.count()).select_from(
            select(Notification)
            .where(and_(col(Notification.user_id) == user_id, col(Notification.is_read) == False))  # noqa: E712
            .subquery()
        )
    )
    unread_count = unread_result.scalar_one()
    result = await db.execute(
        base_query.order_by(col(Notification.created_at).desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    return NotificationList(
        items=[NotificationRead.model_validate(item) for item in items],
        total=total,
        unread_count=unread_count,
    )


async def get_notification(db: AsyncSession, notification_id: int, user_id: int) -> Optional[Notification]:
    result = await db.execute(
        select(Notification).where(
            and_(
                col(Notification.id) == notification_id,
                col(Notification.user_id) == user_id,
            )
        )
    )
    return result.scalars().first()


async def mark_as_read(
    db: AsyncSession,
    notification_id: int,
    user_id: int,
) -> Optional[Notification]:
    notification = await get_notification(db, notification_id, user_id)
    if not notification:
        return None
    notification.is_read = True
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(Notification).where(
            and_(col(Notification.user_id) == user_id, col(Notification.is_read) == False)  # noqa: E712
        )
    )
    notifications = result.scalars().all()
    for notification in notifications:
        notification.is_read = True
        db.add(notification)
    await db.commit()
    return len(notifications)


async def delete_notification(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    notification = await get_notification(db, notification_id, user_id)
    if not notification:
        return False
    await db.delete(notification)
    await db.commit()
    return True
