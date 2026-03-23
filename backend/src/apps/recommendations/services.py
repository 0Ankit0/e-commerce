from __future__ import annotations

import json
from datetime import timezone
from math import exp, log1p

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Inventory, Product, ProductVariant, ProductStatus
from src.apps.core.time import utc_now
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
    user_price_profile: tuple[float, float] | None = None
    if user_id:
        user_affinities = (
            await db.execute(select(UserAffinity).where(UserAffinity.user_id == user_id))
        ).scalars().all()
        orders = (
            await db.execute(select(Order).where(Order.user_id == user_id, Order.status != OrderStatus.CANCELLED))
        ).scalars().all()
        observed_prices: list[float] = []
        for order in orders:
            items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
            purchased_product_ids.update(item.product_id for item in items)
            observed_prices.extend(item.unit_price for item in items if item.unit_price > 0)
        if observed_prices:
            user_price_profile = (
                sum(observed_prices) / len(observed_prices),
                max(observed_prices),
            )

    similarity_ids: dict[int, float] = {}
    context_product = await db.get(Product, product_id) if product_id else None
    if context_product:
        rows = (
            await db.execute(select(ProductSimilarity).where(ProductSimilarity.product_id == context_product.id))
        ).scalars().all()
        similarity_ids = {row.similar_product_id: row.score for row in rows}

    category_affinity = {
        affinity.category_id: affinity.score for affinity in user_affinities if affinity.category_id is not None
    }
    brand_affinity = {
        affinity.brand_id: affinity.score for affinity in user_affinities if affinity.brand_id is not None
    }
    max_category_affinity = max(category_affinity.values(), default=0.0)
    max_brand_affinity = max(brand_affinity.values(), default=0.0)

    results: list[tuple[float, Product, str, dict[str, float]]] = []
    for product in products:
        if product_id and product.id == product_id:
            continue
        available = await _available_stock(product.id, db)
        if available <= 0:
            continue
        price_point = await _product_price_point(product.id, db)
        popularity = popularity_map.get(product.id)

        popularity_feature = min(
            log1p(
                (popularity.view_count if popularity else 0)
                + (popularity.cart_count if popularity else 0) * 3
                + (popularity.wishlist_count if popularity else 0) * 2
                + (popularity.purchase_count if popularity else 0) * 5
                + (popularity.score if popularity else 0)
            )
            / 4.5,
            1.0,
        )
        rating_feature = _bayesian_rating(product.avg_rating, product.review_count)
        recency_feature = _recency_score(product.created_at)
        stock_feature = min(available / 10.0, 1.0)
        featured_feature = 1.0 if product.is_featured else 0.0
        category_feature = (
            category_affinity.get(product.category_id, 0.0) / max_category_affinity
            if product.category_id and max_category_affinity > 0
            else 0.0
        )
        brand_feature = (
            brand_affinity.get(product.brand_id, 0.0) / max_brand_affinity
            if product.brand_id and max_brand_affinity > 0
            else 0.0
        )
        similarity_feature = similarity_ids.get(product.id, 0.0)
        context_match_feature = 0.0
        if context_product and product.category_id == context_product.category_id:
            context_match_feature += 0.7
        if context_product and context_product.brand_id and product.brand_id == context_product.brand_id:
            context_match_feature += 0.3
        price_fit_feature = _price_fit_score(price_point, user_price_profile)

        features = {
            "popularity": popularity_feature,
            "rating": rating_feature,
            "recency": recency_feature,
            "stock": stock_feature,
            "featured": featured_feature,
            "category_affinity": category_feature,
            "brand_affinity": brand_feature,
            "similarity": similarity_feature,
            "context_match": min(context_match_feature, 1.0),
            "price_fit": price_fit_feature,
        }

        score = (
            features["popularity"] * 2.1
            + features["rating"] * 1.6
            + features["recency"] * 1.0
            + features["stock"] * 0.8
            + features["featured"] * 0.5
            + features["category_affinity"] * 2.0
            + features["brand_affinity"] * 1.2
            + features["similarity"] * 2.4
            + features["context_match"] * 1.4
            + features["price_fit"] * 0.9
        )

        reason = _reason_from_features(features, context_product)
        if placement in {RecommendationPlacement.HOME, RecommendationPlacement.POST_PURCHASE} and product.id in purchased_product_ids:
            score -= 3
        results.append((score, product, reason, features))

    results.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    ranked_results = _apply_diversity_rerank(results)
    from src.apps.catalog.services import serialize_product

    payload: list[dict[str, object]] = []
    for score, product, reason, features in ranked_results[:limit]:
        serialized = await serialize_product(product, db, include_variants=False)
        serialized["score"] = round(score, 2)
        serialized["reason"] = reason
        serialized["ranking_features"] = {key: round(value, 3) for key, value in features.items()}
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


async def _product_price_point(product_id: int, db: AsyncSession) -> float:
    variants = (
        await db.execute(select(ProductVariant).where(ProductVariant.product_id == product_id))
    ).scalars().all()
    prices = [variant.selling_price for variant in variants if variant.selling_price > 0]
    return min(prices) if prices else 0.0


def _bayesian_rating(avg_rating: float, review_count: int, baseline: float = 3.8, confidence: int = 8) -> float:
    weighted = ((review_count / (review_count + confidence)) * avg_rating) + (
        (confidence / (review_count + confidence)) * baseline
    )
    return min(max(weighted / 5.0, 0.0), 1.0)


def _recency_score(created_at) -> float:  # noqa: ANN001
    current_time = utc_now()
    created_time = created_at
    if created_time.tzinfo is None:
        created_time = created_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    age_days = max((current_time - created_time).days, 0)
    return exp(-(age_days / 45.0))


def _price_fit_score(price_point: float, profile: tuple[float, float] | None) -> float:
    if not profile or price_point <= 0:
        return 0.5
    average_price, max_price = profile
    tolerance = max(max_price * 0.35, 15.0)
    distance = abs(price_point - average_price)
    return max(0.0, 1.0 - min(distance / tolerance, 1.0))


def _reason_from_features(features: dict[str, float], context_product: Product | None) -> str:
    feature_name = max(features, key=features.get)
    if feature_name == "similarity" and context_product is not None:
        return f"Because you viewed {context_product.name}"
    if feature_name in {"category_affinity", "brand_affinity"}:
        return "Based on your recent shopping signals"
    if feature_name == "rating":
        return "Highly rated by similar shoppers"
    if feature_name == "recency":
        return "Fresh arrival with rising momentum"
    return "Trending for shoppers like you"


def _apply_diversity_rerank(
    ranked_items: list[tuple[float, Product, str, dict[str, float]]]
) -> list[tuple[float, Product, str, dict[str, float]]]:
    selected: list[tuple[float, Product, str, dict[str, float]]] = []
    seen_categories: dict[int, int] = {}
    seen_brands: dict[int, int] = {}

    for score, product, reason, features in ranked_items:
        adjusted_score = score
        if product.category_id is not None:
            adjusted_score -= seen_categories.get(product.category_id, 0) * 0.35
        if product.brand_id is not None:
            adjusted_score -= seen_brands.get(product.brand_id, 0) * 0.2
        selected.append((adjusted_score, product, reason, features))
        if product.category_id is not None:
            seen_categories[product.category_id] = seen_categories.get(product.category_id, 0) + 1
        if product.brand_id is not None:
            seen_brands[product.brand_id] = seen_brands.get(product.brand_id, 0) + 1

    selected.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    return selected
