from __future__ import annotations

import hashlib
import json

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.catalog.models import Inventory, Product, ProductVariant
from src.apps.commerce.models import Address, Cart, CartItem, TaxRule
from src.apps.core.config import settings
from src.apps.core.time import utc_now
from src.apps.promotions.models import Coupon
from src.apps.promotions.services import calculate_coupon_discount


async def get_or_create_cart(user_id: int, db: AsyncSession) -> Cart:
    cart = (await db.execute(select(Cart).where(Cart.user_id == user_id))).scalars().first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
    cart.updated_at = utc_now()
    return cart


async def build_cart_payload(cart: Cart, db: AsyncSession) -> dict[str, object]:
    items = (
        await db.execute(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.id.desc()))
    ).scalars().all()
    payload_items: list[dict[str, object]] = []
    subtotal = 0.0
    product_ids: set[int] = set()
    category_ids: set[int] = set()
    for item in items:
        variant = await db.get(ProductVariant, item.variant_id)
        if variant is None:
            continue
        product = await db.get(Product, variant.product_id)
        if product:
            product_ids.add(product.id)
            category_ids.add(product.category_id)
        inventory_rows = (
            await db.execute(select(Inventory).where(Inventory.variant_id == variant.id))
        ).scalars().all()
        available_qty = sum(max(inv.quantity - inv.reserved_qty, 0) for inv in inventory_rows)
        line_total = round(item.quantity * variant.selling_price, 2)
        subtotal += line_total
        payload_items.append(
            {
                "id": _encode(item.id),
                "variant_id": _encode(variant.id or 0),
                "product_id": _encode(product.id or 0) if product else None,
                "product_name": product.name if product else "",
                "variant_name": variant.name,
                "sku": variant.sku,
                "quantity": item.quantity,
                "unit_price": variant.selling_price,
                "line_total": line_total,
                "available_qty": available_qty,
            }
        )

    discount = 0.0
    coupon_code = None
    if cart.coupon_id:
        coupon = await db.get(Coupon, cart.coupon_id)
        if coupon:
            discount = await calculate_coupon_discount(
                coupon,
                subtotal,
                db=db,
                user_id=cart.user_id,
                product_ids=product_ids,
                category_ids=category_ids,
            )
            coupon_code = coupon.code

    return {
        "id": _encode(cart.id or 0),
        "coupon_id": _encode(cart.coupon_id) if cart.coupon_id else None,
        "coupon_code": coupon_code,
        "items": payload_items,
        "subtotal": round(subtotal, 2),
        "discount": discount,
        "total": round(max(subtotal - discount, 0.0), 2),
        "product_ids": sorted(product_ids),
        "category_ids": sorted(category_ids),
    }


def _encode(value: int | None) -> str | None:
    if value is None:
        return None
    from src.apps.iam.utils.hashid import encode_id

    return encode_id(value)


async def calculate_tax_amount(
    *,
    address: Address,
    category_ids: set[int],
    taxable_amount: float,
    db: AsyncSession,
) -> dict[str, object]:
    if taxable_amount <= 0:
        return {"tax": 0.0, "rate": 0.0, "rule": None}

    rules = (
        await db.execute(select(TaxRule).where(TaxRule.is_active == True).order_by(TaxRule.priority.asc()))  # noqa: E712
    ).scalars().all()

    matched_rule = None
    matched_specificity = -1
    for rule in rules:
        if rule.country and rule.country.lower() != (address.country or "").lower():
            continue
        if rule.state and rule.state.lower() != (address.state or "").lower():
            continue
        if rule.pincode_prefix and not (address.pincode or "").startswith(rule.pincode_prefix):
            continue
        if rule.category_id and rule.category_id not in category_ids:
            continue

        specificity = sum(
            1
            for matched in (
                bool(rule.state),
                bool(rule.city),
                bool(rule.pincode_prefix),
                bool(rule.category_id),
            )
            if matched
        )
        if matched_rule is None or specificity > matched_specificity:
            matched_rule = rule
            matched_specificity = specificity

    rate = matched_rule.rate if matched_rule else 0.13
    tax = round(max(taxable_amount * rate, 0.0), 2)
    return {
        "tax": tax,
        "rate": rate,
        "rule": matched_rule.name if matched_rule else "default",
    }


def build_quote_fingerprint(
    *,
    cart_payload: dict[str, object],
    address_id: int,
    payment_method: str,
    shipping_quote: dict[str, object],
    tax_payload: dict[str, object],
) -> str:
    canonical = json.dumps(
        {
            "address_id": address_id,
            "payment_method": payment_method,
            "items": [
                {
                    "variant_id": item["variant_id"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                }
                for item in cart_payload["items"]  # type: ignore[index]
            ],
            "subtotal": cart_payload["subtotal"],
            "discount": cart_payload["discount"],
            "shipping_rate": shipping_quote["shipping_rate"],
            "shipping_option": shipping_quote.get("shipping_option"),
            "tax": tax_payload["tax"],
            "tax_rate": tax_payload["rate"],
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def autocomplete_address_suggestions(
    *,
    query: str,
    current_user_id: int,
    db: AsyncSession,
    limit: int = 5,
) -> list[dict[str, object]]:
    normalized = query.strip()
    if not normalized:
        return []

    suggestions: list[dict[str, object]] = []
    saved_addresses = (
        await db.execute(select(Address).where(Address.user_id == current_user_id).order_by(Address.id.desc()))
    ).scalars().all()
    for address in saved_addresses:
        haystack = " ".join(
            filter(
                None,
                [
                    address.name,
                    address.line1,
                    address.line2,
                    address.city,
                    address.state,
                    address.pincode,
                    address.country,
                ],
            )
        ).lower()
        if normalized.lower() in haystack:
            suggestions.append(
                {
                    "source": "saved",
                    "label": ", ".join(filter(None, [address.line1, address.city, address.state, address.pincode])),
                    "city": address.city,
                    "state": address.state,
                    "country": address.country,
                    "pincode": address.pincode,
                    "line1": address.line1,
                    "line2": address.line2,
                }
            )
        if len(suggestions) >= limit:
            return suggestions[:limit]

    if not settings.FEATURE_MAPS:
        return suggestions[:limit]

    try:
        if settings.MAP_PROVIDER == "osm" and settings.OSM_MAPS_ENABLED:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": normalized, "format": "jsonv2", "addressdetails": 1, "limit": max(limit, 5)},
                    headers={"User-Agent": settings.APP_INSTANCE_NAME},
                )
                response.raise_for_status()
                for row in response.json():
                    address = row.get("address", {})
                    suggestions.append(
                        {
                            "source": "osm",
                            "label": row.get("display_name", ""),
                            "city": address.get("city") or address.get("town") or address.get("village") or "",
                            "state": address.get("state", ""),
                            "country": address.get("country", ""),
                            "pincode": address.get("postcode", ""),
                            "line1": address.get("road", ""),
                            "line2": "",
                            "latitude": row.get("lat"),
                            "longitude": row.get("lon"),
                        }
                    )
        elif settings.MAP_PROVIDER == "google" and settings.GOOGLE_MAPS_ENABLED and settings.GOOGLE_MAPS_API_KEY:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/place/autocomplete/json",
                    params={"input": normalized, "key": settings.GOOGLE_MAPS_API_KEY},
                )
                response.raise_for_status()
                for prediction in response.json().get("predictions", []):
                    suggestions.append(
                        {
                            "source": "google",
                            "label": prediction.get("description", ""),
                            "place_id": prediction.get("place_id"),
                            "city": "",
                            "state": "",
                            "country": "",
                            "pincode": "",
                            "line1": prediction.get("structured_formatting", {}).get("main_text", ""),
                            "line2": prediction.get("structured_formatting", {}).get("secondary_text", ""),
                        }
                    )
    except Exception:
        return suggestions[:limit]

    return suggestions[:limit]
