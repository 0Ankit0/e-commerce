from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.commerce.models import Address
from src.apps.commerce.services import build_cart_payload, build_quote_fingerprint, calculate_tax_amount, get_or_create_cart
from src.apps.core.models import ReportJob, ReportJobStatus
from src.apps.core.time import utc_now, utc_now_iso
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.logistics.services import quote_shipping
from src.apps.orders.models import (
    CheckoutIdempotency,
    Order,
    OrderEvent,
    OrderItem,
    OrderNote,
    OrderStatus,
    PaymentMethod,
    ReturnEvent,
    ReturnRequest,
    ReturnStatus,
    Shipment,
    ShipmentTracking,
    VendorOrder,
    VendorOrderStatus,
)
from src.apps.orders.services import (
    add_order_note,
    cancel_order,
    create_order_from_cart,
    create_return_request,
    list_order_events,
    list_order_notes,
    list_return_events,
    serialize_order,
    update_return_request_status,
)
from src.apps.notification.services.commerce_events import notify_order_event, notify_return_event
from src.apps.recommendations.models import RecommendationEventType
from src.apps.recommendations.services import record_recommendation_event
from src.apps.vendors.models import VendorPayoutBatch, VendorPayoutRequest, VendorTimelineEvent
from src.apps.vendors.services import get_vendor_for_user

router = APIRouter()


class CheckoutRequest(BaseModel):
    address_id: str
    payment_method: PaymentMethod = PaymentMethod.COD
    payment_transaction_id: str | None = None
    shipping_option_code: str | None = None
    quote_fingerprint: str | None = None
    notes: str = ""


class ReturnRequestPayload(BaseModel):
    order_id: str
    order_item_id: str | None = None
    reason: str = Field(min_length=3, max_length=255)
    details: str = ""
    refund_method: str = "original"


class VendorOrderStatusUpdateRequest(BaseModel):
    status: VendorOrderStatus
    location: str = ""
    remarks: str = ""


class VendorOrderRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class OrderNoteCreateRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
    note_type: str = "internal"
    is_customer_visible: bool = False


class ReturnStatusUpdateRequest(BaseModel):
    status: ReturnStatus
    note: str = ""


class ReportJobCreateRequest(BaseModel):
    report_type: str = Field(min_length=3, max_length=80)
    date_from: datetime | None = None
    date_to: datetime | None = None
    output_format: str = "csv"


def _build_live_feed_item(
    *,
    source: str,
    event_type: str,
    message: str,
    created_at: datetime,
    payload: dict[str, object],
    actor_user_id: int | None = None,
) -> dict[str, object]:
    return {
        "source": source,
        "event_type": event_type,
        "message": message,
        "actor_user_id": encode_id(actor_user_id) if actor_user_id else None,
        "payload": payload,
        "created_at": created_at.isoformat(),
    }


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(
    request: Request,
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        existing_key = (
            await db.execute(
                select(CheckoutIdempotency).where(
                    CheckoutIdempotency.user_id == current_user.id,
                    CheckoutIdempotency.idempotency_key == idempotency_key,
                )
            )
        ).scalars().first()
        if existing_key:
            if payload.quote_fingerprint and existing_key.request_fingerprint and existing_key.request_fingerprint != payload.quote_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different checkout request",
                )
            existing_order = await db.get(Order, existing_key.order_id)
            if existing_order is not None:
                return {"order": await serialize_order(existing_order, db)}

    address = await db.get(Address, decode_id_or_404(payload.address_id))
    if address is None or address.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    cart = await get_or_create_cart(current_user.id, db)
    cart_payload = await build_cart_payload(cart, db)
    shipping_quote = await quote_shipping(
        address.pincode,
        payload.payment_method == PaymentMethod.COD,
        db,
        shipping_option_code=payload.shipping_option_code,
    )
    taxable_amount = max(float(cart_payload["subtotal"]) - float(cart_payload["discount"]), 0.0)
    tax_payload = await calculate_tax_amount(
        address=address,
        category_ids=set(cart_payload.get("category_ids", [])),
        taxable_amount=taxable_amount,
        db=db,
    )
    expected_quote_fingerprint = build_quote_fingerprint(
        cart_payload=cart_payload,
        address_id=address.id,
        payment_method=payload.payment_method.value,
        shipping_quote=shipping_quote,
        tax_payload=tax_payload,
    )
    if payload.quote_fingerprint and payload.quote_fingerprint != expected_quote_fingerprint:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Checkout quote is stale; refresh the quote and retry")
    order = await create_order_from_cart(
        user_id=current_user.id,
        address_id=decode_id_or_404(payload.address_id),
        payment_method=payload.payment_method,
        payment_transaction_id=decode_id_or_404(payload.payment_transaction_id) if payload.payment_transaction_id else None,
        notes=payload.notes,
        db=db,
        idempotency_key=idempotency_key,
        request_fingerprint=expected_quote_fingerprint,
        shipping_option_code=payload.shipping_option_code,
    )
    order_items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    for item in order_items:
        await record_recommendation_event(
            user_id=current_user.id,
            product_id=item.product_id,
            event_type=RecommendationEventType.PURCHASE,
            placement=None,
            query_text="",
            metadata={"order_id": order.id},
            db=db,
        )
    await db.commit()
    await db.refresh(order)
    await analytics.capture(str(current_user.id), "order_created", {"order_id": order.id, "order_number": order.order_number})
    await notify_order_event(
        db=db,
        user_id=current_user.id,
        order_id=encode_id(order.id or 0),
        order_number=order.order_number,
        event="order.created",
        title="Order placed",
        body=f"Your order {order.order_number} has been placed.",
        status=order.status.value,
        payment_status=order.payment_status.value,
    )
    return {"order": await serialize_order(order, db)}


@router.get("/checkout/quote")
async def checkout_quote(
    address_id: str,
    payment_method: PaymentMethod = PaymentMethod.COD,
    shipping_option_code: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, decode_id_or_404(address_id))
    if address is None or address.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    cart = await get_or_create_cart(current_user.id, db)
    cart_payload = await build_cart_payload(cart, db)
    shipping_quote = await quote_shipping(
        address.pincode,
        payment_method == PaymentMethod.COD,
        db,
        shipping_option_code=shipping_option_code,
    )
    if not shipping_quote["serviceable"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Address is not serviceable")
    taxable_amount = max(float(cart_payload["subtotal"]) - float(cart_payload["discount"]), 0.0)
    tax_payload = await calculate_tax_amount(
        address=address,
        category_ids=set(cart_payload.get("category_ids", [])),
        taxable_amount=taxable_amount,
        db=db,
    )
    tax = float(tax_payload["tax"])
    total = round(taxable_amount + float(shipping_quote["shipping_rate"]) + tax, 2)
    fingerprint = build_quote_fingerprint(
        cart_payload=cart_payload,
        address_id=address.id,
        payment_method=payment_method.value,
        shipping_quote=shipping_quote,
        tax_payload=tax_payload,
    )
    return {
        "cart": cart_payload,
        "shipping": shipping_quote,
        "tax": tax,
        "tax_rate": tax_payload["rate"],
        "tax_rule": tax_payload["rule"],
        "total": total,
        "fingerprint": fingerprint,
    }


@router.get("/orders")
async def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = (
        await db.execute(select(Order).where(Order.user_id == current_user.id).order_by(Order.created_at.desc()))
    ).scalars().all()
    return {"items": [await serialize_order(order, db) for order in orders], "total": len(orders)}


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"order": await serialize_order(order, db)}


@router.get("/orders/{order_id}/timeline")
async def get_order_timeline(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    events = await list_order_events(order.id, db)
    return {
        "items": [
            {
                "id": encode_id(event.id or 0),
                "event_type": event.event_type,
                "message": event.message,
                "payload": json.loads(event.payload_json or "{}"),
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
    }


@router.get("/orders/{order_id}/notes")
async def get_order_notes(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    notes = [note for note in await list_order_notes(order.id, db) if note.is_customer_visible]
    return {
        "items": [
            {
                "id": encode_id(note.id or 0),
                "note_type": note.note_type,
                "note": note.note,
                "created_at": note.created_at.isoformat(),
            }
            for note in notes
        ]
    }


@router.get("/orders/{order_id}/invoice")
async def get_order_invoice(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order_payload = await serialize_order(order, db)
    return {
        "invoice_number": f"INV-{order.order_number}",
        "order": order_payload,
        "billing_currency": "NPR",
        "issued_at": utc_now_iso(),
    }


@router.post("/orders/{order_id}/cancel")
async def cancel_customer_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    await cancel_order(order, db)
    await db.commit()
    await notify_order_event(
        db=db,
        user_id=current_user.id,
        order_id=encode_id(order.id or 0),
        order_number=order.order_number,
        event="order.cancelled",
        title="Order cancelled",
        body=f"Your order {order.order_number} has been cancelled.",
        status=order.status.value,
        payment_status=order.payment_status.value,
    )
    return {"order": await serialize_order(order, db)}


@router.post("/orders/{order_id}/cancel-items/{order_item_id}")
async def cancel_order_item(
    order_id: str,
    order_item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status in {OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order item can no longer be cancelled")
    order_item = await db.get(OrderItem, decode_id_or_404(order_item_id))
    if order_item is None or order_item.order_id != order.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    order_item.status = VendorOrderStatus.CANCELLED
    order.discount = round(order.discount, 2)
    order.total = round(max(order.total - order_item.total_price, 0.0), 2)
    await db.commit()
    return {"order": await serialize_order(order, db)}


@router.post("/returns", status_code=status.HTTP_201_CREATED)
async def request_return(
    payload: ReturnRequestPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(payload.order_id))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return_request = await create_return_request(
        order=order,
        user_id=current_user.id,
        order_item_id=decode_id_or_404(payload.order_item_id) if payload.order_item_id else None,
        reason=payload.reason,
        details=payload.details,
        refund_method=payload.refund_method,
        db=db,
    )
    await db.commit()
    await notify_return_event(
        db=db,
        user_id=current_user.id,
        return_request_id=encode_id(return_request.id or 0),
        order_id=payload.order_id,
        event="return.requested",
        title="Return requested",
        body="Your return request has been submitted.",
        status=return_request.status.value,
    )
    return {"return_request_id": encode_id(return_request.id or 0), "status": return_request.status.value}


@router.get("/returns/{return_request_id}")
async def get_return_request(
    return_request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return_request = await db.get(ReturnRequest, decode_id_or_404(return_request_id))
    if return_request is None or return_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    return {"return_request": _serialize_return_request(return_request)}


@router.get("/returns/{return_request_id}/timeline")
async def get_return_timeline(
    return_request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return_request = await db.get(ReturnRequest, decode_id_or_404(return_request_id))
    if return_request is None or return_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    events = await list_return_events(return_request.id, db)
    return {
        "items": [
            {
                "id": encode_id(event.id or 0),
                "event_type": event.event_type,
                "message": event.message,
                "payload": json.loads(event.payload_json or "{}"),
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
    }


@router.get("/tracking/{order_id}")
async def track_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    shipments = (await db.execute(select(Shipment).where(Shipment.order_id == order.id))).scalars().all()
    payload = []
    for shipment in shipments:
        tracking = (
            await db.execute(
                select(ShipmentTracking).where(ShipmentTracking.shipment_id == shipment.id).order_by(ShipmentTracking.timestamp.asc())
            )
        ).scalars().all()
        payload.append(
            {
                "shipment_id": encode_id(shipment.id or 0),
                "awb": shipment.awb,
                "status": shipment.status.value,
                "current_location": shipment.current_location,
                "events": [
                    {
                        "status": event.status.value,
                        "location": event.location,
                        "remarks": event.remarks,
                        "timestamp": event.timestamp.isoformat(),
                    }
                    for event in tracking
                ],
            }
        )
    return {"order_number": order.order_number, "shipments": payload}


@router.get("/vendor/orders")
async def list_vendor_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    vendor_orders = (
        await db.execute(select(VendorOrder).where(VendorOrder.vendor_id == vendor.id).order_by(VendorOrder.created_at.desc()))
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(vendor_order.id or 0),
                "order_id": encode_id(vendor_order.order_id),
                "vendor_order_number": vendor_order.vendor_order_number,
                "status": vendor_order.status.value,
                "subtotal": vendor_order.subtotal,
                "commission": vendor_order.commission,
                "vendor_amount": vendor_order.vendor_amount,
            }
            for vendor_order in vendor_orders
        ],
        "total": len(vendor_orders),
    }


@router.post("/vendor/orders/{vendor_order_id}/status")
async def update_vendor_order_status(
    vendor_order_id: str,
    payload: VendorOrderStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    vendor_order = await db.get(VendorOrder, decode_id_or_404(vendor_order_id))
    if vendor_order is None or vendor_order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor order not found")
    vendor_order.status = payload.status
    vendor_order.updated_at = utc_now()

    order = await db.get(Order, vendor_order.order_id)
    if order:
        status_map = {
            VendorOrderStatus.ACCEPTED: OrderStatus.PROCESSING,
            VendorOrderStatus.PACKED: OrderStatus.PACKED,
            VendorOrderStatus.SHIPPED: OrderStatus.SHIPPED,
            VendorOrderStatus.DELIVERED: OrderStatus.DELIVERED,
            VendorOrderStatus.CANCELLED: OrderStatus.CANCELLED,
        }
        if payload.status in status_map:
            order.status = status_map[payload.status]
            if payload.status == VendorOrderStatus.DELIVERED:
                order.delivered_at = utc_now()

    order_items = (
        await db.execute(select(OrderItem).where(OrderItem.vendor_order_id == vendor_order.id))
    ).scalars().all()
    for item in order_items:
        item.status = payload.status

    shipment = (
        await db.execute(select(Shipment).where(Shipment.vendor_order_id == vendor_order.id))
    ).scalars().first()
    if shipment:
        shipment.status = order.status if order else OrderStatus.CONFIRMED
        shipment.current_location = payload.location or shipment.current_location
        shipment.updated_at = utc_now()
        db.add(
            ShipmentTracking(
                shipment_id=shipment.id,
                status=shipment.status,
                location=payload.location or shipment.current_location,
                remarks=payload.remarks or payload.status.value,
            )
        )
    await db.commit()
    if order is not None:
        await notify_order_event(
            db=db,
            user_id=order.user_id,
            order_id=encode_id(order.id or 0),
            order_number=order.order_number,
            event=f"order.{order.status.value}",
            title=f"Order {order.status.value.replace('_', ' ')}",
            body=payload.remarks or f"Your order is now {order.status.value.replace('_', ' ')}.",
            status=order.status.value,
            payment_status=order.payment_status.value,
        )
    return {"success": True, "status": payload.status.value}


@router.post("/vendor/orders/{vendor_order_id}/reject")
async def reject_vendor_order(
    vendor_order_id: str,
    payload: VendorOrderRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    vendor_order = await db.get(VendorOrder, decode_id_or_404(vendor_order_id))
    if vendor_order is None or vendor_order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor order not found")
    vendor_order.status = VendorOrderStatus.REJECTED
    vendor_order.updated_at = utc_now()
    order = await db.get(Order, vendor_order.order_id)
    if order:
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = utc_now()
    shipment = (
        await db.execute(select(Shipment).where(Shipment.vendor_order_id == vendor_order.id))
    ).scalars().first()
    if shipment:
        shipment.status = OrderStatus.CANCELLED
        shipment.current_location = "Vendor rejected order"
        db.add(
            ShipmentTracking(
                shipment_id=shipment.id,
                status=OrderStatus.CANCELLED,
                location="Vendor",
                remarks=payload.reason,
            )
        )
    await db.commit()
    if order is not None:
        await notify_order_event(
            db=db,
            user_id=order.user_id,
            order_id=encode_id(order.id or 0),
            order_number=order.order_number,
            event="order.cancelled",
            title="Order cancelled",
            body=payload.reason,
            status=order.status.value,
            payment_status=order.payment_status.value,
        )
    return {"success": True}


@router.get("/admin/orders")
async def list_all_orders(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    orders = (await db.execute(select(Order).order_by(Order.created_at.desc()))).scalars().all()
    return {"items": [await serialize_order(order, db) for order in orders], "total": len(orders)}


@router.get("/admin/orders/live-feed")
async def admin_order_live_feed(
    limit: int = 50,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    order_events = (
        await db.execute(select(OrderEvent).order_by(OrderEvent.created_at.desc()).limit(limit))
    ).scalars().all()
    return_events = (
        await db.execute(select(ReturnEvent).order_by(ReturnEvent.created_at.desc()).limit(limit))
    ).scalars().all()
    shipment_events = (
        await db.execute(select(ShipmentTracking).order_by(ShipmentTracking.timestamp.desc()).limit(limit))
    ).scalars().all()
    payout_requests = (
        await db.execute(select(VendorPayoutRequest).order_by(VendorPayoutRequest.created_at.desc()).limit(limit))
    ).scalars().all()
    payout_batches = (
        await db.execute(select(VendorPayoutBatch).order_by(VendorPayoutBatch.created_at.desc()).limit(limit))
    ).scalars().all()
    vendor_timeline_events = (
        await db.execute(select(VendorTimelineEvent).order_by(VendorTimelineEvent.created_at.desc()).limit(limit))
    ).scalars().all()
    items = [
        _build_live_feed_item(
            source="order",
            event_type=event.event_type,
            message=event.message,
            created_at=event.created_at,
            payload={"order_id": encode_id(event.order_id), **json.loads(event.payload_json or "{}")},
            actor_user_id=event.actor_user_id,
        )
        for event in order_events
    ]
    items.extend(
        [
            _build_live_feed_item(
                source="return",
                event_type=event.event_type,
                message=event.message,
                created_at=event.created_at,
                payload={"return_request_id": encode_id(event.return_request_id), **json.loads(event.payload_json or "{}")},
                actor_user_id=event.actor_user_id,
            )
            for event in return_events
        ]
    )
    items.extend(
        [
            _build_live_feed_item(
                source="shipment",
                event_type=f"shipment.{event.status.value}",
                message=event.remarks or f"Shipment updated to {event.status.value}",
                created_at=event.timestamp,
                payload={
                    "shipment_id": encode_id(event.shipment_id),
                    "status": event.status.value,
                    "location": event.location,
                },
            )
            for event in shipment_events
        ]
    )
    items.extend(
        [
            _build_live_feed_item(
                source="payout",
                event_type="vendor.payout_requested",
                message="Vendor requested payout",
                created_at=request.created_at,
                payload={
                    "payout_request_id": encode_id(request.id or 0),
                    "vendor_id": encode_id(request.vendor_id),
                    "amount": request.amount,
                    "status": request.status.value,
                },
                actor_user_id=request.requested_by_user_id,
            )
            for request in payout_requests
        ]
    )
    items.extend(
        [
            _build_live_feed_item(
                source="payout",
                event_type="vendor.payout_batch_created",
                message="Payout batch created",
                created_at=batch.created_at,
                payload={
                    "payout_batch_id": encode_id(batch.id or 0),
                    "code": batch.code,
                    "status": batch.status.value,
                    "total_amount": batch.total_amount,
                },
            )
            for batch in payout_batches
        ]
    )
    items.extend(
        [
            _build_live_feed_item(
                source="vendor",
                event_type=event.event_type,
                message=event.message,
                created_at=event.created_at,
                payload={"vendor_id": encode_id(event.vendor_id), **json.loads(event.payload_json or "{}")},
                actor_user_id=event.actor_user_id,
            )
            for event in vendor_timeline_events
            if "payout" in event.event_type
        ]
    )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return {"items": items[:limit], "total": len(items[:limit])}


@router.get("/admin/returns")
async def list_admin_returns(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    returns = (await db.execute(select(ReturnRequest).order_by(ReturnRequest.created_at.desc()))).scalars().all()
    return {"items": [_serialize_return_request(return_request) for return_request in returns], "total": len(returns)}


@router.post("/admin/returns/{return_request_id}/status")
async def update_admin_return_status(
    return_request_id: str,
    payload: ReturnStatusUpdateRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    return_request = await db.get(ReturnRequest, decode_id_or_404(return_request_id))
    if return_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    await update_return_request_status(
        return_request=return_request,
        status_value=payload.status,
        actor_user_id=current_user.id,
        message=payload.note or f"Return updated to {payload.status.value}",
        payload={"note": payload.note},
        db=db,
    )
    await db.commit()
    await notify_return_event(
        db=db,
        user_id=return_request.user_id,
        return_request_id=encode_id(return_request.id or 0),
        order_id=encode_id(return_request.order_id),
        event=f"return.{return_request.status.value}",
        title=f"Return {return_request.status.value.replace('_', ' ')}",
        body=payload.note or f"Your return request is now {return_request.status.value.replace('_', ' ')}.",
        status=return_request.status.value,
    )
    return {"return_request": _serialize_return_request(return_request)}


@router.post("/admin/orders/{order_id}/notes", status_code=status.HTTP_201_CREATED)
async def create_admin_order_note(
    order_id: str,
    payload: OrderNoteCreateRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(order_id))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    note = await add_order_note(
        order_id=order.id,
        note=payload.note,
        note_type=payload.note_type,
        is_customer_visible=payload.is_customer_visible,
        created_by_user_id=current_user.id,
        db=db,
    )
    await db.commit()
    return {"note_id": encode_id(note.id or 0)}


@router.get("/admin/reports/overview")
async def admin_reports_overview(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    orders = (await db.execute(select(Order))).scalars().all()
    returns = (await db.execute(select(ReturnRequest))).scalars().all()
    vendor_orders = (await db.execute(select(VendorOrder))).scalars().all()
    gmv = round(sum(order.total for order in orders if order.status != OrderStatus.CANCELLED), 2)
    delivered_orders = [order for order in orders if order.status == OrderStatus.DELIVERED]
    aov = round(gmv / len(orders), 2) if orders else 0
    return_rate = round((len(returns) / len(delivered_orders)) * 100, 2) if delivered_orders else 0
    return {
        "gmv": gmv,
        "order_count": len(orders),
        "delivered_order_count": len(delivered_orders),
        "average_order_value": aov,
        "return_rate_percent": return_rate,
        "vendor_order_count": len(vendor_orders),
    }


@router.get("/admin/reports/export")
async def export_admin_report(
    report_type: str = "orders",
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if report_type == "returns":
        returns = (await db.execute(select(ReturnRequest).order_by(ReturnRequest.created_at.desc()))).scalars().all()
        writer.writerow(["return_id", "order_id", "status", "refund_method", "eligible_until", "created_at"])
        for return_request in returns:
            writer.writerow(
                [
                    encode_id(return_request.id or 0),
                    encode_id(return_request.order_id),
                    return_request.status.value,
                    return_request.refund_method,
                    return_request.eligible_until.isoformat() if return_request.eligible_until else "",
                    return_request.created_at.isoformat(),
                ]
            )
    else:
        orders = (await db.execute(select(Order).order_by(Order.created_at.desc()))).scalars().all()
        writer.writerow(["order_id", "order_number", "status", "payment_status", "total", "created_at"])
        for order in orders:
            writer.writerow(
                [
                    encode_id(order.id or 0),
                    order.order_number,
                    order.status.value,
                    order.payment_status.value,
                    order.total,
                    order.created_at.isoformat(),
                ]
            )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="admin-{report_type}-report.csv"'},
    )


@router.post("/admin/reports/jobs", status_code=status.HTTP_201_CREATED)
async def create_report_job(
    payload: ReportJobCreateRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    preview_json = json.dumps({"report_type": payload.report_type})
    report_job = ReportJob(
        report_type=payload.report_type,
        requested_by_user_id=current_user.id,
        date_from=payload.date_from,
        date_to=payload.date_to,
        output_format=payload.output_format,
        status=ReportJobStatus.COMPLETED,
        run_at=utc_now(),
        result_preview_json=preview_json,
    )
    db.add(report_job)
    await db.commit()
    await db.refresh(report_job)
    return {"report_job_id": encode_id(report_job.id or 0), "status": report_job.status.value}


@router.get("/admin/reports/jobs")
async def list_report_jobs(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    jobs = (await db.execute(select(ReportJob).order_by(ReportJob.created_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(job.id or 0),
                "report_type": job.report_type,
                "status": job.status.value,
                "output_format": job.output_format,
                "created_at": job.created_at.isoformat(),
                "run_at": job.run_at.isoformat() if job.run_at else None,
            }
            for job in jobs
        ],
        "total": len(jobs),
    }


def _serialize_return_request(return_request: ReturnRequest) -> dict[str, object]:
    return {
        "id": encode_id(return_request.id or 0),
        "order_id": encode_id(return_request.order_id),
        "order_item_id": encode_id(return_request.order_item_id) if return_request.order_item_id else None,
        "user_id": encode_id(return_request.user_id),
        "reason": return_request.reason,
        "details": return_request.details,
        "refund_method": return_request.refund_method,
        "status": return_request.status.value,
        "return_window_days": return_request.return_window_days,
        "eligible_until": return_request.eligible_until.isoformat() if return_request.eligible_until else None,
        "created_at": return_request.created_at.isoformat(),
        "resolved_at": return_request.resolved_at.isoformat() if return_request.resolved_at else None,
    }
