from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from src.apps.promotions.models import Coupon


def validate_coupon(coupon: Coupon | None, subtotal: float) -> float:
    if coupon is None:
        return 0.0
    now = datetime.utcnow()
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
        "used_count": coupon.used_count,
        "is_active": coupon.is_active,
        "valid_from": coupon.valid_from.isoformat() if coupon.valid_from else None,
        "valid_to": coupon.valid_to.isoformat() if coupon.valid_to else None,
    }
