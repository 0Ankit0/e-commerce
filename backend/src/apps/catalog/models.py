from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ProductReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProductImportJobStatus(str, Enum):
    PREVIEW = "preview"
    COMMITTED = "committed"
    FAILED = "failed"


class ProductImportRowStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    IMPORTED = "imported"
    SKIPPED = "skipped"


class Category(SQLModel, table=True):
    __tablename__ = "categories"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=150, unique=True, index=True)
    level: int = Field(default=1, ge=1, le=3)
    description: str = Field(default="", max_length=1000)
    icon_url: str = Field(default="", max_length=500)
    image_url: str = Field(default="", max_length=500)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    attributes_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=utc_now)


class Brand(SQLModel, table=True):
    __tablename__ = "brands"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=150, unique=True, index=True)
    logo_url: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=1000)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class Product(SQLModel, table=True):
    __tablename__ = "products"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    category_id: int = Field(foreign_key="categories.id", index=True)
    brand_id: Optional[int] = Field(default=None, foreign_key="brands.id", index=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=180, unique=True, index=True)
    short_description: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=3000)
    specifications_json: str = Field(default="{}")
    status: ProductStatus = Field(default=ProductStatus.DRAFT)
    avg_rating: float = Field(default=0.0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    view_count: int = Field(default=0, ge=0)
    is_featured: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    published_at: Optional[datetime] = Field(default=None)


class ProductVariant(SQLModel, table=True):
    __tablename__ = "product_variants"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    sku: str = Field(max_length=120, unique=True, index=True)
    name: str = Field(default="", max_length=255)
    mrp: float = Field(ge=0)
    selling_price: float = Field(ge=0)
    cost_price: float = Field(default=0, ge=0)
    attributes_json: str = Field(default="{}")
    weight: float = Field(default=0, ge=0)
    dimensions_json: str = Field(default="{}")
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class ProductImage(SQLModel, table=True):
    __tablename__ = "product_images"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    url: str = Field(max_length=500)
    thumbnail_url: str = Field(default="", max_length=500)
    alt_text: str = Field(default="", max_length=255)
    position: int = Field(default=0)
    is_primary: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class Inventory(SQLModel, table=True):
    __tablename__ = "inventory"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    warehouse_id: Optional[int] = Field(default=None, foreign_key="warehouses.id", index=True)
    quantity: int = Field(default=0, ge=0)
    reserved_qty: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=0, ge=0)
    reorder_qty: int = Field(default=0, ge=0)
    last_restocked_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=utc_now)


class ProductReview(SQLModel, table=True):
    __tablename__ = "product_reviews"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    rating: int = Field(ge=1, le=5)
    title: str = Field(default="", max_length=255)
    body: str = Field(default="", max_length=2000)
    status: ProductReviewStatus = Field(default=ProductReviewStatus.APPROVED)
    created_at: datetime = Field(default_factory=utc_now)


class ProductImportJob(SQLModel, table=True):
    __tablename__ = "product_import_jobs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    created_by_user_id: int = Field(foreign_key="user.id", index=True)
    file_name: str = Field(default="", max_length=255)
    status: ProductImportJobStatus = Field(default=ProductImportJobStatus.PREVIEW)
    dry_run: bool = Field(default=True)
    total_rows: int = Field(default=0, ge=0)
    valid_rows: int = Field(default=0, ge=0)
    invalid_rows: int = Field(default=0, ge=0)
    summary_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)


class ProductImportRowResult(SQLModel, table=True):
    __tablename__ = "product_import_row_results"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="product_import_jobs.id", index=True)
    row_number: int = Field(ge=1)
    status: ProductImportRowStatus = Field(default=ProductImportRowStatus.VALID)
    sku: str = Field(default="", max_length=120)
    product_name: str = Field(default="", max_length=255)
    error_message: str = Field(default="", max_length=1000)
    payload_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
