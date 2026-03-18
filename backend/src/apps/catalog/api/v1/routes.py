from __future__ import annotations

import csv
import io
import json
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.core.time import utc_now
from src.apps.catalog.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImportJob,
    ProductImportJobStatus,
    ProductImportRowResult,
    ProductImportRowStatus,
    ProductImage,
    ProductReview,
    ProductReviewStatus,
    ProductStatus,
    ProductVariant,
)
from src.apps.catalog.services import (
    ensure_product_active,
    ensure_variant_pricing,
    recalculate_product_rating,
    serialize_product,
)
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.recommendations.models import RecommendationEventType, UserProductEvent
from src.apps.vendors.models import Vendor
from src.apps.vendors.services import ensure_vendor_active, get_vendor_for_user

router = APIRouter()


class CategoryCreateRequest(BaseModel):
    name: str
    slug: str
    parent_id: str | None = None
    level: int = Field(default=1, ge=1, le=3)
    description: str = ""
    attributes: list[dict[str, object]] = []
    sort_order: int = 0


class BrandCreateRequest(BaseModel):
    name: str
    slug: str
    description: str = ""
    logo_url: str = ""


class InventoryUpdateRequest(BaseModel):
    quantity: int = Field(ge=0)
    reorder_level: int = Field(default=0, ge=0)
    reorder_qty: int = Field(default=0, ge=0)


class VariantPayload(BaseModel):
    sku: str
    name: str
    mrp: float = Field(ge=0)
    selling_price: float = Field(ge=0)
    cost_price: float = Field(default=0, ge=0)
    attributes: dict[str, object] = {}
    quantity: int = Field(default=0, ge=0)
    is_default: bool = False


class ProductImagePayload(BaseModel):
    url: str
    thumbnail_url: str = ""
    alt_text: str = ""
    position: int = 0
    is_primary: bool = False


class ProductCreateRequest(BaseModel):
    category_id: str
    brand_id: str | None = None
    name: str
    slug: str
    short_description: str = ""
    description: str = ""
    specifications: dict[str, object] = {}
    is_featured: bool = False
    status: ProductStatus = ProductStatus.PENDING
    variants: list[VariantPayload]
    images: list[ProductImagePayload] = []


class ProductReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = ""
    body: str = ""


IMPORT_TEMPLATE_HEADERS = [
    "product_slug",
    "product_name",
    "category_slug",
    "brand_slug",
    "short_description",
    "description",
    "status",
    "sku",
    "variant_name",
    "mrp",
    "selling_price",
    "cost_price",
    "quantity",
    "is_default",
    "image_url",
]


def _read_import_rows(csv_content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_content))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty")
    missing = [field for field in IMPORT_TEMPLATE_HEADERS if field not in reader.fieldnames]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"CSV is missing required columns: {', '.join(missing)}")
    return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


async def _preview_product_import(
    *,
    csv_content: str,
    vendor: Vendor,
    current_user: User,
    db: AsyncSession,
    dry_run: bool,
) -> dict[str, object]:
    rows = _read_import_rows(csv_content)
    category_by_slug = {row.slug: row for row in (await db.execute(select(Category))).scalars().all()}
    brand_by_slug = {row.slug: row for row in (await db.execute(select(Brand))).scalars().all()}
    job = ProductImportJob(
        vendor_id=vendor.id,
        created_by_user_id=current_user.id,
        file_name="upload.csv",
        status=ProductImportJobStatus.PREVIEW if dry_run else ProductImportJobStatus.COMMITTED,
        dry_run=dry_run,
        total_rows=len(rows),
    )
    db.add(job)
    await db.flush()

    grouped: dict[str, list[dict[str, str]]] = {}
    valid_rows = 0
    invalid_rows = 0
    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        error_messages: list[str] = []
        if not row["product_slug"]:
            error_messages.append("product_slug is required")
        if not row["product_name"]:
            error_messages.append("product_name is required")
        if row["category_slug"] not in category_by_slug:
            error_messages.append("category_slug does not exist")
        if row["brand_slug"] and row["brand_slug"] not in brand_by_slug:
            error_messages.append("brand_slug does not exist")
        try:
            if float(row["selling_price"]) > float(row["mrp"]):
                error_messages.append("selling_price cannot exceed mrp")
        except ValueError:
            error_messages.append("mrp and selling_price must be numeric")
        if not row["sku"]:
            error_messages.append("sku is required")

        status_value = ProductImportRowStatus.INVALID if error_messages else ProductImportRowStatus.VALID
        db.add(
            ProductImportRowResult(
                job_id=job.id,
                row_number=index,
                status=status_value,
                sku=row["sku"],
                product_name=row["product_name"],
                error_message="; ".join(error_messages),
                payload_json=json.dumps(row),
            )
        )
        if error_messages:
            invalid_rows += 1
            errors.extend(error_messages)
        else:
            valid_rows += 1
            grouped.setdefault(row["product_slug"], []).append(row)

    job.valid_rows = valid_rows
    job.invalid_rows = invalid_rows
    job.summary_json = json.dumps({"errors": errors[:20]})

    created_products: list[str] = []
    if not dry_run:
        for product_slug, grouped_rows in grouped.items():
            first_row = grouped_rows[0]
            category = category_by_slug[first_row["category_slug"]]
            brand = brand_by_slug.get(first_row["brand_slug"]) if first_row["brand_slug"] else None
            product = Product(
                vendor_id=vendor.id,
                category_id=category.id,
                brand_id=brand.id if brand else None,
                name=first_row["product_name"],
                slug=product_slug,
                short_description=first_row["short_description"],
                description=first_row["description"],
                status=ProductStatus(first_row["status"] or ProductStatus.PENDING.value),
                published_at=utc_now() if (first_row["status"] or ProductStatus.PENDING.value) == ProductStatus.ACTIVE.value else None,
            )
            db.add(product)
            await db.flush()
            if first_row["image_url"]:
                db.add(ProductImage(product_id=product.id, url=first_row["image_url"], is_primary=True))
            for row in grouped_rows:
                variant = ProductVariant(
                    product_id=product.id,
                    sku=row["sku"],
                    name=row["variant_name"],
                    mrp=float(row["mrp"]),
                    selling_price=float(row["selling_price"]),
                    cost_price=float(row["cost_price"] or 0),
                    is_default=str(row["is_default"]).lower() in {"1", "true", "yes"},
                )
                ensure_variant_pricing(variant)
                db.add(variant)
                await db.flush()
                db.add(
                    Inventory(
                        variant_id=variant.id,
                        quantity=int(row["quantity"] or 0),
                    )
                )
            created_products.append(product.slug)
        vendor.product_count += len(created_products)

    return {
        "job_id": encode_id(job.id or 0),
        "total_rows": len(rows),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "created_products": created_products,
    }


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    categories = (
        await db.execute(select(Category).where(Category.is_active == True).order_by(Category.level.asc(), Category.sort_order.asc()))
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(category.id or 0),
                "parent_id": encode_id(category.parent_id) if category.parent_id else None,
                "name": category.name,
                "slug": category.slug,
                "level": category.level,
                "description": category.description,
                "attributes": json.loads(category.attributes_json or "[]"),
            }
            for category in categories
        ],
        "total": len(categories),
    }


@router.post("/admin/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    category = Category(
        name=payload.name,
        slug=payload.slug,
        parent_id=decode_id_or_404(payload.parent_id) if payload.parent_id else None,
        level=payload.level,
        description=payload.description,
        sort_order=payload.sort_order,
        attributes_json=json.dumps(payload.attributes),
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return {"category": {"id": encode_id(category.id or 0), "name": category.name, "slug": category.slug}}


@router.patch("/admin/categories/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    category = await db.get(Category, decode_id_or_404(category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    category.name = payload.name
    category.slug = payload.slug
    category.parent_id = decode_id_or_404(payload.parent_id) if payload.parent_id else None
    category.level = payload.level
    category.description = payload.description
    category.sort_order = payload.sort_order
    category.attributes_json = json.dumps(payload.attributes)
    await db.commit()
    return {"category": {"id": encode_id(category.id or 0), "name": category.name, "slug": category.slug}}


@router.delete("/admin/categories/{category_id}")
async def delete_category(
    category_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    category = await db.get(Category, decode_id_or_404(category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    category.is_active = False
    await db.commit()
    return {"success": True}


@router.get("/brands")
async def list_brands(db: AsyncSession = Depends(get_db)):
    brands = (await db.execute(select(Brand).where(Brand.is_active == True).order_by(Brand.name.asc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(brand.id or 0),
                "name": brand.name,
                "slug": brand.slug,
                "description": brand.description,
            }
            for brand in brands
        ],
        "total": len(brands),
    }


@router.post("/admin/catalog/brands", status_code=status.HTTP_201_CREATED)
async def create_brand(
    payload: BrandCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    brand = Brand(**payload.model_dump())
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return {"brand": {"id": encode_id(brand.id or 0), "name": brand.name, "slug": brand.slug}}


@router.patch("/admin/catalog/brands/{brand_id}")
async def update_brand(
    brand_id: str,
    payload: BrandCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    brand = await db.get(Brand, decode_id_or_404(brand_id))
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    brand.name = payload.name
    brand.slug = payload.slug
    brand.description = payload.description
    brand.logo_url = payload.logo_url
    await db.commit()
    return {"brand": {"id": encode_id(brand.id or 0), "name": brand.name, "slug": brand.slug}}


@router.delete("/admin/catalog/brands/{brand_id}")
async def delete_brand(
    brand_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    brand = await db.get(Brand, decode_id_or_404(brand_id))
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    brand.is_active = False
    await db.commit()
    return {"success": True}


@router.post("/vendor/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    ensure_vendor_active(vendor)
    if not payload.variants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one variant is required")
    category = await db.get(Category, decode_id_or_404(payload.category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    brand_id = decode_id_or_404(payload.brand_id) if payload.brand_id else None
    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand_id,
        name=payload.name,
        slug=payload.slug,
        short_description=payload.short_description,
        description=payload.description,
        specifications_json=json.dumps(payload.specifications),
        is_featured=payload.is_featured,
        status=payload.status,
        published_at=utc_now() if payload.status == ProductStatus.ACTIVE else None,
    )
    db.add(product)
    await db.flush()

    for image in payload.images:
        db.add(ProductImage(product_id=product.id, **image.model_dump()))
    for variant_payload in payload.variants:
        variant = ProductVariant(
            product_id=product.id,
            sku=variant_payload.sku,
            name=variant_payload.name,
            mrp=variant_payload.mrp,
            selling_price=variant_payload.selling_price,
            cost_price=variant_payload.cost_price,
            attributes_json=json.dumps(variant_payload.attributes),
            is_default=variant_payload.is_default,
        )
        ensure_variant_pricing(variant)
        db.add(variant)
        await db.flush()
        db.add(Inventory(variant_id=variant.id, quantity=variant_payload.quantity))
    vendor.product_count += 1
    await db.commit()
    await db.refresh(product)
    return {"product": await serialize_product(product, db)}


@router.get("/vendor/products/import/template")
async def get_product_import_template(
    _: User = Depends(get_current_user),
):
    sample = ",".join(IMPORT_TEMPLATE_HEADERS) + "\n" + ",".join(
        [
            "wireless-headphones",
            "Wireless Headphones",
            "electronics",
            "acme-audio",
            "Noise cancelling",
            "Premium over-ear wireless headphones",
            "pending",
            "WH-001",
            "Black",
            "120",
            "99",
            "0",
            "5",
            "true",
            "https://example.com/headphones.jpg",
        ]
    )
    return {"headers": IMPORT_TEMPLATE_HEADERS, "sample_csv": sample}


@router.post("/vendor/products/import/preview")
async def preview_product_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    ensure_vendor_active(vendor)
    preview = await _preview_product_import(
        csv_content=(await file.read()).decode("utf-8"),
        vendor=vendor,
        current_user=current_user,
        db=db,
        dry_run=True,
    )
    await db.commit()
    return preview


@router.post("/vendor/products/import/commit", status_code=status.HTTP_201_CREATED)
async def commit_product_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    ensure_vendor_active(vendor)
    preview = await _preview_product_import(
        csv_content=(await file.read()).decode("utf-8"),
        vendor=vendor,
        current_user=current_user,
        db=db,
        dry_run=False,
    )
    await db.commit()
    return preview


@router.get("/vendor/products")
async def list_vendor_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    products = (
        await db.execute(select(Product).where(Product.vendor_id == vendor.id).order_by(Product.created_at.desc()))
    ).scalars().all()
    return {"items": [await serialize_product(product, db) for product in products], "total": len(products)}


@router.patch("/vendor/products/{product_id}")
async def update_vendor_product(
    product_id: str,
    payload: ProductCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    product = await db.get(Product, decode_id_or_404(product_id))
    if product is None or product.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.category_id = decode_id_or_404(payload.category_id)
    product.brand_id = decode_id_or_404(payload.brand_id) if payload.brand_id else None
    product.name = payload.name
    product.slug = payload.slug
    product.short_description = payload.short_description
    product.description = payload.description
    product.specifications_json = json.dumps(payload.specifications)
    product.is_featured = payload.is_featured
    product.status = payload.status
    product.updated_at = utc_now()
    await db.commit()
    return {"product": await serialize_product(product, db)}


@router.post("/vendor/products/{product_id}/archive")
async def archive_vendor_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    product = await db.get(Product, decode_id_or_404(product_id))
    if product is None or product.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.status = ProductStatus.ARCHIVED
    product.updated_at = utc_now()
    await db.commit()
    return {"success": True}


@router.delete("/vendor/products/{product_id}")
async def delete_vendor_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    product = await db.get(Product, decode_id_or_404(product_id))
    if product is None or product.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.status = ProductStatus.ARCHIVED
    product.updated_at = utc_now()
    await db.commit()
    return {"success": True}


@router.patch("/vendor/inventory/{variant_id}")
async def update_vendor_inventory(
    variant_id: str,
    payload: InventoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    variant = await db.get(ProductVariant, decode_id_or_404(variant_id))
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    product = await db.get(Product, variant.product_id)
    if product is None or product.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    inventory = (
        await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
    ).scalars().first()
    if inventory is None:
        inventory = Inventory(variant_id=variant.id)
        db.add(inventory)
        await db.flush()
    inventory.quantity = payload.quantity
    inventory.reorder_level = payload.reorder_level
    inventory.reorder_qty = payload.reorder_qty
    inventory.updated_at = utc_now()
    await db.commit()
    return {"variant_id": encode_id(variant.id or 0), "quantity": inventory.quantity}


@router.get("/vendor/inventory/summary")
async def get_vendor_inventory_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    products = (
        await db.execute(select(Product).where(Product.vendor_id == vendor.id))
    ).scalars().all()
    items = []
    for product in products:
        variants = (
            await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
        ).scalars().all()
        for variant in variants:
            inventory_rows = (
                await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
            ).scalars().all()
            quantity = sum(row.quantity for row in inventory_rows)
            reserved = sum(row.reserved_qty for row in inventory_rows)
            reorder_level = max((row.reorder_level for row in inventory_rows), default=0)
            items.append(
                {
                    "product_id": encode_id(product.id or 0),
                    "variant_id": encode_id(variant.id or 0),
                    "sku": variant.sku,
                    "quantity": quantity,
                    "reserved_qty": reserved,
                    "available_qty": max(quantity - reserved, 0),
                    "low_stock": quantity <= reorder_level if reorder_level else False,
                }
            )
    return {"items": items, "total": len(items)}


@router.get("/admin/catalog/inventory/reorder-report")
async def get_reorder_report(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    inventory_rows = (await db.execute(select(Inventory).order_by(Inventory.updated_at.asc()))).scalars().all()
    items = []
    for inventory in inventory_rows:
        if inventory.reorder_level and inventory.quantity <= inventory.reorder_level:
            variant = await db.get(ProductVariant, inventory.variant_id)
            items.append(
                {
                    "variant_id": encode_id(inventory.variant_id),
                    "sku": variant.sku if variant else "",
                    "quantity": inventory.quantity,
                    "reorder_level": inventory.reorder_level,
                    "reorder_qty": inventory.reorder_qty,
                    "warehouse_id": encode_id(inventory.warehouse_id) if inventory.warehouse_id else None,
                }
            )
    return {"items": items, "total": len(items)}


@router.post("/admin/catalog/products/{product_id}/approve")
async def approve_product(
    product_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, decode_id_or_404(product_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.status = ProductStatus.ACTIVE
    product.published_at = utc_now()
    product.updated_at = utc_now()
    await db.commit()
    return {"product": await serialize_product(product, db)}


@router.post("/admin/catalog/products/{product_id}/reject")
async def reject_product(
    product_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, decode_id_or_404(product_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.status = ProductStatus.REJECTED
    product.updated_at = utc_now()
    await db.commit()
    return {"product": await serialize_product(product, db)}


@router.get("/products")
async def list_products(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    in_stock: bool = Query(default=False),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    is_featured: bool | None = Query(default=None),
    attribute_key: str | None = Query(default=None),
    attribute_value: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.status == ProductStatus.ACTIVE)
    if q:
        query = query.where(
            (Product.name.ilike(f"%{q}%")) |
            (Product.short_description.ilike(f"%{q}%")) |
            (Product.description.ilike(f"%{q}%"))
        )
    if category:
        query = query.where(Product.category_id == decode_id_or_404(category))
    if brand:
        query = query.where(Product.brand_id == decode_id_or_404(brand))
    if vendor_id:
        query = query.where(Product.vendor_id == decode_id_or_404(vendor_id))
    if min_rating is not None:
        query = query.where(Product.avg_rating >= min_rating)
    if is_featured is not None:
        query = query.where(Product.is_featured == is_featured)
    products = (await db.execute(query.order_by(Product.created_at.desc()))).scalars().all()
    filtered: list[dict[str, object]] = []
    for product in products:
        serialized = await serialize_product(product, db, include_variants=False)
        if in_stock and not serialized["in_stock"]:
            continue
        if min_price is not None and (serialized["min_selling_price"] or 0) < min_price:
            continue
        if max_price is not None and (serialized["min_selling_price"] or 0) > max_price:
            continue
        if attribute_key and attribute_value:
            specifications = serialized["specifications"]
            value = specifications.get(attribute_key)
            if str(value).lower() != attribute_value.lower():
                continue
        filtered.append(serialized)
    if sort == "price_asc":
        filtered.sort(key=lambda item: item["min_selling_price"] or 0)
    elif sort == "price_desc":
        filtered.sort(key=lambda item: item["min_selling_price"] or 0, reverse=True)
    elif sort == "rating":
        filtered.sort(key=lambda item: item["avg_rating"], reverse=True)
    start = (page - 1) * limit
    end = start + limit
    return {
        "items": filtered[start:end],
        "total": len(filtered),
        "page": page,
        "limit": limit,
    }


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_products(q=q, page=page, limit=limit, db=db)


@router.get("/search/autocomplete")
async def autocomplete_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    products = (
        await db.execute(select(Product).where(Product.status == ProductStatus.ACTIVE).order_by(Product.view_count.desc(), Product.created_at.desc()))
    ).scalars().all()
    q_lower = q.lower()
    suggestions = []
    for product in products:
        score = max(
            SequenceMatcher(None, q_lower, product.name.lower()).ratio(),
            1.0 if product.name.lower().startswith(q_lower) else 0.0,
            0.9 if q_lower in product.name.lower() else 0.0,
        )
        if score >= 0.35:
            suggestions.append(
                {
                    "id": encode_id(product.id or 0),
                    "name": product.name,
                    "slug": product.slug,
                    "score": round(score, 3),
                }
            )
    suggestions.sort(key=lambda item: item["score"], reverse=True)
    return {"items": suggestions[:limit], "total": min(len(suggestions), limit)}


@router.get("/products/{product_id}")
async def get_product_detail(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, decode_id_or_404(product_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    ensure_product_active(product)
    product.view_count += 1
    await db.commit()
    return {"product": await serialize_product(product, db)}


@router.get("/products/{product_id}/reviews")
async def list_product_reviews(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    reviews = (
        await db.execute(
            select(ProductReview).where(
                ProductReview.product_id == decode_id_or_404(product_id),
                ProductReview.status == ProductReviewStatus.APPROVED,
            )
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(review.id or 0),
                "user_id": encode_id(review.user_id),
                "rating": review.rating,
                "title": review.title,
                "body": review.body,
                "created_at": review.created_at.isoformat(),
            }
            for review in reviews
        ],
        "total": len(reviews),
    }


@router.post("/products/{product_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: str,
    payload: ProductReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    decoded_product_id = decode_id_or_404(product_id)
    product = await db.get(Product, decoded_product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    review = ProductReview(product_id=decoded_product_id, user_id=current_user.id, **payload.model_dump())
    db.add(review)
    db.add(
        UserProductEvent(
            user_id=current_user.id,
            product_id=decoded_product_id,
            event_type=RecommendationEventType.RATING,
        )
    )
    await recalculate_product_rating(decoded_product_id, db)
    await db.commit()
    await analytics.capture(str(current_user.id), "product_review_created", {"product_id": decoded_product_id})
    return {"review_id": encode_id(review.id or 0)}


@router.patch("/products/{product_id}/reviews/{review_id}")
async def update_review(
    product_id: str,
    review_id: str,
    payload: ProductReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(ProductReview, decode_id_or_404(review_id))
    decoded_product_id = decode_id_or_404(product_id)
    if review is None or review.product_id != decoded_product_id or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    review.rating = payload.rating
    review.title = payload.title
    review.body = payload.body
    review.status = ProductReviewStatus.PENDING
    await recalculate_product_rating(decoded_product_id, db)
    await db.commit()
    return {"review_id": encode_id(review.id or 0), "status": review.status.value}


@router.delete("/products/{product_id}/reviews/{review_id}")
async def delete_review(
    product_id: str,
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(ProductReview, decode_id_or_404(review_id))
    decoded_product_id = decode_id_or_404(product_id)
    if review is None or review.product_id != decoded_product_id or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    await db.delete(review)
    await recalculate_product_rating(decoded_product_id, db)
    await db.commit()
    return {"success": True}


@router.post("/admin/catalog/reviews/{review_id}/approve")
async def approve_review(
    review_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(ProductReview, decode_id_or_404(review_id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    review.status = ProductReviewStatus.APPROVED
    await recalculate_product_rating(review.product_id, db)
    await db.commit()
    return {"review_id": encode_id(review.id or 0), "status": review.status.value}


@router.post("/admin/catalog/reviews/{review_id}/reject")
async def reject_review(
    review_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(ProductReview, decode_id_or_404(review_id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    review.status = ProductReviewStatus.REJECTED
    await recalculate_product_rating(review.product_id, db)
    await db.commit()
    return {"review_id": encode_id(review.id or 0), "status": review.status.value}
