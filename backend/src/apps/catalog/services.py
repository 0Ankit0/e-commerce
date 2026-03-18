from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.catalog.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductReview,
    ProductStatus,
    ProductVariant,
)


async def serialize_product(product: Product, db: AsyncSession, include_variants: bool = True) -> dict[str, object]:
    from src.apps.iam.utils.hashid import encode_id

    category = await db.get(Category, product.category_id)
    brand = await db.get(Brand, product.brand_id) if product.brand_id else None
    variants = (
        await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
    ).scalars().all()
    images = (
        await db.execute(
            select(ProductImage).where(ProductImage.product_id == product.id).order_by(ProductImage.position.asc())
        )
    ).scalars().all()
    variant_payloads = []
    in_stock = False
    min_selling_price: float | None = None
    for variant in variants:
        inventory_rows = (
            await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
        ).scalars().all()
        available_qty = sum(max(row.quantity - row.reserved_qty, 0) for row in inventory_rows)
        in_stock = in_stock or available_qty > 0
        min_selling_price = variant.selling_price if min_selling_price is None else min(min_selling_price, variant.selling_price)
        if include_variants:
            variant_payloads.append(
                {
                    "id": encode_id(variant.id or 0),
                    "sku": variant.sku,
                    "name": variant.name,
                    "mrp": variant.mrp,
                    "selling_price": variant.selling_price,
                    "attributes": json.loads(variant.attributes_json or "{}"),
                    "available_qty": available_qty,
                    "is_default": variant.is_default,
                    "is_active": variant.is_active,
                }
            )
    return {
        "id": encode_id(product.id or 0),
        "vendor_id": encode_id(product.vendor_id),
        "category": {
            "id": encode_id(category.id or 0),
            "name": category.name,
            "slug": category.slug,
        }
        if category
        else None,
        "brand": {
            "id": encode_id(brand.id or 0),
            "name": brand.name,
            "slug": brand.slug,
        }
        if brand
        else None,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "description": product.description,
        "specifications": json.loads(product.specifications_json or "{}"),
        "status": product.status.value,
        "avg_rating": product.avg_rating,
        "review_count": product.review_count,
        "view_count": product.view_count,
        "is_featured": product.is_featured,
        "images": [
            {
                "id": encode_id(image.id or 0),
                "url": image.url,
                "thumbnail_url": image.thumbnail_url,
                "alt_text": image.alt_text,
                "position": image.position,
                "is_primary": image.is_primary,
            }
            for image in images
        ],
        "variants": variant_payloads,
        "min_selling_price": min_selling_price,
        "in_stock": in_stock,
        "created_at": product.created_at.isoformat(),
    }


def ensure_variant_pricing(variant: ProductVariant) -> None:
    if variant.selling_price > variant.mrp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot exceed MRP",
        )


async def recalculate_product_rating(product_id: int, db: AsyncSession) -> None:
    product = await db.get(Product, product_id)
    if product is None:
        return
    reviews = (
        await db.execute(select(ProductReview).where(ProductReview.product_id == product_id))
    ).scalars().all()
    if not reviews:
        product.avg_rating = 0
        product.review_count = 0
        return
    product.review_count = len(reviews)
    product.avg_rating = round(sum(review.rating for review in reviews) / len(reviews), 2)
    product.updated_at = utc_now()


def ensure_product_active(product: Product) -> None:
    if product.status != ProductStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not available")
