from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from math import log1p
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductSearchDocument,
    ProductStatus,
    ProductVariant,
)
from src.apps.catalog.services import serialize_product
from src.apps.core.time import utc_now
from src.apps.iam.utils.hashid import encode_id
from src.apps.recommendations.models import (
    ProductPopularity,
    ProductSimilarity,
    RecommendationEventType,
    UserAffinity,
    UserProductEvent,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}
_SEARCH_EVENT_WEIGHTS = {
    RecommendationEventType.VIEW: 0.6,
    RecommendationEventType.CLICK: 1.0,
    RecommendationEventType.SEARCH: 0.8,
    RecommendationEventType.ADD_TO_CART: 1.8,
    RecommendationEventType.ADD_TO_WISHLIST: 1.4,
    RecommendationEventType.PURCHASE: 2.6,
    RecommendationEventType.RATING: 1.7,
    RecommendationEventType.RECOMMENDATION_CLICK: 1.2,
}


def normalize_search_text(text: str) -> str:
    tokens = _TOKEN_RE.findall(text.lower())
    return " ".join(tokens)


def tokenize_search_text(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in _STOPWORDS
    ]


def _safe_json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _flatten_search_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        flattened: list[str] = []
        for key, nested in value.items():
            flattened.append(str(key))
            flattened.extend(_flatten_search_values(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_search_values(item))
        return flattened
    return [str(value)]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


async def sync_product_search_document(product_id: int, db: AsyncSession) -> ProductSearchDocument | None:
    product = await db.get(Product, product_id)
    if product is None:
        return None

    category = await db.get(Category, product.category_id)
    brand = await db.get(Brand, product.brand_id) if product.brand_id else None
    variants = (
        await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
    ).scalars().all()

    specification_terms = _flatten_search_values(_safe_json_loads(product.specifications_json or "{}"))
    variant_terms: list[str] = []
    for variant in variants:
        variant_terms.extend(
            [
                variant.name,
                variant.sku,
                *_flatten_search_values(_safe_json_loads(variant.attributes_json or "{}")),
            ]
        )

    title_parts = _dedupe_preserve_order(
        [
            product.name,
            product.slug.replace("-", " "),
            brand.name if brand else "",
        ]
    )
    facet_parts = _dedupe_preserve_order(
        [
            category.name if category else "",
            category.slug.replace("-", " ") if category else "",
            brand.name if brand else "",
            brand.slug.replace("-", " ") if brand else "",
            *specification_terms,
        ]
    )
    keyword_parts = _dedupe_preserve_order(
        [
            *variant_terms,
            product.short_description,
        ]
    )
    searchable_parts = _dedupe_preserve_order(
        [
            *title_parts,
            product.short_description,
            product.description,
            *facet_parts,
            *keyword_parts,
        ]
    )

    document = (
        await db.execute(
            select(ProductSearchDocument).where(ProductSearchDocument.product_id == product.id)
        )
    ).scalars().first()
    if document is None:
        document = ProductSearchDocument(product_id=product.id)
        db.add(document)

    document.title_text = " ".join(title_parts)
    document.summary_text = product.short_description
    document.body_text = product.description
    document.facet_text = " ".join(facet_parts)
    document.keyword_text = " ".join(keyword_parts)
    document.searchable_text = " ".join(searchable_parts)
    document.updated_at = utc_now()
    await db.flush()
    return document


async def sync_product_search_documents(product_ids: list[int], db: AsyncSession) -> None:
    candidate_ids = [product_id for product_id in dict.fromkeys(product_ids) if product_id > 0]
    if not candidate_ids:
        return

    existing_ids = set(
        (
            await db.execute(
                select(ProductSearchDocument.product_id).where(
                    ProductSearchDocument.product_id.in_(candidate_ids)
                )
            )
        ).scalars().all()
    )

    for product_id in candidate_ids:
        if product_id not in existing_ids:
            await sync_product_search_document(product_id, db)


async def delete_product_search_document(product_id: int, db: AsyncSession) -> None:
    document = (
        await db.execute(
            select(ProductSearchDocument).where(ProductSearchDocument.product_id == product_id)
        )
    ).scalars().first()
    if document is not None:
        await db.delete(document)


async def _base_filtered_products(
    *,
    db: AsyncSession,
    category: str | None,
    brand: str | None,
    vendor_id: str | None,
    min_rating: float | None,
    is_featured: bool | None,
) -> list[Product]:
    from src.apps.iam.utils.hashid import decode_id_or_404

    query = select(Product).where(Product.status == ProductStatus.ACTIVE)
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
    return (await db.execute(query.order_by(Product.created_at.desc()))).scalars().all()


def _matches_serialized_filters(
    serialized: dict[str, object],
    *,
    in_stock: bool,
    min_price: float | None,
    max_price: float | None,
    attribute_key: str | None,
    attribute_value: str | None,
) -> bool:
    if in_stock and not bool(serialized["in_stock"]):
        return False
    price_value = float(serialized["min_selling_price"] or 0)
    if min_price is not None and price_value < min_price:
        return False
    if max_price is not None and price_value > max_price:
        return False
    if attribute_key and attribute_value:
        specifications = serialized["specifications"]
        if not isinstance(specifications, dict):
            return False
        value = specifications.get(attribute_key)
        if str(value).lower() != attribute_value.lower():
            return False
    return True


async def _load_search_documents(
    product_ids: list[int],
    db: AsyncSession,
) -> dict[int, ProductSearchDocument]:
    await sync_product_search_documents(product_ids, db)
    rows = (
        await db.execute(
            select(ProductSearchDocument).where(ProductSearchDocument.product_id.in_(product_ids))
        )
    ).scalars().all()
    documents = {row.product_id: row for row in rows}
    missing_ids = [product_id for product_id in product_ids if product_id not in documents]
    for missing_id in missing_ids:
        document = await sync_product_search_document(missing_id, db)
        if document is not None:
            documents[missing_id] = document
    return documents


async def _load_search_personalization(
    *,
    db: AsyncSession,
    user_id: int | None,
) -> tuple[dict[int, float], dict[int, float], dict[int, float], float]:
    if user_id is None:
        return {}, {}, {}, 0.0

    user_affinities = (
        await db.execute(select(UserAffinity).where(UserAffinity.user_id == user_id))
    ).scalars().all()
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

    recent_signal_scores: dict[int, float] = {}
    for index, event in enumerate(recent_events):
        if event.product_id is None:
            continue
        recency_factor = max(0.35, 1 - (index * 0.06))
        weighted = _SEARCH_EVENT_WEIGHTS.get(event.event_type, 0.5) * recency_factor
        existing = recent_signal_scores.get(event.product_id, 0.0)
        recent_signal_scores[event.product_id] = max(existing, weighted)
        if len(recent_signal_scores) >= 12 and index >= 12:
            break

    similarity_boosts: dict[int, float] = {}
    if recent_signal_scores:
        similarity_rows = (
            await db.execute(
                select(ProductSimilarity).where(
                    ProductSimilarity.product_id.in_(list(recent_signal_scores.keys()))
                )
            )
        ).scalars().all()
        for row in similarity_rows:
            similarity_boosts[row.similar_product_id] = similarity_boosts.get(
                row.similar_product_id,
                0.0,
            ) + (row.score * recent_signal_scores.get(row.product_id, 0.0))

    max_similarity = max(similarity_boosts.values(), default=0.0)
    return category_affinity, brand_affinity, similarity_boosts, max_similarity


def _best_fuzzy_ratio(query_token: str, candidate_tokens: list[str]) -> float:
    return max(
        (
            SequenceMatcher(None, query_token, candidate_token).ratio()
            for candidate_token in candidate_tokens[:24]
        ),
        default=0.0,
    )


def _search_reason(matched_fields: set[str]) -> str:
    if "title" in matched_fields:
        return "Strong title match"
    if "facet" in matched_fields:
        return "Matched category, brand, or product attributes"
    if "keywords" in matched_fields:
        return "Matched variants and product keywords"
    if "summary" in matched_fields:
        return "Matched the short product summary"
    return "Matched the full product description"


def _score_document(
    *,
    query: str,
    product: Product,
    document: ProductSearchDocument,
    popularity: ProductPopularity | None,
    category_affinity: dict[int, float],
    brand_affinity: dict[int, float],
    similarity_boosts: dict[int, float],
    max_similarity: float,
) -> tuple[float, set[str]]:
    normalized_query = normalize_search_text(query)
    query_tokens = tokenize_search_text(query)
    if not normalized_query and not query_tokens:
        return 0.0, set()

    title_text = normalize_search_text(document.title_text)
    summary_text = normalize_search_text(document.summary_text)
    body_text = normalize_search_text(document.body_text)
    facet_text = normalize_search_text(document.facet_text)
    keyword_text = normalize_search_text(document.keyword_text)
    searchable_text = normalize_search_text(document.searchable_text)

    title_tokens = tokenize_search_text(document.title_text)
    summary_tokens = tokenize_search_text(document.summary_text)
    body_tokens = tokenize_search_text(document.body_text)
    facet_tokens = tokenize_search_text(document.facet_text)
    keyword_tokens = tokenize_search_text(document.keyword_text)

    score = 0.0
    matched_fields: set[str] = set()

    if normalized_query in title_text:
        score += 8.5
        matched_fields.add("title")
    if normalized_query in facet_text:
        score += 4.0
        matched_fields.add("facet")
    if normalized_query in keyword_text:
        score += 3.4
        matched_fields.add("keywords")
    if normalized_query in summary_text:
        score += 2.8
        matched_fields.add("summary")
    if normalized_query in body_text:
        score += 1.7
        matched_fields.add("body")

    matched_token_count = 0
    for token in query_tokens:
        token_matched = False
        if token in title_tokens:
            score += 3.2
            matched_fields.add("title")
            token_matched = True
        elif any(candidate.startswith(token) for candidate in title_tokens):
            score += 2.2
            matched_fields.add("title")
            token_matched = True
        elif token in facet_tokens:
            score += 2.4
            matched_fields.add("facet")
            token_matched = True
        elif any(candidate.startswith(token) for candidate in facet_tokens):
            score += 1.7
            matched_fields.add("facet")
            token_matched = True
        elif token in keyword_tokens:
            score += 1.8
            matched_fields.add("keywords")
            token_matched = True
        elif any(candidate.startswith(token) for candidate in keyword_tokens):
            score += 1.3
            matched_fields.add("keywords")
            token_matched = True
        elif token in summary_tokens:
            score += 1.3
            matched_fields.add("summary")
            token_matched = True
        elif token in body_tokens:
            score += 0.9
            matched_fields.add("body")
            token_matched = True

        if token_matched:
            matched_token_count += 1
            continue

        fuzzy_ratio = max(
            _best_fuzzy_ratio(token, title_tokens),
            _best_fuzzy_ratio(token, facet_tokens),
            _best_fuzzy_ratio(token, keyword_tokens),
        )
        if fuzzy_ratio >= 0.83:
            score += fuzzy_ratio * 1.6
            matched_fields.add("title")
            matched_token_count += 1
        elif fuzzy_ratio >= 0.73:
            score += fuzzy_ratio * 0.9

    if query_tokens:
        coverage = matched_token_count / len(query_tokens)
        score += coverage * 3.4
        if coverage == 1.0 and len(query_tokens) > 1:
            score += 1.6
    elif normalized_query in searchable_text:
        score += 2.0

    title_similarity = SequenceMatcher(None, normalized_query, title_text).ratio()
    if title_similarity >= 0.45:
        score += title_similarity * 1.4

    popularity_metric = (
        (popularity.view_count if popularity else 0)
        + (popularity.cart_count if popularity else 0) * 2
        + (popularity.wishlist_count if popularity else 0) * 2
        + (popularity.purchase_count if popularity else 0) * 4
    )
    score += min(log1p(popularity_metric) / 8, 0.55)
    score += min(product.avg_rating / 5 * 0.45, 0.45)

    if product.category_id and category_affinity:
        max_category_affinity = max(category_affinity.values(), default=0.0)
        if max_category_affinity > 0:
            score += (
                category_affinity.get(product.category_id, 0.0) / max_category_affinity
            ) * 0.85
    if product.brand_id and brand_affinity:
        max_brand_affinity = max(brand_affinity.values(), default=0.0)
        if max_brand_affinity > 0:
            score += (
                brand_affinity.get(product.brand_id, 0.0) / max_brand_affinity
            ) * 0.55
    if max_similarity > 0:
        score += (similarity_boosts.get(product.id or 0, 0.0) / max_similarity) * 0.95

    if matched_token_count == 0 and normalized_query not in searchable_text:
        return 0.0, set()
    if score < 1.25:
        return 0.0, set()
    return score, matched_fields


async def query_catalog_products(
    *,
    q: str | None,
    category: str | None,
    brand: str | None,
    vendor_id: str | None,
    in_stock: bool,
    min_price: float | None,
    max_price: float | None,
    min_rating: float | None,
    is_featured: bool | None,
    attribute_key: str | None,
    attribute_value: str | None,
    sort: str,
    page: int,
    limit: int,
    user_id: int | None,
    db: AsyncSession,
) -> dict[str, object]:
    products = await _base_filtered_products(
        db=db,
        category=category,
        brand=brand,
        vendor_id=vendor_id,
        min_rating=min_rating,
        is_featured=is_featured,
    )

    filtered_products: list[tuple[Product, dict[str, object]]] = []
    for product in products:
        serialized = await serialize_product(product, db, include_variants=False)
        if _matches_serialized_filters(
            serialized,
            in_stock=in_stock,
            min_price=min_price,
            max_price=max_price,
            attribute_key=attribute_key,
            attribute_value=attribute_value,
        ):
            filtered_products.append((product, serialized))

    if not q:
        items = filtered_products
        if sort == "price_asc":
            items.sort(key=lambda item: item[1]["min_selling_price"] or 0)
        elif sort == "price_desc":
            items.sort(key=lambda item: item[1]["min_selling_price"] or 0, reverse=True)
        elif sort == "rating":
            items.sort(key=lambda item: item[1]["avg_rating"], reverse=True)
        else:
            items.sort(key=lambda item: item[0].created_at, reverse=True)

        start = (page - 1) * limit
        end = start + limit
        return {
            "items": [serialized for _, serialized in items[start:end]],
            "total": len(items),
            "page": page,
            "limit": limit,
        }

    product_ids = [product.id for product, _ in filtered_products if product.id is not None]
    if not product_ids:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "query": q,
            "search_mode": "full_text",
        }

    documents = await _load_search_documents(product_ids, db)
    popularity_map = {
        row.product_id: row
        for row in (await db.execute(select(ProductPopularity))).scalars().all()
    }
    category_affinity, brand_affinity, similarity_boosts, max_similarity = (
        await _load_search_personalization(db=db, user_id=user_id)
    )

    scored_items: list[tuple[float, Product, dict[str, object], set[str]]] = []
    for product, serialized in filtered_products:
        if product.id is None:
            continue
        document = documents.get(product.id)
        if document is None:
            continue
        score, matched_fields = _score_document(
            query=q,
            product=product,
            document=document,
            popularity=popularity_map.get(product.id),
            category_affinity=category_affinity,
            brand_affinity=brand_affinity,
            similarity_boosts=similarity_boosts,
            max_similarity=max_similarity,
        )
        if score <= 0:
            continue
        serialized["search_score"] = round(score, 3)
        serialized["search_reason"] = _search_reason(matched_fields)
        serialized["matched_fields"] = sorted(matched_fields)
        scored_items.append((score, product, serialized, matched_fields))

    if sort == "price_asc":
        scored_items.sort(
            key=lambda item: (item[2]["min_selling_price"] or 0, item[0]),
        )
    elif sort == "price_desc":
        scored_items.sort(
            key=lambda item: (item[2]["min_selling_price"] or 0, item[0]),
            reverse=True,
        )
    elif sort == "rating":
        scored_items.sort(
            key=lambda item: (item[2]["avg_rating"], item[0]),
            reverse=True,
        )
    else:
        scored_items.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)

    start = (page - 1) * limit
    end = start + limit
    return {
        "items": [serialized for _, _, serialized, _ in scored_items[start:end]],
        "total": len(scored_items),
        "page": page,
        "limit": limit,
        "query": q,
        "search_mode": "full_text",
    }


async def autocomplete_catalog_products(
    *,
    q: str,
    limit: int,
    user_id: int | None,
    db: AsyncSession,
) -> dict[str, object]:
    products = (
        await db.execute(
            select(Product).where(Product.status == ProductStatus.ACTIVE).order_by(Product.created_at.desc())
        )
    ).scalars().all()
    product_ids = [product.id for product in products if product.id is not None]
    if not product_ids:
        return {"items": [], "total": 0}

    documents = await _load_search_documents(product_ids, db)
    popularity_map = {
        row.product_id: row
        for row in (await db.execute(select(ProductPopularity))).scalars().all()
    }
    category_affinity, brand_affinity, similarity_boosts, max_similarity = (
        await _load_search_personalization(db=db, user_id=user_id)
    )

    suggestions: list[dict[str, object]] = []
    for product in products:
        if product.id is None:
            continue
        document = documents.get(product.id)
        if document is None:
            continue
        score, matched_fields = _score_document(
            query=q,
            product=product,
            document=document,
            popularity=popularity_map.get(product.id),
            category_affinity=category_affinity,
            brand_affinity=brand_affinity,
            similarity_boosts=similarity_boosts,
            max_similarity=max_similarity,
        )
        if score <= 0:
            continue
        suggestions.append(
            {
                "id": encode_id(product.id),
                "name": product.name,
                "slug": product.slug,
                "score": round(score, 3),
                "reason": _search_reason(matched_fields),
            }
        )

    suggestions.sort(key=lambda item: item["score"], reverse=True)
    return {"items": suggestions[:limit], "total": min(len(suggestions), limit)}
