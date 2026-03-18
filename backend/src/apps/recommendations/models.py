from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class RecommendationPlacement(str, Enum):
    HOME = "home"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"
    POST_PURCHASE = "post_purchase"
    SEARCH = "search"


class RecommendationEventType(str, Enum):
    VIEW = "view"
    CLICK = "click"
    SEARCH = "search"
    ADD_TO_CART = "add_to_cart"
    ADD_TO_WISHLIST = "add_to_wishlist"
    PURCHASE = "purchase"
    RATING = "rating"
    RECOMMENDATION_CLICK = "recommendation_click"


class UserProductEvent(SQLModel, table=True):
    __tablename__ = "user_product_events"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    product_id: Optional[int] = Field(default=None, foreign_key="products.id", index=True)
    event_type: RecommendationEventType = Field(default=RecommendationEventType.VIEW)
    placement: Optional[RecommendationPlacement] = Field(default=None)
    query_text: str = Field(default="", max_length=255)
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)


class ProductPopularity(SQLModel, table=True):
    __tablename__ = "product_popularity"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True, unique=True)
    score: float = Field(default=0, ge=0)
    view_count: int = Field(default=0, ge=0)
    purchase_count: int = Field(default=0, ge=0)
    cart_count: int = Field(default=0, ge=0)
    wishlist_count: int = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=utc_now)


class UserAffinity(SQLModel, table=True):
    __tablename__ = "user_affinity"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    brand_id: Optional[int] = Field(default=None, foreign_key="brands.id", index=True)
    score: float = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=utc_now)


class ProductSimilarity(SQLModel, table=True):
    __tablename__ = "product_similarity"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    similar_product_id: int = Field(foreign_key="products.id", index=True)
    score: float = Field(default=0, ge=0)
    reason_code: str = Field(default="", max_length=80)
    updated_at: datetime = Field(default_factory=utc_now)


class RecommendationCache(SQLModel, table=True):
    __tablename__ = "recommendation_cache"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    placement: RecommendationPlacement = Field(default=RecommendationPlacement.HOME)
    context_product_id: Optional[int] = Field(default=None, foreign_key="products.id", index=True)
    cache_key: str = Field(max_length=255, unique=True, index=True)
    product_ids_json: str = Field(default="[]")
    reasons_json: str = Field(default="{}")
    updated_at: datetime = Field(default_factory=utc_now)
