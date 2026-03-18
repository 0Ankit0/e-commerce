from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class CouponType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class Coupon(SQLModel, table=True):
    __tablename__ = "coupons"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=80, unique=True, index=True)
    description: str = Field(default="", max_length=255)
    type: CouponType = Field(default=CouponType.PERCENTAGE)
    value: float = Field(ge=0)
    min_order_value: float = Field(default=0, ge=0)
    max_discount: float = Field(default=0, ge=0)
    valid_from: Optional[datetime] = Field(default=None)
    valid_to: Optional[datetime] = Field(default=None)
    usage_limit: int = Field(default=0, ge=0)
    used_count: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
