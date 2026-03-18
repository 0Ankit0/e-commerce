from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.catalog.models import (
    Brand,
    Category,
    Inventory,
    Product,
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
        published_at=datetime.utcnow() if payload.status == ProductStatus.ACTIVE else None,
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
    product.updated_at = datetime.utcnow()
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
    product.updated_at = datetime.utcnow()
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
    product.updated_at = datetime.utcnow()
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
    inventory.updated_at = datetime.utcnow()
    await db.commit()
    return {"variant_id": encode_id(variant.id or 0), "quantity": inventory.quantity}


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
    product.published_at = datetime.utcnow()
    product.updated_at = datetime.utcnow()
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
    product.updated_at = datetime.utcnow()
    await db.commit()
    return {"product": await serialize_product(product, db)}


@router.get("/products")
async def list_products(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    in_stock: bool = Query(default=False),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.status == ProductStatus.ACTIVE)
    products = (await db.execute(query.order_by(Product.created_at.desc()))).scalars().all()
    filtered: list[dict[str, object]] = []
    for product in products:
        if q and q.lower() not in f"{product.name} {product.short_description} {product.description}".lower():
            continue
        if category and product.category_id != decode_id_or_404(category):
            continue
        if brand and product.brand_id != decode_id_or_404(brand):
            continue
        if vendor_id and product.vendor_id != decode_id_or_404(vendor_id):
            continue
        serialized = await serialize_product(product, db, include_variants=False)
        if in_stock and not serialized["in_stock"]:
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
        if product.name.lower().startswith(q_lower) or q_lower in product.name.lower():
            suggestions.append({"id": encode_id(product.id or 0), "name": product.name, "slug": product.slug})
        if len(suggestions) >= limit:
            break
    return {"items": suggestions, "total": len(suggestions)}


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
