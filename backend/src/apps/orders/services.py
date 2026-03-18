from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import json
import random
import string

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Inventory, Product, ProductVariant
from src.apps.commerce.models import Address, Cart, CartItem
from src.apps.commerce.services import build_cart_payload
from src.apps.finance.models.payment import PaymentStatus, PaymentTransaction
from src.apps.finance.models.stored_value import WalletLedgerType
from src.apps.finance.services.stored_value import create_wallet_entry, create_wallet_payment_transaction, get_wallet_balance
from src.apps.logistics.services import quote_shipping
from src.apps.orders.models import (
    CheckoutIdempotency,
    Order,
    OrderItem,
    OrderPaymentStatus,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    RefundRecord,
    RefundStatus,
    ReturnRequest,
    ReturnStatus,
    Shipment,
    ShipmentTracking,
    VendorOrder,
    VendorOrderStatus,
)
from src.apps.promotions.models import Coupon
from src.apps.vendors.models import CommissionTier, Vendor


def generate_reference(prefix: str, size: int = 10) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=size))
    return f"{prefix}-{suffix}"


def commission_rate(tier: CommissionTier) -> float:
    return {
        CommissionTier.STANDARD: 0.10,
        CommissionTier.PREMIUM: 0.07,
        CommissionTier.ENTERPRISE: 0.05,
    }[tier]


async def create_order_from_cart(
    *,
    user_id: int,
    address_id: int,
    payment_method: PaymentMethod,
    payment_transaction_id: int | None,
    notes: str,
    db: AsyncSession,
    idempotency_key: str | None = None,
) -> Order:
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
        transaction = await db.get(PaymentTransaction, payment_transaction_id)
        if transaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment transaction not found")
        if transaction.status == PaymentStatus.COMPLETED:
            payment_status = OrderPaymentStatus.PAID
            order_status = OrderStatus.CONFIRMED
        elif transaction.status == PaymentStatus.FAILED:
            payment_status = OrderPaymentStatus.FAILED
            order_status = OrderStatus.PENDING_PAYMENT

    shipping_quote = await quote_shipping(address.pincode, payment_method == PaymentMethod.COD, db)
    shipping_charge = round(float(shipping_quote["shipping_rate"]), 2)
    taxable_amount = max(float(cart_payload["subtotal"]) - float(cart_payload["discount"]), 0.0)
    tax = round(taxable_amount * 0.13, 2)
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
        "tax_rate": 0.13,
        "total": order_total,
        "coupon_code": coupon.code if coupon else "",
        "items": cart_payload["items"],
    }
    order = Order(
        order_number=generate_reference("ORD"),
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
        confirmed_at=datetime.utcnow() if order_status == OrderStatus.CONFIRMED else None,
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
    for item in cart_items:
        variant = await db.get(ProductVariant, item.variant_id)
        if variant is None:
            continue
        product = await db.get(Product, variant.product_id)
        if product is None:
            continue
        inventory_rows = (
            await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
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
            inventory.quantity -= deduction
            inventory.updated_at = datetime.utcnow()
            remaining -= deduction
            if remaining == 0:
                break
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
            eta=datetime.utcnow() + timedelta(days=3),
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

    for item in cart_items:
        await db.delete(item)
    cart.coupon_id = None
    cart.updated_at = datetime.utcnow()
    if coupon:
        coupon.used_count += 1
    if idempotency_key:
        db.add(CheckoutIdempotency(user_id=user_id, idempotency_key=idempotency_key, order_id=order.id))
    await db.flush()
    return order


async def cancel_order(order: Order, db: AsyncSession) -> Order:
    if order.status in {OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order can no longer be cancelled")
    if order.status == OrderStatus.CANCELLED:
        return order

    order_items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    for item in order_items:
        inventory = (
            await db.execute(select(Inventory).where(Inventory.variant_id == item.variant_id))
        ).scalars().first()
        if inventory:
            inventory.quantity += item.quantity
            inventory.updated_at = datetime.utcnow()
        item.status = VendorOrderStatus.CANCELLED

    vendor_orders = (await db.execute(select(VendorOrder).where(VendorOrder.order_id == order.id))).scalars().all()
    for vendor_order in vendor_orders:
        vendor_order.status = VendorOrderStatus.CANCELLED
        vendor_order.updated_at = datetime.utcnow()

    shipments = (await db.execute(select(Shipment).where(Shipment.order_id == order.id))).scalars().all()
    for shipment in shipments:
        shipment.status = OrderStatus.CANCELLED
        shipment.updated_at = datetime.utcnow()
        db.add(
            ShipmentTracking(
                shipment_id=shipment.id,
                status=OrderStatus.CANCELLED,
                location=shipment.current_location,
                remarks="Order cancelled",
            )
        )

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    db.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Order cancelled"))
    return order


async def create_return_request(
    *,
    order: Order,
    user_id: int,
    order_item_id: int | None,
    reason: str,
    details: str,
    refund_method: str,
    db: AsyncSession,
) -> ReturnRequest:
    if order.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order does not belong to user")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only delivered orders can be returned")

    return_request = ReturnRequest(
        order_id=order.id,
        order_item_id=order_item_id,
        user_id=user_id,
        reason=reason,
        details=details,
        refund_method=refund_method,
    )
    db.add(return_request)
    await db.flush()
    refund_amount = order.total if order_item_id is None else 0.0
    if order_item_id is not None:
        item = await db.get(OrderItem, order_item_id)
        refund_amount = item.total_price if item else 0.0
    db.add(
        RefundRecord(
            return_request_id=return_request.id,
            payment_transaction_id=order.payment_transaction_id,
            amount=refund_amount,
            status=RefundStatus.PENDING,
        )
    )
    if refund_method == "wallet":
        await create_wallet_entry(
            user_id=user_id,
            amount=int(round(refund_amount * 100)),
            entry_type=WalletLedgerType.REFUND,
            reference_type="return_request",
            reference_id=return_request.id,
            notes=f"Wallet refund for order {order.order_number}",
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
