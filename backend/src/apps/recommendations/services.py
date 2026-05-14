from __future__ import annotations

import json
from datetime import timezone
from math import exp, log1p

from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Inventory, Product, ProductStatus, ProductVariant
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

EVENT_SIGNAL_WEIGHTS = {
    RecommendationEventType.VIEW: 0.4,
    RecommendationEventType.CLICK: 0.7,
    RecommendationEventType.SEARCH: 0.8,
    RecommendationEventType.ADD_TO_CART: 1.7,
    RecommendationEventType.ADD_TO_WISHLIST: 1.3,
    RecommendationEventType.PURCHASE: 2.6,
    RecommendationEventType.RATING: 1.8,
    RecommendationEventType.RECOMMENDATION_CLICK: 1.0,
}


def _event_weight(event_type: RecommendationEventType) -> float:
    return EVENT_SIGNAL_WEIGHTS[event_type]


def _product_popularity_insert_values(product_id: int, event_type: RecommendationEventType, now) -> dict[str, object]:
    values: dict[str, object] = {
        "product_id": product_id,
        "score": 0.0,
        "view_count": 0,
        "purchase_count": 0,
        "cart_count": 0,
        "wishlist_count": 0,
        "updated_at": now,
    }
    if event_type == RecommendationEventType.VIEW:
        values["view_count"] = 1
        values["score"] = 1.0
    elif event_type == RecommendationEventType.ADD_TO_CART:
        values["cart_count"] = 1
        values["score"] = 3.0
    elif event_type == RecommendationEventType.ADD_TO_WISHLIST:
        values["wishlist_count"] = 1
        values["score"] = 2.0
    elif event_type == RecommendationEventType.PURCHASE:
        values["purchase_count"] = 1
        values["score"] = 5.0
    return values


def _product_popularity_update_values(event_type: RecommendationEventType, now) -> dict[str, object]:
    values: dict[str, object] = {"updated_at": now}
    if event_type == RecommendationEventType.VIEW:
        values["view_count"] = ProductPopularity.view_count + 1
        values["score"] = ProductPopularity.score + 1.0
    elif event_type == RecommendationEventType.ADD_TO_CART:
        values["cart_count"] = ProductPopularity.cart_count + 1
        values["score"] = ProductPopularity.score + 3.0
    elif event_type == RecommendationEventType.ADD_TO_WISHLIST:
        values["wishlist_count"] = ProductPopularity.wishlist_count + 1
        values["score"] = ProductPopularity.score + 2.0
    elif event_type == RecommendationEventType.PURCHASE:
        values["purchase_count"] = ProductPopularity.purchase_count + 1
        values["score"] = ProductPopularity.score + 5.0
    return values


async def _increment_product_popularity(
    *,
    product_id: int,
    event_type: RecommendationEventType,
    db: AsyncSession,
) -> None:
    now = utc_now()
    insert_values = _product_popularity_insert_values(product_id, event_type, now)
    update_values = _product_popularity_update_values(event_type, now)
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""

    if dialect_name == "postgresql":
        stmt = postgresql_insert(ProductPopularity).values(**insert_values)
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[ProductPopularity.product_id],
                set_=update_values,
            )
        )
        return

    popularity = (
        await db.execute(select(ProductPopularity).where(ProductPopularity.product_id == product_id))
    ).scalars().first()
    if popularity is None:
        popularity = ProductPopularity(**insert_values)
        try:
            async with db.begin_nested():
                db.add(popularity)
                await db.flush()
        except IntegrityError:
            popularity = (
                await db.execute(select(ProductPopularity).where(ProductPopularity.product_id == product_id))
            ).scalars().one()
    await db.execute(
        sa_update(ProductPopularity)
        .where(ProductPopularity.product_id == product_id)
        .values(**update_values)
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

    product = await db.get(Product, product_id) if product_id else None
    if product_id:
        await _increment_product_popularity(product_id=product_id, event_type=event_type, db=db)
    if product is not None:
        await _upsert_similarity(product.id, db)

    if user_id and product is not None:
        await _upsert_affinity(
            user_id,
            product.category_id,
            product.brand_id,
            event_type,
            db,
        )
        await _update_behavioral_similarity(
            user_id=user_id,
            product_id=product.id,
            event_type=event_type,
            db=db,
        )
    if user_id and event_type == RecommendationEventType.SEARCH:
        await _upsert_search_intent_affinities(user_id=user_id, metadata=metadata, db=db)

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

    user_affinities: list[UserAffinity] = []
    purchased_product_ids: set[int] = set()
    user_price_profile: tuple[float, float] | None = None
    recent_signal_scores: dict[int, float] = {}
    if user_id:
        user_affinities = (
            await db.execute(select(UserAffinity).where(UserAffinity.user_id == user_id))
        ).scalars().all()
        recent_signal_scores = await _recent_user_product_signals(
            user_id=user_id,
            db=db,
            exclude_product_id=product_id,
        )
        orders = (
            await db.execute(
                select(Order).where(
                    Order.user_id == user_id,
                    Order.status != OrderStatus.CANCELLED,
                )
            )
        ).scalars().all()
        observed_prices: list[float] = []
        for order in orders:
            items = (
                await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
            ).scalars().all()
            purchased_product_ids.update(item.product_id for item in items)
            observed_prices.extend(item.unit_price for item in items if item.unit_price > 0)
        if observed_prices:
            user_price_profile = (
                sum(observed_prices) / len(observed_prices),
                max(observed_prices),
            )

    similarity_scores: dict[int, float] = {}
    context_product = await db.get(Product, product_id) if product_id else None
    if context_product:
        rows = (
            await db.execute(
                select(ProductSimilarity).where(ProductSimilarity.product_id == context_product.id)
            )
        ).scalars().all()
        for row in rows:
            similarity_scores[row.similar_product_id] = similarity_scores.get(
                row.similar_product_id,
                0.0,
            ) + row.score

    for seed_product_id, seed_score in recent_signal_scores.items():
        rows = (
            await db.execute(
                select(ProductSimilarity).where(ProductSimilarity.product_id == seed_product_id)
            )
        ).scalars().all()
        for row in rows:
            similarity_scores[row.similar_product_id] = similarity_scores.get(
                row.similar_product_id,
                0.0,
            ) + (row.score * max(seed_score, 0.4))

    similarity_max = max(similarity_scores.values(), default=0.0)
    collaborative_scores = await _collaborative_product_scores(
        user_id=user_id,
        seed_scores=recent_signal_scores,
        exclude_product_ids=purchased_product_ids | ({product_id} if product_id else set()),
        db=db,
    )
    collaborative_max = max(collaborative_scores.values(), default=0.0)

    category_affinity = {
        affinity.category_id: affinity.score
        for affinity in user_affinities
        if affinity.category_id is not None
    }
    brand_affinity = {
        affinity.brand_id: affinity.score
        for affinity in user_affinities
        if affinity.brand_id is not None
    }
    max_category_affinity = max(category_affinity.values(), default=0.0)
    max_brand_affinity = max(brand_affinity.values(), default=0.0)
    max_recent_signal = max(recent_signal_scores.values(), default=0.0)

    results: list[tuple[float, Product, str, dict[str, float]]] = []
    for product in products:
        if product.id is None:
            continue
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
        similarity_feature = (
            similarity_scores.get(product.id, 0.0) / similarity_max
            if similarity_max > 0
            else 0.0
        )
        collaborative_feature = (
            collaborative_scores.get(product.id, 0.0) / collaborative_max
            if collaborative_max > 0
            else 0.0
        )
        recent_interest_feature = (
            recent_signal_scores.get(product.id, 0.0) / max_recent_signal
            if max_recent_signal > 0
            else 0.0
        )

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
            "collaborative": collaborative_feature,
            "recent_interest": recent_interest_feature,
            "context_match": min(context_match_feature, 1.0),
            "price_fit": price_fit_feature,
        }

        score = (
            features["popularity"] * 1.9
            + features["rating"] * 1.5
            + features["recency"] * 0.8
            + features["stock"] * 0.6
            + features["featured"] * 0.35
            + features["category_affinity"] * 1.8
            + features["brand_affinity"] * 1.1
            + features["similarity"] * 2.3
            + features["collaborative"] * 1.9
            + features["recent_interest"] * 1.0
            + features["context_match"] * 1.2
            + features["price_fit"] * 0.7
        )
        if placement in {
            RecommendationPlacement.HOME,
            RecommendationPlacement.POST_PURCHASE,
        } and product.id in purchased_product_ids:
            score -= 3.0

        reason = _reason_from_features(features, context_product)
        results.append((score, product, reason, features))

    results.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    ranked_results = _apply_diversity_rerank(results)

    from src.apps.catalog.services import serialize_product

    payload: list[dict[str, object]] = []
    for score, product, reason, features in ranked_results[:limit]:
        serialized = await serialize_product(product, db, include_variants=False)
        serialized["score"] = round(score, 2)
        serialized["reason"] = reason
        serialized["ranking_features"] = {
            key: round(value, 3)
            for key, value in features.items()
        }
        payload.append(serialized)
    return payload


async def _recent_user_product_signals(
    *,
    user_id: int,
    db: AsyncSession,
    exclude_product_id: int | None = None,
    limit: int = 18,
) -> dict[int, float]:
    recent_events = (
        await db.execute(
            select(UserProductEvent)
            .where(
                UserProductEvent.user_id == user_id,
                UserProductEvent.product_id != None,  # noqa: E711
            )
            .order_by(UserProductEvent.created_at.desc())
        )
    ).scalars().all()

    product_scores: dict[int, float] = {}
    for index, event in enumerate(recent_events):
        if event.product_id is None or event.product_id == exclude_product_id:
            continue
        recency_factor = max(0.35, 1 - (index * 0.05))
        weight = _event_weight(event.event_type) * recency_factor
        product_scores[event.product_id] = max(product_scores.get(event.product_id, 0.0), weight)
        if len(product_scores) >= limit and index >= limit:
            break

    orders = (
        await db.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.status != OrderStatus.CANCELLED,
            )
        )
    ).scalars().all()
    for order in orders[:8]:
        items = (
            await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        ).scalars().all()
        for item in items:
            if item.product_id == exclude_product_id:
                continue
            product_scores[item.product_id] = max(
                product_scores.get(item.product_id, 0.0),
                EVENT_SIGNAL_WEIGHTS[RecommendationEventType.PURCHASE] * 0.9,
            )
    return dict(
        sorted(
            product_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:limit]
    )


async def _upsert_affinity(
    user_id: int,
    category_id: int | None,
    brand_id: int | None,
    event_type: RecommendationEventType,
    db: AsyncSession,
    *,
    multiplier: float = 1.0,
) -> None:
    weight = _event_weight(event_type) * multiplier
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
        affinity.updated_at = utc_now()
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
        affinity.updated_at = utc_now()


async def _upsert_search_intent_affinities(
    *,
    user_id: int,
    metadata: dict[str, object],
    db: AsyncSession,
) -> None:
    raw_product_ids = metadata.get("product_ids")
    if not isinstance(raw_product_ids, list):
        return

    multipliers = [0.8, 0.65, 0.5, 0.35, 0.25]
    for index, raw_product_id in enumerate(raw_product_ids[: len(multipliers)]):
        try:
            decoded_product_id = int(raw_product_id)
        except (TypeError, ValueError):
            continue
        product = await db.get(Product, decoded_product_id)
        if product is None:
            continue
        await _upsert_affinity(
            user_id,
            product.category_id,
            product.brand_id,
            RecommendationEventType.SEARCH,
            db,
            multiplier=multipliers[index],
        )


async def _update_behavioral_similarity(
    *,
    user_id: int,
    product_id: int,
    event_type: RecommendationEventType,
    db: AsyncSession,
) -> None:
    related_signals = await _recent_user_product_signals(
        user_id=user_id,
        db=db,
        exclude_product_id=product_id,
        limit=12,
    )
    if not related_signals:
        return

    base_delta = max(_event_weight(event_type), 0.5)
    for related_product_id, signal_score in related_signals.items():
        delta = min(0.18 + ((base_delta + signal_score) / 4.5), 1.35)
        await _upsert_similarity_edge(
            product_id=product_id,
            similar_product_id=related_product_id,
            delta=delta,
            reason_code="behavioral_cooccurrence",
            db=db,
        )
        await _upsert_similarity_edge(
            product_id=related_product_id,
            similar_product_id=product_id,
            delta=delta,
            reason_code="behavioral_cooccurrence",
            db=db,
        )


async def _upsert_similarity_edge(
    *,
    product_id: int,
    similar_product_id: int,
    delta: float,
    reason_code: str,
    db: AsyncSession,
) -> None:
    if product_id == similar_product_id:
        return
    existing = (
        await db.execute(
            select(ProductSimilarity).where(
                ProductSimilarity.product_id == product_id,
                ProductSimilarity.similar_product_id == similar_product_id,
            )
        )
    ).scalars().first()
    if existing is None:
        db.add(
            ProductSimilarity(
                product_id=product_id,
                similar_product_id=similar_product_id,
                score=min(delta, 3.5),
                reason_code=reason_code,
            )
        )
        return
    existing.score = min(existing.score + delta, 3.5)
    existing.reason_code = reason_code
    existing.updated_at = utc_now()


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
    for similar in similar_products[:8]:
        base_score = 0.65 if product.brand_id == similar.brand_id else 0.35
        await _upsert_similarity_edge(
            product_id=product.id,
            similar_product_id=similar.id or 0,
            delta=base_score,
            reason_code="category_match",
            db=db,
        )


async def _collaborative_product_scores(
    *,
    user_id: int | None,
    seed_scores: dict[int, float],
    exclude_product_ids: set[int],
    db: AsyncSession,
) -> dict[int, float]:
    if user_id is None or not seed_scores:
        return {}

    overlap_rows = (
        await db.execute(
            select(UserProductEvent).where(
                UserProductEvent.user_id != user_id,
                UserProductEvent.product_id.in_(list(seed_scores.keys())),
            )
        )
    ).scalars().all()

    peer_scores: dict[int, float] = {}
    for row in overlap_rows:
        if row.user_id is None or row.product_id is None:
            continue
        peer_scores[row.user_id] = peer_scores.get(row.user_id, 0.0) + (
            _event_weight(row.event_type) * seed_scores.get(row.product_id, 0.0)
        )

    top_peers = sorted(peer_scores.items(), key=lambda item: item[1], reverse=True)[:10]
    if not top_peers:
        return {}

    peer_weight_map = {peer_id: score for peer_id, score in top_peers}
    peer_events = (
        await db.execute(
            select(UserProductEvent).where(
                UserProductEvent.user_id.in_(list(peer_weight_map.keys())),
                UserProductEvent.product_id != None,  # noqa: E711
            )
        )
    ).scalars().all()

    collaborative_scores: dict[int, float] = {}
    for event in peer_events:
        if event.user_id is None or event.product_id is None:
            continue
        if event.product_id in exclude_product_ids or event.product_id in seed_scores:
            continue
        collaborative_scores[event.product_id] = collaborative_scores.get(event.product_id, 0.0) + (
            peer_weight_map.get(event.user_id, 0.0) * _event_weight(event.event_type)
        )
    return collaborative_scores


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
    if feature_name == "collaborative":
        return "Popular with shoppers whose tastes match yours"
    if feature_name == "recent_interest":
        return "Inspired by what you explored recently"
    if feature_name in {"category_affinity", "brand_affinity"}:
        return "Based on your recent shopping signals"
    if feature_name == "rating":
        return "Highly rated by similar shoppers"
    if feature_name == "price_fit":
        return "Near your usual price range"
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
