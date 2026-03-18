from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class Address(SQLModel, table=True):
    __tablename__ = "addresses"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(max_length=255)
    phone: str = Field(max_length=20)
    line1: str = Field(max_length=255)
    line2: str = Field(default="", max_length=255)
    city: str = Field(max_length=120)
    state: str = Field(max_length=120)
    pincode: str = Field(max_length=20)
    country: str = Field(default="Nepal", max_length=120)
    landmark: str = Field(default="", max_length=255)
    type: str = Field(default="home", max_length=20)
    is_default: bool = Field(default=False)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class Cart(SQLModel, table=True):
    __tablename__ = "carts"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    coupon_id: Optional[int] = Field(default=None, foreign_key="coupons.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="carts.id", index=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    quantity: int = Field(default=1, ge=1)
    price_at_add: float = Field(default=0, ge=0)
    added_at: datetime = Field(default_factory=utc_now)


class WishlistItem(SQLModel, table=True):
    __tablename__ = "wishlist_items"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class TaxRule(SQLModel, table=True):
    __tablename__ = "tax_rules"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    country: str = Field(default="Nepal", max_length=120, index=True)
    state: str = Field(default="", max_length=120, index=True)
    city: str = Field(default="", max_length=120)
    pincode_prefix: str = Field(default="", max_length=20, index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    rate: float = Field(default=0.13, ge=0)
    priority: int = Field(default=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
