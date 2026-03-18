from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.commerce.models import Address
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.orders.models import (
    CheckoutIdempotency,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    ReturnRequest,
    Shipment,
    ShipmentTracking,
    VendorOrder,
    VendorOrderStatus,
)
from src.apps.orders.services import cancel_order, create_order_from_cart, create_return_request, serialize_order
from src.apps.recommendations.models import RecommendationEventType
from src.apps.recommendations.services import record_recommendation_event
from src.apps.vendors.services import get_vendor_for_user

router = APIRouter()


class CheckoutRequest(BaseModel):
    address_id: str
    payment_method: PaymentMethod = PaymentMethod.COD
    payment_transaction_id: str | None = None
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


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(
    request: Request,
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    idempotency_key = request.headers.get("Idempotency-Key")
    order = await create_order_from_cart(
        user_id=current_user.id,
        address_id=decode_id_or_404(payload.address_id),
        payment_method=payload.payment_method,
        payment_transaction_id=decode_id_or_404(payload.payment_transaction_id) if payload.payment_transaction_id else None,
        notes=payload.notes,
        db=db,
        idempotency_key=idempotency_key,
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
    return {"order": await serialize_order(order, db)}


@router.get("/checkout/quote")
async def checkout_quote(
    address_id: str,
    payment_method: PaymentMethod = PaymentMethod.COD,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, decode_id_or_404(address_id))
    if address is None or address.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    from src.apps.commerce.services import get_or_create_cart, build_cart_payload
    from src.apps.logistics.services import quote_shipping

    cart = await get_or_create_cart(current_user.id, db)
    cart_payload = await build_cart_payload(cart, db)
    shipping_quote = await quote_shipping(address.pincode, payment_method == PaymentMethod.COD, db)
    taxable_amount = max(float(cart_payload["subtotal"]) - float(cart_payload["discount"]), 0.0)
    tax = round(taxable_amount * 0.13, 2)
    total = round(taxable_amount + float(shipping_quote["shipping_rate"]) + tax, 2)
    return {
        "cart": cart_payload,
        "shipping": shipping_quote,
        "tax": tax,
        "total": total,
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
        "issued_at": datetime.utcnow().isoformat(),
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
    return {"return_request_id": encode_id(return_request.id or 0), "status": return_request.status.value}


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
    vendor_order.updated_at = datetime.utcnow()

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
                order.delivered_at = datetime.utcnow()

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
        shipment.updated_at = datetime.utcnow()
        db.add(
            ShipmentTracking(
                shipment_id=shipment.id,
                status=shipment.status,
                location=payload.location or shipment.current_location,
                remarks=payload.remarks or payload.status.value,
            )
        )
    await db.commit()
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
    vendor_order.updated_at = datetime.utcnow()
    order = await db.get(Order, vendor_order.order_id)
    if order:
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
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
    return {"success": True}


@router.get("/admin/orders")
async def list_all_orders(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    orders = (await db.execute(select(Order).order_by(Order.created_at.desc()))).scalars().all()
    return {"items": [await serialize_order(order, db) for order in orders], "total": len(orders)}


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
