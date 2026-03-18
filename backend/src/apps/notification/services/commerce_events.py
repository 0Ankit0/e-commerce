from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.notification.models.notification import NotificationType
from src.apps.notification.schemas.notification import NotificationCreate
from src.apps.notification.services.notification import create_notification
from src.apps.websocket.manager import manager

ADMIN_LIVE_ROOM = "admin.orders.live"


async def notify_user(
    *,
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str,
    event: str,
    notification_type: NotificationType = NotificationType.INFO,
    extra_data: dict[str, Any] | None = None,
) -> None:
    payload = extra_data or {}
    await create_notification(
        db,
        NotificationCreate(
            user_id=user_id,
            title=title,
            body=body,
            type=notification_type,
            extra_data={"event": event, **payload},
        ),
    )
    await manager.push_event(
        user_id,
        event,
        {
            "title": title,
            "body": body,
            **payload,
        },
    )


async def push_admin_live_event(
    *,
    event: str,
    payload: dict[str, Any],
) -> None:
    await manager.push_event_to_room(
        ADMIN_LIVE_ROOM,
        event,
        payload,
    )


async def notify_order_event(
    *,
    db: AsyncSession,
    user_id: int,
    order_id: str,
    order_number: str,
    event: str,
    title: str,
    body: str,
    status: str,
    payment_status: str | None = None,
) -> None:
    payload = {
        "order_id": order_id,
        "order_number": order_number,
        "status": status,
    }
    if payment_status is not None:
        payload["payment_status"] = payment_status
    await notify_user(
        db=db,
        user_id=user_id,
        title=title,
        body=body,
        event=event,
        notification_type=NotificationType.SUCCESS if status in {"confirmed", "delivered"} else NotificationType.INFO,
        extra_data=payload,
    )
    await push_admin_live_event(
        event=event,
        payload={"source": "order", **payload, "title": title, "body": body},
    )


async def notify_return_event(
    *,
    db: AsyncSession,
    user_id: int,
    return_request_id: str,
    order_id: str,
    event: str,
    title: str,
    body: str,
    status: str,
) -> None:
    payload = {
        "return_request_id": return_request_id,
        "order_id": order_id,
        "status": status,
    }
    await notify_user(
        db=db,
        user_id=user_id,
        title=title,
        body=body,
        event=event,
        notification_type=NotificationType.INFO,
        extra_data=payload,
    )
    await push_admin_live_event(event=event, payload={"source": "return", **payload, "title": title, "body": body})


async def notify_payout_event(
    *,
    db: AsyncSession,
    user_id: int,
    vendor_id: str,
    event: str,
    title: str,
    body: str,
    amount: float | None = None,
    payout_request_id: str | None = None,
    payout_batch_id: str | None = None,
    status: str | None = None,
) -> None:
    payload: dict[str, Any] = {"vendor_id": vendor_id}
    if amount is not None:
        payload["amount"] = amount
    if payout_request_id is not None:
        payload["payout_request_id"] = payout_request_id
    if payout_batch_id is not None:
        payload["payout_batch_id"] = payout_batch_id
    if status is not None:
        payload["status"] = status
    await notify_user(
        db=db,
        user_id=user_id,
        title=title,
        body=body,
        event=event,
        notification_type=NotificationType.PAYMENT,
        extra_data=payload,
    )
    await push_admin_live_event(event=event, payload={"source": "payout", **payload, "title": title, "body": body})


async def notify_low_stock(
    *,
    db: AsyncSession,
    user_id: int,
    product_id: str,
    variant_id: str,
    sku: str,
    quantity: int,
    reorder_level: int,
) -> None:
    await notify_user(
        db=db,
        user_id=user_id,
        title="Low stock alert",
        body=f"{sku} is down to {quantity} units.",
        event="catalog.low_stock",
        notification_type=NotificationType.WARNING,
        extra_data={
            "product_id": product_id,
            "variant_id": variant_id,
            "sku": sku,
            "quantity": quantity,
            "reorder_level": reorder_level,
        },
    )
    await push_admin_live_event(
        event="catalog.low_stock",
        payload={
            "source": "catalog",
            "product_id": product_id,
            "variant_id": variant_id,
            "sku": sku,
            "quantity": quantity,
            "reorder_level": reorder_level,
            "title": "Low stock alert",
        },
    )


async def notify_wishlist_price_drop(
    *,
    db: AsyncSession,
    user_id: int,
    product_id: str,
    variant_id: str,
    product_name: str,
    variant_name: str,
    previous_price: float,
    current_price: float,
) -> None:
    await notify_user(
        db=db,
        user_id=user_id,
        title="Price drop on your wishlist",
        body=f"{product_name} {variant_name}".strip() + f" dropped from {previous_price:.2f} to {current_price:.2f}.",
        event="wishlist.price_drop",
        notification_type=NotificationType.SUCCESS,
        extra_data={
            "product_id": product_id,
            "variant_id": variant_id,
            "previous_price": previous_price,
            "current_price": current_price,
        },
    )
    await push_admin_live_event(
        event="wishlist.price_drop",
        payload={
            "source": "wishlist",
            "product_id": product_id,
            "variant_id": variant_id,
            "previous_price": previous_price,
            "current_price": current_price,
        },
    )


async def notify_delivery_exception(
    *,
    db: AsyncSession,
    user_id: int,
    shipment_id: str,
    order_id: str,
    event: str,
    title: str,
    body: str,
    status: str,
) -> None:
    payload = {
        "shipment_id": shipment_id,
        "order_id": order_id,
        "status": status,
    }
    await notify_user(
        db=db,
        user_id=user_id,
        title=title,
        body=body,
        event=event,
        notification_type=NotificationType.WARNING,
        extra_data=payload,
    )
    await push_admin_live_event(event=event, payload={"source": "shipment", **payload, "title": title, "body": body})
