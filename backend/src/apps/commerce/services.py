from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Inventory, Product, ProductVariant
from src.apps.commerce.models import Cart, CartItem
from src.apps.promotions.models import Coupon
from src.apps.promotions.services import validate_coupon


async def get_or_create_cart(user_id: int, db: AsyncSession) -> Cart:
    cart = (await db.execute(select(Cart).where(Cart.user_id == user_id))).scalars().first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
    cart.updated_at = datetime.utcnow()
    return cart


async def build_cart_payload(cart: Cart, db: AsyncSession) -> dict[str, object]:
    items = (
        await db.execute(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.id.desc()))
    ).scalars().all()
    payload_items: list[dict[str, object]] = []
    subtotal = 0.0
    for item in items:
        variant = await db.get(ProductVariant, item.variant_id)
        if variant is None:
            continue
        product = await db.get(Product, variant.product_id)
        inventory_rows = (
            await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
        ).scalars().all()
        available_qty = sum(max(inv.quantity - inv.reserved_qty, 0) for inv in inventory_rows)
        line_total = round(item.quantity * variant.selling_price, 2)
        subtotal += line_total
        payload_items.append(
            {
                "id": _encode(item.id),
                "variant_id": _encode(variant.id or 0),
                "product_id": _encode(product.id or 0) if product else None,
                "product_name": product.name if product else "",
                "variant_name": variant.name,
                "sku": variant.sku,
                "quantity": item.quantity,
                "unit_price": variant.selling_price,
                "line_total": line_total,
                "available_qty": available_qty,
            }
        )

    discount = 0.0
    coupon_code = None
    if cart.coupon_id:
        coupon = await db.get(Coupon, cart.coupon_id)
        if coupon:
            discount = validate_coupon(coupon, subtotal)
            coupon_code = coupon.code

    return {
        "id": _encode(cart.id or 0),
        "coupon_id": _encode(cart.coupon_id) if cart.coupon_id else None,
        "coupon_code": coupon_code,
        "items": payload_items,
        "subtotal": round(subtotal, 2),
        "discount": discount,
        "total": round(max(subtotal - discount, 0.0), 2),
    }


def _encode(value: int | None) -> str | None:
    if value is None:
        return None
    from src.apps.iam.utils.hashid import encode_id

    return encode_id(value)
