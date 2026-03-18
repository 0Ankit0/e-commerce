from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.promotions.models import Coupon, CouponScope, CouponUsage


def validate_coupon(coupon: Coupon | None, subtotal: float) -> float:
    if coupon is None:
        return 0.0
    now = utc_now()
    if not coupon.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon is inactive")
    if coupon.valid_from and coupon.valid_from > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon is not active yet")
    if coupon.valid_to and coupon.valid_to < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon has expired")
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon usage limit reached")
    if subtotal < coupon.min_order_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order total does not meet coupon minimum",
        )

    if coupon.type.value == "percentage":
        discount = subtotal * (coupon.value / 100)
    else:
        discount = coupon.value
    if coupon.max_discount:
        discount = min(discount, coupon.max_discount)
    return round(max(discount, 0.0), 2)


async def calculate_coupon_discount(
    coupon: Coupon | None,
    subtotal: float,
    *,
    db: AsyncSession,
    user_id: int | None = None,
    product_ids: set[int] | None = None,
    category_ids: set[int] | None = None,
) -> float:
    discount = validate_coupon(coupon, subtotal)
    if coupon is None:
        return discount

    if user_id and coupon.per_user_limit:
        usage_count = (
            await db.execute(
                select(CouponUsage).where(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.user_id == user_id,
                )
            )
        ).scalars().all()
        if len(usage_count) >= coupon.per_user_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon per-user usage limit reached")

    applies_to = json.loads(coupon.applies_to_json or "{}")
    if coupon.scope == CouponScope.PRODUCT:
        allowed_products = {int(value) for value in applies_to.get("product_ids", [])}
        allowed_categories = {int(value) for value in applies_to.get("category_ids", [])}
        product_ids = product_ids or set()
        category_ids = category_ids or set()
        if allowed_products and product_ids.isdisjoint(allowed_products):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon does not apply to selected products")
        if allowed_categories and category_ids.isdisjoint(allowed_categories):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon does not apply to selected products")

    return discount


async def record_coupon_usage(
    *,
    coupon: Coupon | None,
    user_id: int,
    order_id: int,
    discount_amount: float,
    db: AsyncSession,
) -> None:
    if coupon is None:
        return
    db.add(
        CouponUsage(
            coupon_id=coupon.id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
    )


def serialize_coupon(coupon: Coupon) -> dict[str, object]:
    from src.apps.iam.utils.hashid import encode_id

    return {
        "id": encode_id(coupon.id or 0),
        "code": coupon.code,
        "description": coupon.description,
        "type": coupon.type.value,
        "value": coupon.value,
        "min_order_value": coupon.min_order_value,
        "max_discount": coupon.max_discount,
        "usage_limit": coupon.usage_limit,
        "per_user_limit": coupon.per_user_limit,
        "stackable": coupon.stackable,
        "scope": coupon.scope.value,
        "applies_to": json.loads(coupon.applies_to_json or "{}"),
        "used_count": coupon.used_count,
        "is_active": coupon.is_active,
        "valid_from": coupon.valid_from.isoformat() if coupon.valid_from else None,
        "valid_to": coupon.valid_to.isoformat() if coupon.valid_to else None,
    }
