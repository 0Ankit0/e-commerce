from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Brand, Category, Inventory, Product, ProductVariant, ProductStatus
from src.apps.orders.models import Order, OrderItem, OrderStatus
from src.apps.recommendations.models import (
    ProductPopularity,
    ProductSimilarity,
    RecommendationEventType,
    RecommendationPlacement,
    UserAffinity,
    UserProductEvent,
)


async def record_recommendation_event(
    *,
    user_id: int | None,
    product_id: int | None,
    event_type: RecommendationEventType,
    placement: RecommendationPlacement | None,
    query_text: str,
    metadata: dict[str, object],
    db: AsyncSession,
) -> UserProductEvent:
    event = UserProductEvent(
        user_id=user_id,
        product_id=product_id,
        event_type=event_type,
        placement=placement,
        query_text=query_text,
        metadata_json=json.dumps(metadata),
    )
    db.add(event)
    await db.flush()

    if product_id:
        popularity = (
            await db.execute(select(ProductPopularity).where(ProductPopularity.product_id == product_id))
        ).scalars().first()
        if popularity is None:
            popularity = ProductPopularity(product_id=product_id)
            db.add(popularity)
            await db.flush()
        if event_type == RecommendationEventType.VIEW:
            popularity.view_count += 1
            popularity.score += 1.0
        elif event_type == RecommendationEventType.ADD_TO_CART:
            popularity.cart_count += 1
            popularity.score += 3.0
        elif event_type == RecommendationEventType.ADD_TO_WISHLIST:
            popularity.wishlist_count += 1
            popularity.score += 2.0
        elif event_type == RecommendationEventType.PURCHASE:
            popularity.purchase_count += 1
            popularity.score += 5.0

        if user_id:
            product = await db.get(Product, product_id)
            if product:
                await _upsert_affinity(user_id, product.category_id, product.brand_id, event_type, db)
                await _upsert_similarity(product.id, db)

    return event


async def get_recommendations(
    *,
    placement: RecommendationPlacement,
    limit: int,
    db: AsyncSession,
    user_id: int | None = None,
    product_id: int | None = None,
) -> list[dict[str, object]]:
    products = (
        await db.execute(select(Product).where(Product.status == ProductStatus.ACTIVE))
    ).scalars().all()
    popularity_map = {
        popularity.product_id: popularity
        for popularity in (await db.execute(select(ProductPopularity))).scalars().all()
    }
    user_affinities = []
    purchased_product_ids: set[int] = set()
    if user_id:
        user_affinities = (
            await db.execute(select(UserAffinity).where(UserAffinity.user_id == user_id))
        ).scalars().all()
        orders = (
            await db.execute(select(Order).where(Order.user_id == user_id, Order.status != OrderStatus.CANCELLED))
        ).scalars().all()
        for order in orders:
            items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
            purchased_product_ids.update(item.product_id for item in items)

    similarity_ids: dict[int, float] = {}
    context_product = await db.get(Product, product_id) if product_id else None
    if context_product:
        rows = (
            await db.execute(select(ProductSimilarity).where(ProductSimilarity.product_id == context_product.id))
        ).scalars().all()
        similarity_ids = {row.similar_product_id: row.score for row in rows}

    results: list[tuple[float, Product, str]] = []
    for product in products:
        if product_id and product.id == product_id:
            continue
        available = await _available_stock(product.id, db)
        if available <= 0:
            continue
        score = 0.0
        reason = "Trending for shoppers"
        popularity = popularity_map.get(product.id)
        if popularity:
            score += popularity.score
        if product.is_featured:
            score += 1.5
            reason = "Featured this week"
        if context_product and product.category_id == context_product.category_id:
            score += 2.5
            reason = f"Similar to {context_product.name}"
        if context_product and context_product.brand_id and product.brand_id == context_product.brand_id:
            score += 1.5
        if product.id in similarity_ids:
            score += similarity_ids[product.id] * 5
            reason = f"Because you viewed {context_product.name}"
        if user_affinities:
            for affinity in user_affinities:
                if affinity.category_id and affinity.category_id == product.category_id:
                    score += affinity.score
                    reason = "Based on your recent category activity"
                if affinity.brand_id and affinity.brand_id == product.brand_id:
                    score += affinity.score * 0.8
                    reason = "Based on your brand preferences"
        if placement in {RecommendationPlacement.HOME, RecommendationPlacement.POST_PURCHASE} and product.id in purchased_product_ids:
            score -= 3
        results.append((score, product, reason))

    results.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    from src.apps.catalog.services import serialize_product

    payload: list[dict[str, object]] = []
    for score, product, reason in results[:limit]:
        serialized = await serialize_product(product, db, include_variants=False)
        serialized["score"] = round(score, 2)
        serialized["reason"] = reason
        payload.append(serialized)
    return payload


async def _upsert_affinity(
    user_id: int,
    category_id: int | None,
    brand_id: int | None,
    event_type: RecommendationEventType,
    db: AsyncSession,
) -> None:
    weight = {
        RecommendationEventType.VIEW: 0.3,
        RecommendationEventType.CLICK: 0.6,
        RecommendationEventType.ADD_TO_CART: 1.5,
        RecommendationEventType.ADD_TO_WISHLIST: 1.0,
        RecommendationEventType.PURCHASE: 2.5,
        RecommendationEventType.RATING: 1.5,
        RecommendationEventType.SEARCH: 0.7,
        RecommendationEventType.RECOMMENDATION_CLICK: 0.8,
    }[event_type]
    if category_id:
        affinity = (
            await db.execute(
                select(UserAffinity).where(
                    UserAffinity.user_id == user_id,
                    UserAffinity.category_id == category_id,
                    UserAffinity.brand_id == None,  # noqa: E711
                )
            )
        ).scalars().first()
        if affinity is None:
            affinity = UserAffinity(user_id=user_id, category_id=category_id, score=0)
            db.add(affinity)
        affinity.score += weight
    if brand_id:
        affinity = (
            await db.execute(
                select(UserAffinity).where(
                    UserAffinity.user_id == user_id,
                    UserAffinity.brand_id == brand_id,
                    UserAffinity.category_id == None,  # noqa: E711
                )
            )
        ).scalars().first()
        if affinity is None:
            affinity = UserAffinity(user_id=user_id, brand_id=brand_id, score=0)
            db.add(affinity)
        affinity.score += weight


async def _upsert_similarity(product_id: int, db: AsyncSession) -> None:
    product = await db.get(Product, product_id)
    if product is None:
        return
    similar_products = (
        await db.execute(
            select(Product).where(
                Product.id != product.id,
                Product.category_id == product.category_id,
                Product.status == ProductStatus.ACTIVE,
            )
        )
    ).scalars().all()
    for similar in similar_products[:5]:
        existing = (
            await db.execute(
                select(ProductSimilarity).where(
                    ProductSimilarity.product_id == product.id,
                    ProductSimilarity.similar_product_id == similar.id,
                )
            )
        ).scalars().first()
        if existing is None:
            db.add(
                ProductSimilarity(
                    product_id=product.id,
                    similar_product_id=similar.id,
                    score=0.7 if product.brand_id == similar.brand_id else 0.5,
                    reason_code="category_match",
                )
            )


async def _available_stock(product_id: int, db: AsyncSession) -> int:
    variants = (
        await db.execute(select(ProductVariant).where(ProductVariant.product_id == product_id))
    ).scalars().all()
    total = 0
    for variant in variants:
        inventory_rows = (
            await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
        ).scalars().all()
        total += sum(max(row.quantity - row.reserved_qty, 0) for row in inventory_rows)
    return total
