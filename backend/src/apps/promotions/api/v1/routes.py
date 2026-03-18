from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.iam.api.deps import get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.promotions.models import Coupon, CouponScope, CouponType
from src.apps.promotions.services import calculate_coupon_discount, serialize_coupon, validate_coupon

router = APIRouter()


class CouponCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    description: str = ""
    type: CouponType = CouponType.PERCENTAGE
    scope: CouponScope = CouponScope.ORDER
    value: float = Field(gt=0)
    min_order_value: float = 0
    max_discount: float = 0
    usage_limit: int = 0
    per_user_limit: int = 0
    stackable: bool = False
    applies_to: dict[str, object] = {}
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool = True


@router.post("/admin/promotions/coupons", status_code=status.HTTP_201_CREATED)
async def create_coupon(
    payload: CouponCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(Coupon).where(Coupon.code == payload.code.upper()))).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon code already exists")
    coupon_data = payload.model_dump()
    coupon_data["applies_to_json"] = json.dumps(coupon_data.pop("applies_to"))
    coupon = Coupon(**coupon_data)
    coupon.code = coupon.code.upper()
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return {"coupon": serialize_coupon(coupon)}


@router.get("/admin/promotions")
async def list_coupons(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    coupons = (await db.execute(select(Coupon).order_by(Coupon.created_at.desc()))).scalars().all()
    return {"items": [serialize_coupon(coupon) for coupon in coupons], "total": len(coupons)}


@router.get("/promotions/coupons/validate")
async def validate_coupon_endpoint(
    code: str = Query(...),
    subtotal: float = Query(..., ge=0),
    user_id: str | None = Query(default=None),
    product_ids: list[str] = Query(default=[]),
    category_ids: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    coupon = (await db.execute(select(Coupon).where(Coupon.code == code.upper()))).scalars().first()
    if not product_ids and not category_ids:
        discount = validate_coupon(coupon, subtotal)
    else:
        from src.apps.iam.utils.hashid import decode_id_or_404

        discount = await calculate_coupon_discount(
            coupon,
            subtotal,
            db=db,
            user_id=decode_id_or_404(user_id) if user_id else None,
            product_ids={decode_id_or_404(product_id) for product_id in product_ids},
            category_ids={decode_id_or_404(category_id) for category_id in category_ids},
        )
    return {"code": code.upper(), "discount": discount, "coupon": serialize_coupon(coupon) if coupon else None}
