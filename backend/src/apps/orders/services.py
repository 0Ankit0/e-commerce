from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import hashlib
import json
import random
import string

from fastapi import HTTPException, status
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Inventory, Product, ProductVariant
from src.apps.commerce.models import Address, Cart, CartItem
from src.apps.commerce.services import build_cart_payload, calculate_tax_amount
from src.apps.core.time import utc_now
from src.apps.finance.models.payment import PaymentStatus, PaymentTransaction
from src.apps.finance.models.stored_value import WalletLedgerType
from src.apps.finance.services.stored_value import create_wallet_entry, create_wallet_payment_transaction, get_wallet_balance
from src.apps.logistics.services import quote_shipping
from src.apps.orders.references import build_order_reference
from src.apps.orders.models import (
    CheckoutIdempotency,
    CheckoutFinalization,
    InventoryReservation,
    InventoryReservationStatus,
    Order,
    OrderEvent,
    OrderItem,
    OrderNote,
    OrderPaymentStatus,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    RefundRecord,
    RefundStatus,
    ReturnEvent,
    ReturnRequest,
    ReturnStatus,
    Shipment,
    ShipmentTracking,
    VendorOrder,
    VendorOrderStatus,
)
from src.apps.promotions.models import Coupon
from src.apps.promotions.services import record_coupon_usage
from src.apps.vendors.models import CommissionTier, Vendor

RETURN_WINDOW_DAYS = 7
RETURN_TERMINAL_STATUSES = {ReturnStatus.REJECTED, ReturnStatus.REFUNDED}
RETURN_ACTIVE_STATUSES = {
    ReturnStatus.REQUESTED,
    ReturnStatus.APPROVED,
    ReturnStatus.REVERSE_PICKUP_ASSIGNED,
    ReturnStatus.PICKED_UP,
    ReturnStatus.RECEIVED,
}


def generate_reference(prefix: str, size: int = 10) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=size))
    return f"{prefix}-{suffix}"


def commission_rate(tier: CommissionTier) -> float:
    return {
        CommissionTier.STANDARD: 0.10,
        CommissionTier.PREMIUM: 0.07,
        CommissionTier.ENTERPRISE: 0.05,
    }[tier]


def build_checkout_boundary_key(*, user_id: int, quote_fingerprint: str, payment_transaction_id: int) -> str:
    raw = f"{user_id}:{quote_fingerprint}:{payment_transaction_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_order_from_cart(
    *,
    user_id: int,
    address_id: int,
    payment_method: PaymentMethod,
    payment_transaction_id: int | None,
    notes: str,
    db: AsyncSession,
    idempotency_key: str | None = None,
    request_fingerprint: str = "",
    shipping_option_code: str | None = None,
) -> Order:
    transaction = None
    boundary_key: str | None = None
    if payment_transaction_id:
        transaction = (
            await db.execute(
                select(PaymentTransaction).where(PaymentTransaction.id == payment_transaction_id).with_for_update()
            )
        ).scalars().first()
        if transaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment transaction not found")
        if transaction.user_id and transaction.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payment transaction does not belong to user")
        existing_order_for_tx = (
            await db.execute(select(Order).where(Order.payment_transaction_id == payment_transaction_id))
        ).scalars().first()
        if existing_order_for_tx is not None:
            if existing_order_for_tx.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment transaction already finalized")
            return existing_order_for_tx
        if request_fingerprint:
            boundary_key = build_checkout_boundary_key(
                user_id=user_id,
                quote_fingerprint=request_fingerprint,
                payment_transaction_id=payment_transaction_id,
            )
            existing_finalization = (
                await db.execute(
                    select(CheckoutFinalization).where(CheckoutFinalization.boundary_key == boundary_key)
                )
            ).scalars().first()
            if existing_finalization:
                existing_order = await db.get(Order, existing_finalization.order_id)
                if existing_order is not None:
                    return existing_order

    address = await db.get(Address, address_id)
    if address is None or address.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    if idempotency_key:
        existing_key = (
            await db.execute(
                select(CheckoutIdempotency).where(
                    CheckoutIdempotency.user_id == user_id,
                    CheckoutIdempotency.idempotency_key == idempotency_key,
                )
            )
        ).scalars().first()
        if existing_key:
            if request_fingerprint and existing_key.request_fingerprint and existing_key.request_fingerprint != request_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different checkout request",
                )
            existing_order = await db.get(Order, existing_key.order_id)
            if existing_order:
                return existing_order

    cart = (await db.execute(select(Cart).where(Cart.user_id == user_id))).scalars().first()
    if cart is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")
    cart_payload = await build_cart_payload(cart, db)
    if not cart_payload["items"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    payment_status = OrderPaymentStatus.PENDING
    order_status = OrderStatus.PENDING_PAYMENT
    if payment_method == PaymentMethod.COD:
        payment_status = OrderPaymentStatus.PENDING
        order_status = OrderStatus.CONFIRMED
    elif payment_method == PaymentMethod.WALLET:
        payment_status = OrderPaymentStatus.PAID
        order_status = OrderStatus.CONFIRMED
    elif payment_transaction_id:
        if transaction.status == PaymentStatus.COMPLETED:
            payment_status = OrderPaymentStatus.PAID
            order_status = OrderStatus.CONFIRMED
        elif transaction.status == PaymentStatus.FAILED:
            payment_status = OrderPaymentStatus.FAILED
            order_status = OrderStatus.PENDING_PAYMENT

    shipping_quote = await quote_shipping(
        address.pincode,
        payment_method == PaymentMethod.COD,
        db,
        shipping_option_code=shipping_option_code,
    )
    if not shipping_quote["serviceable"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Address is not serviceable")
    shipping_charge = round(float(shipping_quote["shipping_rate"]), 2)
    taxable_amount = max(float(cart_payload["subtotal"]) - float(cart_payload["discount"]), 0.0)
    tax_payload = await calculate_tax_amount(
        address=address,
        category_ids=set(cart_payload.get("category_ids", [])),
        taxable_amount=taxable_amount,
        db=db,
    )
    tax = float(tax_payload["tax"])
    order_total = round(taxable_amount + shipping_charge + tax, 2)
    if payment_method == PaymentMethod.WALLET:
        wallet_balance = await get_wallet_balance(user_id, db)
        required_amount = int(round(order_total * 100))
        if wallet_balance < required_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient wallet balance")

    coupon: Coupon | None = await db.get(Coupon, cart.coupon_id) if cart.coupon_id else None
    pricing_snapshot = {
        "subtotal": float(cart_payload["subtotal"]),
        "discount": float(cart_payload["discount"]),
        "shipping": shipping_charge,
        "tax": tax,
        "tax_rate": float(tax_payload["rate"]),
        "tax_rule": tax_payload["rule"],
        "total": order_total,
        "coupon_code": coupon.code if coupon else "",
        "shipping_option": shipping_quote.get("shipping_option"),
        "items": cart_payload["items"],
    }
    reserve_only = payment_status != OrderPaymentStatus.PAID and payment_method not in {PaymentMethod.COD, PaymentMethod.WALLET}
    order = Order(
        order_number=build_order_reference(),
        user_id=user_id,
        address_id=address_id,
        coupon_id=cart.coupon_id,
        status=order_status,
        payment_method=payment_method,
        payment_status=payment_status,
        subtotal=float(cart_payload["subtotal"]),
        discount=float(cart_payload["discount"]),
        shipping_charge=shipping_charge,
        tax=tax,
        total=order_total,
        coupon_code=coupon.code if coupon else "",
        coupon_discount=float(cart_payload["discount"]),
        notes=notes,
        pricing_snapshot_json=json.dumps(pricing_snapshot),
        payment_transaction_id=payment_transaction_id,
        confirmed_at=utc_now() if order_status == OrderStatus.CONFIRMED else None,
    )
    db.add(order)
    await db.flush()
    if payment_method == PaymentMethod.WALLET:
        wallet_tx = await create_wallet_payment_transaction(
            user_id=user_id,
            amount=int(round(order_total * 100)),
            purchase_order_id=order.order_number,
            purchase_order_name=f"Order {order.order_number}",
            return_url="wallet://orders",
            website_url="wallet://orders",
            idempotency_key=idempotency_key,
            db=db,
        )
        order.payment_transaction_id = wallet_tx.id
        await create_wallet_entry(
            user_id=user_id,
            amount=int(round(order_total * 100)),
            entry_type=WalletLedgerType.DEBIT,
            reference_type="order",
            reference_id=order.id,
            notes=f"Wallet checkout for {order.order_number}",
            db=db,
        )

    grouped_items: dict[int, list[dict[str, object]]] = defaultdict(list)
    cart_items = (
        await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    ).scalars().all()
    reservation_expiry = utc_now() + timedelta(minutes=30)

    await release_expired_inventory_reservations(db)
    for item in cart_items:
        variant = await db.get(ProductVariant, item.variant_id)
        if variant is None:
            continue
        product = await db.get(Product, variant.product_id)
        if product is None:
            continue
        inventory_rows = (
            await db.execute(
                select(Inventory)
                .where(Inventory.variant_id == variant.id)
                .order_by(Inventory.id.asc())
                .with_for_update()
            )
        ).scalars().all()
        available = sum(max(inv.quantity - inv.reserved_qty, 0) for inv in inventory_rows)
        if available < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory for SKU {variant.sku}",
            )
        remaining = item.quantity
        for inventory in inventory_rows:
            free_units = max(inventory.quantity - inventory.reserved_qty, 0)
            if free_units <= 0:
                continue
            deduction = min(remaining, free_units)
            inventory_update = (
                sa_update(Inventory)
                .where(
                    Inventory.id == inventory.id,
                    (Inventory.quantity - Inventory.reserved_qty) >= deduction,
                )
                .values(
                    reserved_qty=Inventory.reserved_qty + deduction if reserve_only else Inventory.reserved_qty,
                    quantity=Inventory.quantity if reserve_only else Inventory.quantity - deduction,
                    updated_at=utc_now(),
                )
            )
            update_result = await db.execute(inventory_update)
            if update_result.rowcount == 0:
                continue
            if reserve_only:
                db.add(
                    InventoryReservation(
                        user_id=user_id,
                        cart_id=cart.id,
                        order_id=order.id,
                        variant_id=variant.id,
                        quantity=deduction,
                        status=InventoryReservationStatus.ACTIVE,
                        reserved_until=reservation_expiry,
                        reason="checkout_pending_payment",
                        idempotency_key=idempotency_key or "",
                        metadata_json=json.dumps({"inventory_id": inventory.id}),
                    )
                )
            remaining -= deduction
            if remaining == 0:
                break
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory for SKU {variant.sku}",
            )
        grouped_items[product.vendor_id].append({"product": product, "variant": variant, "cart_item": item})

    for vendor_id, entries in grouped_items.items():
        vendor = await db.get(Vendor, vendor_id)
        if vendor is None:
            continue
        vendor_subtotal = round(sum(entry["variant"].selling_price * entry["cart_item"].quantity for entry in entries), 2)
        commission = round(vendor_subtotal * commission_rate(vendor.commission_tier), 2)
        vendor_order = VendorOrder(
            order_id=order.id,
            vendor_id=vendor_id,
            vendor_order_number=generate_reference("VND"),
            status=VendorOrderStatus.PENDING,
            subtotal=vendor_subtotal,
            commission=commission,
            vendor_amount=round(vendor_subtotal - commission, 2),
        )
        db.add(vendor_order)
        await db.flush()

        shipment = Shipment(
            order_id=order.id,
            vendor_order_id=vendor_order.id,
            awb=generate_reference("AWB", 12),
            status=order.status,
            current_location="Vendor warehouse",
            eta=utc_now() + timedelta(days=3),
        )
        db.add(shipment)
        await db.flush()
        db.add(
            ShipmentTracking(
                shipment_id=shipment.id,
                status=order.status,
                location="Vendor warehouse",
                remarks="Order created",
            )
        )

        for entry in entries:
            product: Product = entry["product"]
            variant: ProductVariant = entry["variant"]
            cart_item: CartItem = entry["cart_item"]
            db.add(
                OrderItem(
                    order_id=order.id,
                    vendor_order_id=vendor_order.id,
                    vendor_id=vendor_id,
                    product_id=product.id,
                    variant_id=variant.id,
                    product_name=product.name,
                    variant_name=variant.name,
                    quantity=cart_item.quantity,
                    unit_price=variant.selling_price,
                    total_price=round(variant.selling_price * cart_item.quantity, 2),
                    status=VendorOrderStatus.PENDING,
                )
            )

    db.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Order created"))
    await record_order_event(
        order_id=order.id,
        event_type="order.created",
        message="Order created",
        actor_user_id=user_id,
        payload={"payment_status": order.payment_status.value, "status": order.status.value},
        db=db,
    )

    for item in cart_items:
        await db.delete(item)
    cart.coupon_id = None
    cart.updated_at = utc_now()
    if coupon:
        coupon.used_count += 1
        await record_coupon_usage(
            coupon=coupon,
            user_id=user_id,
            order_id=order.id,
            discount_amount=float(cart_payload["discount"]),
            db=db,
        )
    if idempotency_key:
        db.add(
            CheckoutIdempotency(
                user_id=user_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                order_id=order.id,
            )
        )
    if payment_transaction_id and boundary_key:
        db.add(
            CheckoutFinalization(
                user_id=user_id,
                payment_transaction_id=payment_transaction_id,
                quote_fingerprint=request_fingerprint,
                boundary_key=boundary_key,
                order_id=order.id or 0,
            )
        )
    await db.flush()
    return order


async def cancel_order(order: Order, db: AsyncSession) -> Order:
    if order.status in {OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order can no longer be cancelled")
    if order.status == OrderStatus.CANCELLED:
        return order

    order_items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    await release_inventory_reservations_for_order(order, db, target_status=InventoryReservationStatus.RELEASED)
    for item in order_items:
        if order.payment_method in {PaymentMethod.COD, PaymentMethod.WALLET}:
            inventory = (
                await db.execute(select(Inventory).where(Inventory.variant_id == item.variant_id).with_for_update())
            ).scalars().first()
            if inventory:
                inventory.quantity += item.quantity
                inventory.updated_at = utc_now()
        item.status = VendorOrderStatus.CANCELLED

    vendor_orders = (await db.execute(select(VendorOrder).where(VendorOrder.order_id == order.id))).scalars().all()
    for vendor_order in vendor_orders:
        vendor_order.status = VendorOrderStatus.CANCELLED
        vendor_order.updated_at = utc_now()

    shipments = (await db.execute(select(Shipment).where(Shipment.order_id == order.id))).scalars().all()
    for shipment in shipments:
        shipment.status = OrderStatus.CANCELLED
        shipment.updated_at = utc_now()
        db.add(
            ShipmentTracking(
                shipment_id=shipment.id,
                status=OrderStatus.CANCELLED,
                location=shipment.current_location,
                remarks="Order cancelled",
            )
        )

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = utc_now()
    db.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Order cancelled"))
    await record_order_event(
        order_id=order.id,
        event_type="order.cancelled",
        message="Order cancelled",
        actor_user_id=order.user_id,
        payload={},
        db=db,
    )
    return order


async def create_return_request(
    *,
    order: Order,
    user_id: int,
    order_item_id: int | None,
    reason: str,
    details: str,
    quantity: int,
    refund_method: str,
    db: AsyncSession,
) -> ReturnRequest:
    if order.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order does not belong to user")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only delivered orders can be returned")
    delivered_at = order.delivered_at or order.created_at
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=utc_now().tzinfo)
    eligible_until = delivered_at + timedelta(days=RETURN_WINDOW_DAYS)
    if utc_now() > eligible_until:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return window has expired")
    if quantity < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return quantity must be at least 1")

    order_items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    if not order_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order has no items to return")

    target_item: OrderItem | None = None
    return_quantity = quantity
    if order_item_id is not None:
        target_item = await db.get(OrderItem, order_item_id)
        if target_item is None or target_item.order_id != order.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
        if target_item.status != VendorOrderStatus.DELIVERED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only delivered items can be returned")
        if quantity > target_item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return quantity exceeds ordered quantity")
        existing_returns = (
            await db.execute(
                select(ReturnRequest).where(
                    ReturnRequest.order_item_id == target_item.id,
                    ReturnRequest.status.in_(RETURN_ACTIVE_STATUSES),
                )
            )
        ).scalars().all()
        pending_quantity = sum(req.quantity for req in existing_returns)
        remaining_quantity = max(target_item.quantity - target_item.returned_quantity - pending_quantity, 0)
        if quantity > remaining_quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return quantity exceeds eligible quantity")
    else:
        eligible_items = [item for item in order_items if item.status == VendorOrderStatus.DELIVERED]
        if len(eligible_items) != len(order_items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order has mixed return eligibility; submit item-level returns for delivered items",
            )
        pending_returns = (
            await db.execute(
                select(ReturnRequest).where(
                    ReturnRequest.order_id == order.id,
                    ReturnRequest.order_item_id.is_not(None),
                    ReturnRequest.status.in_(RETURN_ACTIVE_STATUSES),
                )
            )
        ).scalars().all()
        pending_by_item_id = defaultdict(int)
        for req in pending_returns:
            if req.order_item_id:
                pending_by_item_id[req.order_item_id] += req.quantity
        remaining_totals = [max(item.quantity - item.returned_quantity - pending_by_item_id[item.id or 0], 0) for item in eligible_items]
        return_quantity = sum(remaining_totals)
        if return_quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No eligible quantity for return")

    return_request = ReturnRequest(
        order_id=order.id,
        order_item_id=order_item_id,
        user_id=user_id,
        reason=reason,
        details=details,
        quantity=return_quantity,
        refund_method=refund_method,
        return_window_days=RETURN_WINDOW_DAYS,
        eligible_until=eligible_until,
    )
    db.add(return_request)
    await db.flush()
    refund_amount = order.total if order_item_id is None else 0.0
    if target_item is not None:
        refund_amount = round(target_item.unit_price * return_quantity, 2)
    db.add(
        RefundRecord(
            return_request_id=return_request.id,
            payment_transaction_id=order.payment_transaction_id,
            amount=refund_amount,
            status=RefundStatus.PENDING,
        )
    )
    await record_return_event(
        return_request_id=return_request.id or 0,
        actor_user_id=user_id,
        event_type="return.requested",
        message="Return request created",
        payload={"refund_method": refund_method, "quantity": return_quantity},
        db=db,
    )
    return return_request


async def serialize_order(order: Order, db: AsyncSession) -> dict[str, object]:
    from src.apps.iam.utils.hashid import encode_id

    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    vendor_orders = (await db.execute(select(VendorOrder).where(VendorOrder.order_id == order.id))).scalars().all()
    shipments = (await db.execute(select(Shipment).where(Shipment.order_id == order.id))).scalars().all()
    return {
        "id": encode_id(order.id or 0),
        "order_number": order.order_number,
        "status": order.status.value,
        "payment_method": order.payment_method.value,
        "payment_status": order.payment_status.value,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "shipping_charge": order.shipping_charge,
        "tax": order.tax,
        "total": order.total,
        "coupon_code": order.coupon_code,
        "pricing_snapshot": json.loads(order.pricing_snapshot_json or "{}"),
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": encode_id(item.id or 0),
                "vendor_id": encode_id(item.vendor_id),
                "product_id": encode_id(item.product_id),
                "variant_id": encode_id(item.variant_id),
                "product_name": item.product_name,
                "variant_name": item.variant_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "status": item.status.value,
            }
            for item in items
        ],
        "vendor_orders": [
            {
                "id": encode_id(vendor_order.id or 0),
                "vendor_id": encode_id(vendor_order.vendor_id),
                "vendor_order_number": vendor_order.vendor_order_number,
                "status": vendor_order.status.value,
                "subtotal": vendor_order.subtotal,
                "commission": vendor_order.commission,
                "vendor_amount": vendor_order.vendor_amount,
            }
            for vendor_order in vendor_orders
        ],
        "shipments": [
            {
                "id": encode_id(shipment.id or 0),
                "awb": shipment.awb,
                "status": shipment.status.value,
                "current_location": shipment.current_location,
                "eta": shipment.eta.isoformat() if shipment.eta else None,
            }
            for shipment in shipments
        ],
    }


async def record_order_event(
    *,
    order_id: int,
    event_type: str,
    message: str,
    actor_user_id: int | None,
    payload: dict[str, object],
    db: AsyncSession,
) -> None:
    db.add(
        OrderEvent(
            order_id=order_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            message=message,
            payload_json=json.dumps(payload),
        )
    )


async def add_order_note(
    *,
    order_id: int,
    note: str,
    db: AsyncSession,
    created_by_user_id: int | None = None,
    note_type: str = "internal",
    is_customer_visible: bool = False,
) -> OrderNote:
    order_note = OrderNote(
        order_id=order_id,
        created_by_user_id=created_by_user_id,
        note_type=note_type,
        note=note,
        is_customer_visible=is_customer_visible,
    )
    db.add(order_note)
    await db.flush()
    return order_note


async def list_order_events(order_id: int, db: AsyncSession) -> list[OrderEvent]:
    return (
        await db.execute(select(OrderEvent).where(OrderEvent.order_id == order_id).order_by(OrderEvent.created_at.asc()))
    ).scalars().all()


async def list_order_notes(order_id: int, db: AsyncSession) -> list[OrderNote]:
    return (
        await db.execute(select(OrderNote).where(OrderNote.order_id == order_id).order_by(OrderNote.created_at.desc()))
    ).scalars().all()


async def record_return_event(
    *,
    return_request_id: int,
    actor_user_id: int | None,
    event_type: str,
    message: str,
    payload: dict[str, object],
    db: AsyncSession,
) -> None:
    db.add(
        ReturnEvent(
            return_request_id=return_request_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            message=message,
            payload_json=json.dumps(payload),
        )
    )


async def list_return_events(return_request_id: int, db: AsyncSession) -> list[ReturnEvent]:
    return (
        await db.execute(
            select(ReturnEvent).where(ReturnEvent.return_request_id == return_request_id).order_by(ReturnEvent.created_at.asc())
        )
    ).scalars().all()


async def update_return_request_status(
    *,
    return_request: ReturnRequest,
    status_value: ReturnStatus,
    db: AsyncSession,
    actor_user_id: int | None = None,
    message: str = "",
    payload: dict[str, object] | None = None,
) -> ReturnRequest:
    transition_map: dict[ReturnStatus, set[ReturnStatus]] = {
        ReturnStatus.REQUESTED: {ReturnStatus.APPROVED, ReturnStatus.REJECTED},
        ReturnStatus.APPROVED: {ReturnStatus.REVERSE_PICKUP_ASSIGNED, ReturnStatus.PICKED_UP, ReturnStatus.REJECTED},
        ReturnStatus.REVERSE_PICKUP_ASSIGNED: {ReturnStatus.PICKED_UP, ReturnStatus.REJECTED},
        ReturnStatus.PICKED_UP: {ReturnStatus.RECEIVED, ReturnStatus.REJECTED},
        ReturnStatus.RECEIVED: {ReturnStatus.REFUNDED, ReturnStatus.REJECTED},
    }
    if return_request.status in RETURN_TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return request is already closed")
    allowed_statuses = transition_map.get(return_request.status, set())
    if status_value != return_request.status and status_value not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition return from {return_request.status.value} to {status_value.value}",
        )

    refund = (
        await db.execute(select(RefundRecord).where(RefundRecord.return_request_id == return_request.id))
    ).scalars().first()
    order = await db.get(Order, return_request.order_id)
    order_item = await db.get(OrderItem, return_request.order_item_id) if return_request.order_item_id else None

    if status_value == ReturnStatus.RECEIVED and refund is not None:
        refund.status = RefundStatus.PENDING
        await record_return_event(
            return_request_id=return_request.id or 0,
            actor_user_id=actor_user_id,
            event_type="return.refund_initiated",
            message="Refund initiated after return inspection",
            payload={"amount": refund.amount},
            db=db,
        )
    if status_value == ReturnStatus.REJECTED and refund is not None:
        refund.status = RefundStatus.FAILED
    if status_value == ReturnStatus.REFUNDED:
        if return_request.status != ReturnStatus.RECEIVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return must be received before refund settlement")
        if refund is not None:
            refund.status = RefundStatus.COMPLETED
        if return_request.refund_method == "wallet" and refund is not None and refund.amount > 0:
            await create_wallet_entry(
                user_id=return_request.user_id,
                amount=int(round(refund.amount * 100)),
                entry_type=WalletLedgerType.REFUND,
                reference_type="return_request",
                reference_id=return_request.id,
                notes=f"Wallet refund for return {return_request.id}",
                db=db,
            )
        if order_item is not None:
            order_item.returned_quantity = min(order_item.quantity, order_item.returned_quantity + return_request.quantity)
            if order_item.returned_quantity >= order_item.quantity:
                order_item.status = VendorOrderStatus.RETURNED
        if order is not None:
            order.payment_status = OrderPaymentStatus.REFUNDED
            if order_item is None:
                order.status = OrderStatus.RETURNED
            else:
                order_items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
                if order_items and all(item.returned_quantity >= item.quantity for item in order_items):
                    order.status = OrderStatus.RETURNED

    return_request.status = status_value
    if status_value in {ReturnStatus.REJECTED, ReturnStatus.REFUNDED}:
        return_request.resolved_at = utc_now()
    await record_return_event(
        return_request_id=return_request.id or 0,
        actor_user_id=actor_user_id,
        event_type=f"return.{status_value.value}",
        message=message or f"Return marked {status_value.value}",
        payload=payload or {},
        db=db,
    )
    return return_request


async def commit_inventory_reservations_for_order(order: Order, db: AsyncSession) -> None:
    reservations = (
        await db.execute(
            select(InventoryReservation).where(
                InventoryReservation.order_id == order.id,
                InventoryReservation.status == InventoryReservationStatus.ACTIVE,
            )
            .order_by(InventoryReservation.id.asc())
            .with_for_update()
        )
    ).scalars().all()
    for reservation in reservations:
        metadata = json.loads(reservation.metadata_json or "{}")
        inventory = (
            await db.get(Inventory, metadata.get("inventory_id"), with_for_update=True) if metadata.get("inventory_id") else None
        )
        if inventory:
            inventory.reserved_qty = max(inventory.reserved_qty - reservation.quantity, 0)
            inventory.quantity = max(inventory.quantity - reservation.quantity, 0)
            inventory.updated_at = utc_now()
        reservation.status = InventoryReservationStatus.COMMITTED
        reservation.updated_at = utc_now()


async def confirm_order_payment(order: Order, db: AsyncSession) -> None:
    if order.payment_status == OrderPaymentStatus.PAID and order.status == OrderStatus.CONFIRMED:
        return
    await release_inventory_reservations_for_order(
        order,
        db,
        target_status=InventoryReservationStatus.EXPIRED,
        only_expired=True,
    )
    remaining_active = (
        await db.execute(
            select(InventoryReservation).where(
                InventoryReservation.order_id == order.id,
                InventoryReservation.status == InventoryReservationStatus.ACTIVE,
            )
        )
    ).scalars().all()
    if not remaining_active and order.status == OrderStatus.PENDING_PAYMENT:
        order.payment_status = OrderPaymentStatus.FAILED
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = order.cancelled_at or utc_now()
        db.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Payment callback received after reservation expiry"))
        await record_order_event(
            order_id=order.id,
            event_type="payment.expired",
            message="Payment callback received after reservation expiry",
            actor_user_id=order.user_id,
            payload={},
            db=db,
        )
        return
    await commit_inventory_reservations_for_order(order, db)
    order.payment_status = OrderPaymentStatus.PAID
    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = order.confirmed_at or utc_now()
    db.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Payment confirmed"))
    await record_order_event(
        order_id=order.id,
        event_type="payment.confirmed",
        message="Payment confirmed and inventory committed",
        actor_user_id=order.user_id,
        payload={},
        db=db,
    )


async def release_inventory_reservations_for_order(
    order: Order,
    db: AsyncSession,
    *,
    target_status: InventoryReservationStatus,
    only_expired: bool = False,
) -> int:
    stmt = (
        select(InventoryReservation)
        .where(
            InventoryReservation.order_id == order.id,
            InventoryReservation.status == InventoryReservationStatus.ACTIVE,
        )
        .order_by(InventoryReservation.id.asc())
        .with_for_update()
    )
    reservations = (await db.execute(stmt)).scalars().all()
    released_count = 0
    now = utc_now()
    for reservation in reservations:
        reserved_until = reservation.reserved_until
        if reserved_until.tzinfo is None:
            reserved_until = reserved_until.replace(tzinfo=now.tzinfo)
        if only_expired and reserved_until > now:
            continue
        metadata = json.loads(reservation.metadata_json or "{}")
        inventory = (
            await db.get(Inventory, metadata.get("inventory_id"), with_for_update=True) if metadata.get("inventory_id") else None
        )
        if inventory:
            inventory.reserved_qty = max(inventory.reserved_qty - reservation.quantity, 0)
            inventory.updated_at = now
        reservation.status = target_status
        reservation.updated_at = now
        released_count += 1
    return released_count


async def release_expired_inventory_reservations(db: AsyncSession) -> int:
    now = utc_now()
    expired_reservations = (
        await db.execute(
            select(InventoryReservation)
            .where(
                InventoryReservation.status == InventoryReservationStatus.ACTIVE,
                InventoryReservation.reserved_until <= now,
            )
            .order_by(InventoryReservation.id.asc())
            .with_for_update()
        )
    ).scalars().all()
    released_count = 0
    for reservation in expired_reservations:
        metadata = json.loads(reservation.metadata_json or "{}")
        inventory = (
            await db.get(Inventory, metadata.get("inventory_id"), with_for_update=True) if metadata.get("inventory_id") else None
        )
        if inventory:
            inventory.reserved_qty = max(inventory.reserved_qty - reservation.quantity, 0)
            inventory.updated_at = now
        reservation.status = InventoryReservationStatus.EXPIRED
        reservation.updated_at = now
        released_count += 1
    return released_count
