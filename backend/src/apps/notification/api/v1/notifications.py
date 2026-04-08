"""
Notification REST API.

Endpoints
─────────
  GET    /notifications/              — list current user's notifications
  POST   /notifications/              — create a notification (superuser only)
  PATCH  /notifications/read-all/     — mark all notifications as read
  PATCH  /notifications/{id}/read/    — mark a single notification as read
  DELETE /notifications/{id}/         — delete a notification
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.notification.models.notification_delivery import (
    NotificationDeliveryChannel,
    NotificationDeliveryStatus,
)
from src.apps.notification.schemas.notification import (
    NotificationCreate,
    NotificationList,
    NotificationRead,
)
from src.apps.notification.schemas.notification_delivery import NotificationDeliveryList, NotificationDeliveryRead
from src.apps.notification.services.notification import (
    create_notification,
    delete_notification,
    get_notification,
    get_user_notifications,
    mark_all_read,
    mark_as_read,
    get_failed_deliveries,
    retry_delivery,
)

router = APIRouter()


@router.get("/", response_model=NotificationList, summary="List notifications")
async def list_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationList:
    """Return paginated notifications for the authenticated user."""
    assert isinstance(current_user.id, int),"User Id can't be None"
    return await get_user_notifications(
        db, current_user.id, unread_only=unread_only, skip=skip, limit=limit
    )


@router.post(
    "/",
    response_model=NotificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification (superuser)",
)
async def create_notification_endpoint(
    data: NotificationCreate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    """
    Create a notification for any user.
    The notification is persisted **and** pushed over WebSocket if the
    target user is currently connected.
    """
    notification = await create_notification(db, data, push_ws=True)
    return NotificationRead.model_validate(notification)


@router.patch(
    "/read-all/",
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark every unread notification for the current user as read."""

    assert isinstance(current_user.id, int),"User Id can't be None"
    count = await mark_all_read(db, current_user.id)
    return {"updated": count}


@router.get(
    "/{notification_id}/",
    response_model=NotificationRead,
    summary="Get a single notification",
)
async def get_notification_endpoint(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    assert isinstance(current_user.id, int),"User Id can't be None"
    notification = await get_notification(db, decode_id_or_404(notification_id), current_user.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationRead.model_validate(notification)


@router.patch(
    "/{notification_id}/read/",
    response_model=NotificationRead,
    summary="Mark notification as read",
)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    """Mark a single notification as read."""

    assert isinstance(current_user.id, int),"User Id can't be None"
    notification = await mark_as_read(db, decode_id_or_404(notification_id), current_user.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationRead.model_validate(notification)


@router.delete(
    "/{notification_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
)
async def delete_notification_endpoint(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a notification belonging to the current user."""
    deleted = await delete_notification(db, decode_id_or_404(notification_id), current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.get(
    "/admin/deliveries/failed/",
    response_model=NotificationDeliveryList,
    summary="List failed/retrying notification deliveries (superuser)",
)
async def list_failed_notification_deliveries(
    channel: NotificationDeliveryChannel | None = Query(default=None),
    status_filter: NotificationDeliveryStatus | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> NotificationDeliveryList:
    _ = current_user
    items, total = await get_failed_deliveries(
        db,
        channel=channel,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return NotificationDeliveryList(
        items=[NotificationDeliveryRead.model_validate(item) for item in items],
        total=total,
    )


@router.post(
    "/admin/deliveries/{delivery_id}/retry/",
    response_model=NotificationDeliveryRead,
    summary="Retry a failed notification delivery (superuser)",
)
async def retry_notification_delivery(
    delivery_id: str,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> NotificationDeliveryRead:
    _ = current_user
    delivery = await retry_delivery(db, decode_id_or_404(delivery_id))
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return NotificationDeliveryRead.model_validate(delivery)
