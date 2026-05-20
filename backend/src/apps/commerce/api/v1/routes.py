from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.catalog.models import Product, ProductImage, ProductVariant
from src.apps.commerce.models import (
    Address,
    CartItem,
    TaxRule,
    WishlistItem,
    WishlistShareLink,
)
from src.apps.commerce.services import (
    autocomplete_address_suggestions,
    build_cart_payload,
    calculate_tax_amount,
    get_or_create_cart,
)
from src.apps.core.models import Banner, StaticPage, StaticPageStatus
from src.apps.core.time import utc_now
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.orders.models import Order
from src.apps.promotions.models import Coupon
from src.apps.recommendations.models import RecommendationEventType
from src.apps.recommendations.services import record_recommendation_event

router = APIRouter()


class AddressCreateRequest(BaseModel):
    name: str
    phone: str
    line1: str
    line2: str = ""
    city: str
    state: str
    pincode: str
    country: str = "Nepal"
    landmark: str = ""
    type: str = "home"
    is_default: bool = False


class AddressUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    country: str | None = None
    landmark: str | None = None
    type: str | None = None
    is_default: bool | None = None


class CartItemCreateRequest(BaseModel):
    variant_id: str
    quantity: int = Field(default=1, ge=1)


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(ge=1)


class ApplyCouponRequest(BaseModel):
    code: str


class TaxRuleCreateRequest(BaseModel):
    name: str
    country: str = "Nepal"
    state: str = ""
    city: str = ""
    pincode_prefix: str = ""
    category_id: str | None = None
    rate: float = Field(default=0.13, ge=0)
    priority: int = 100
    is_active: bool = True


class WishlistShareLinkCreateRequest(BaseModel):
    title: str = Field(default="", max_length=255)


class BannerCreateRequest(BaseModel):
    title: str
    subtitle: str = ""
    image_url: str = ""
    cta_label: str = ""
    cta_url: str = ""
    placement: str = "home"
    is_active: bool = True
    sort_order: int = 0


class StaticPageCreateRequest(BaseModel):
    slug: str
    title: str
    summary: str = ""
    body_markdown: str = ""
    status: StaticPageStatus = StaticPageStatus.DRAFT
    seo_title: str = ""
    seo_description: str = ""


def _serialize_address(address: Address) -> dict[str, object]:
    return {
        "id": encode_id(address.id or 0),
        "name": address.name,
        "phone": address.phone,
        "line1": address.line1,
        "line2": address.line2,
        "city": address.city,
        "state": address.state,
        "pincode": address.pincode,
        "country": address.country,
        "landmark": address.landmark,
        "type": address.type,
        "is_default": address.is_default,
    }


async def _serialize_wishlist_product(product: Product, db: AsyncSession) -> dict[str, object]:
    primary_image = (
        await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.is_primary.desc(), ProductImage.position.asc(), ProductImage.id.asc())
        )
    ).scalars().first()
    variants = (
        await db.execute(
            select(ProductVariant)
            .where(ProductVariant.product_id == product.id)
            .order_by(ProductVariant.is_default.desc(), ProductVariant.id.asc())
        )
    ).scalars().all()
    default_variant = variants[0] if variants else None
    return {
        "product_id": encode_id(product.id or 0),
        "name": product.name,
        "slug": product.slug,
        "status": product.status.value,
        "image_url": primary_image.url if primary_image else "",
        "price": default_variant.selling_price if default_variant else None,
        "variant_id": encode_id(default_variant.id or 0) if default_variant else None,
        "variant_name": default_variant.name if default_variant else "",
    }


def _serialize_share_link(link: WishlistShareLink) -> dict[str, object]:
    return {
        "id": encode_id(link.id or 0),
        "token": link.token,
        "title": link.title,
        "is_active": link.is_active,
        "created_at": link.created_at.isoformat(),
        "updated_at": link.updated_at.isoformat(),
    }


async def _ensure_default_address(user_id: int, db: AsyncSession) -> None:
    default_address = (
        await db.execute(select(Address).where(Address.user_id == user_id, Address.is_default == True))  # noqa: E712
    ).scalars().first()
    if default_address is not None:
        return
    fallback = (
        await db.execute(select(Address).where(Address.user_id == user_id).order_by(Address.id.asc()))
    ).scalars().first()
    if fallback is not None:
        fallback.is_default = True


@router.get("/addresses")
async def list_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addresses = (
        await db.execute(select(Address).where(Address.user_id == current_user.id).order_by(Address.id.desc()))
    ).scalars().all()
    return {
        "items": [_serialize_address(address) for address in addresses],
        "total": len(addresses),
    }


@router.get("/addresses/autocomplete")
async def autocomplete_addresses(
    q: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {
        "items": await autocomplete_address_suggestions(
            query=q,
            current_user_id=current_user.id,
            db=db,
            limit=limit,
        )
    }


@router.post("/addresses", status_code=status.HTTP_201_CREATED)
async def create_address(
    payload: AddressCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.is_default:
        existing = (await db.execute(select(Address).where(Address.user_id == current_user.id))).scalars().all()
        for address in existing:
            address.is_default = False
    address = Address(user_id=current_user.id, **payload.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return {"address": _serialize_address(address)}


@router.patch("/addresses/{address_id}")
async def update_address(
    address_id: str,
    payload: AddressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, decode_id_or_404(address_id))
    if address is None or address.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_default") is True:
        existing = (await db.execute(select(Address).where(Address.user_id == current_user.id))).scalars().all()
        for existing_address in existing:
            existing_address.is_default = False
    for field_name, value in updates.items():
        setattr(address, field_name, value)
    await _ensure_default_address(current_user.id, db)
    await db.commit()
    await db.refresh(address)
    return {"address": _serialize_address(address)}


@router.post("/addresses/{address_id}/default")
async def set_default_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, decode_id_or_404(address_id))
    if address is None or address.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    existing = (await db.execute(select(Address).where(Address.user_id == current_user.id))).scalars().all()
    for existing_address in existing:
        existing_address.is_default = existing_address.id == address.id
    await db.commit()
    await db.refresh(address)
    return {"address": _serialize_address(address)}


@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, decode_id_or_404(address_id))
    if address is None or address.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    deleted_was_default = address.is_default
    await db.delete(address)
    await db.flush()
    if deleted_was_default:
        await _ensure_default_address(current_user.id, db)
    await db.commit()
    return {"success": True}


@router.get("/cart")
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await get_or_create_cart(current_user.id, db)
    await db.commit()
    return await build_cart_payload(cart, db)


@router.post("/cart/items", status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    payload: CartItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    variant = await db.get(ProductVariant, decode_id_or_404(payload.variant_id))
    if variant is None or not variant.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    cart = await get_or_create_cart(current_user.id, db)
    existing = (
        await db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant.id)
        )
    ).scalars().first()
    if existing:
        existing.quantity += payload.quantity
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                variant_id=variant.id,
                quantity=payload.quantity,
                price_at_add=variant.selling_price,
            )
        )
    product = await db.get(Product, variant.product_id)
    if product:
        await record_recommendation_event(
            user_id=current_user.id,
            product_id=product.id,
            event_type=RecommendationEventType.ADD_TO_CART,
            placement=None,
            query_text="",
            metadata={"variant_id": variant.id, "quantity": payload.quantity},
            db=db,
        )
    await db.commit()
    await analytics.capture(str(current_user.id), "cart_item_added", {"variant_id": variant.id, "quantity": payload.quantity})
    return await build_cart_payload(cart, db)


@router.patch("/cart/items/{item_id}")
async def update_cart_item(
    item_id: str,
    payload: CartItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await get_or_create_cart(current_user.id, db)
    item = await db.get(CartItem, decode_id_or_404(item_id))
    if item is None or item.cart_id != cart.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    item.quantity = payload.quantity
    cart.updated_at = utc_now()
    await db.commit()
    return await build_cart_payload(cart, db)


@router.delete("/cart/items/{item_id}")
async def remove_cart_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await get_or_create_cart(current_user.id, db)
    item = await db.get(CartItem, decode_id_or_404(item_id))
    if item is None or item.cart_id != cart.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    await db.delete(item)
    await db.commit()
    return await build_cart_payload(cart, db)


@router.post("/cart/coupon")
async def apply_cart_coupon(
    payload: ApplyCouponRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await get_or_create_cart(current_user.id, db)
    coupon = (await db.execute(select(Coupon).where(Coupon.code == payload.code.upper()))).scalars().first()
    if coupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    cart.coupon_id = coupon.id
    await db.commit()
    return await build_cart_payload(cart, db)


@router.get("/wishlist")
async def list_wishlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = (
        await db.execute(select(WishlistItem).where(WishlistItem.user_id == current_user.id).order_by(WishlistItem.id.desc()))
    ).scalars().all()
    payload = []
    for item in items:
        product = await db.get(Product, item.product_id)
        if product:
            payload.append({"id": encode_id(item.id or 0), **(await _serialize_wishlist_product(product, db))})
    return {"items": payload, "total": len(payload)}


@router.post("/wishlist/share-links", status_code=status.HTTP_201_CREATED)
async def create_wishlist_share_link(
    payload: WishlistShareLinkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    link = WishlistShareLink(
        user_id=current_user.id,
        token=secrets.token_urlsafe(18),
        title=payload.title.strip(),
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return {"share_link": _serialize_share_link(link)}


@router.get("/wishlist/share-links")
async def list_wishlist_share_links(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    links = (
        await db.execute(
            select(WishlistShareLink)
            .where(WishlistShareLink.user_id == current_user.id)
            .order_by(WishlistShareLink.created_at.desc())
        )
    ).scalars().all()
    return {"items": [_serialize_share_link(link) for link in links], "total": len(links)}


@router.delete("/wishlist/share-links/{share_id}")
async def revoke_wishlist_share_link(
    share_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    link = await db.get(WishlistShareLink, decode_id_or_404(share_id))
    if link is None or link.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    link.is_active = False
    link.updated_at = utc_now()
    await db.commit()
    return {"success": True}


@router.get("/wishlist/shared/{token}")
async def get_shared_wishlist(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    link = (
        await db.execute(select(WishlistShareLink).where(WishlistShareLink.token == token, WishlistShareLink.is_active == True))  # noqa: E712
    ).scalars().first()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared wishlist not found")
    owner = await db.get(User, link.user_id)
    items = (
        await db.execute(select(WishlistItem).where(WishlistItem.user_id == link.user_id).order_by(WishlistItem.id.desc()))
    ).scalars().all()
    payload = []
    for item in items:
        product = await db.get(Product, item.product_id)
        if product:
            payload.append(await _serialize_wishlist_product(product, db))
    return {
        "share_link": _serialize_share_link(link),
        "owner": {"username": owner.username if owner else "unknown"},
        "items": payload,
        "total": len(payload),
    }


@router.get("/content/banners")
async def list_active_banners(
    placement: str = "home",
    db: AsyncSession = Depends(get_db),
):
    banners = (
        await db.execute(
            select(Banner).where(Banner.placement == placement, Banner.is_active == True).order_by(Banner.sort_order.asc(), Banner.id.desc())  # noqa: E712
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(banner.id or 0),
                "title": banner.title,
                "subtitle": banner.subtitle,
                "image_url": banner.image_url,
                "cta_label": banner.cta_label,
                "cta_url": banner.cta_url,
                "placement": banner.placement,
            }
            for banner in banners
        ],
        "total": len(banners),
    }


@router.get("/content/pages/{slug}")
async def get_static_page(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    page = (
        await db.execute(select(StaticPage).where(StaticPage.slug == slug, StaticPage.status == StaticPageStatus.PUBLISHED))
    ).scalars().first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return {
        "page": {
            "id": encode_id(page.id or 0),
            "slug": page.slug,
            "title": page.title,
            "summary": page.summary,
            "body_markdown": page.body_markdown,
            "seo_title": page.seo_title,
            "seo_description": page.seo_description,
            "published_at": page.published_at.isoformat() if page.published_at else None,
        }
    }


@router.post("/wishlist/{product_id}", status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    decoded_id = decode_id_or_404(product_id)
    product = await db.get(Product, decoded_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    existing = (
        await db.execute(
            select(WishlistItem).where(WishlistItem.user_id == current_user.id, WishlistItem.product_id == decoded_id)
        )
    ).scalars().first()
    if existing is None:
        db.add(WishlistItem(user_id=current_user.id, product_id=decoded_id))
        await record_recommendation_event(
            user_id=current_user.id,
            product_id=decoded_id,
            event_type=RecommendationEventType.ADD_TO_WISHLIST,
            placement=None,
            query_text="",
            metadata={},
            db=db,
        )
        await db.commit()
    return {"success": True}


@router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == current_user.id,
                WishlistItem.product_id == decode_id_or_404(product_id),
            )
        )
    ).scalars().first()
    if item:
        await db.delete(item)
        await db.commit()
    return {"success": True}


@router.get("/admin/customers")
async def list_customers(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    customers = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    items = []
    for customer in customers:
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == customer.id))
        ).scalars().first()
        order_count = (
            await db.execute(select(Order).where(Order.user_id == customer.id))
        ).scalars().all()
        items.append(
            {
                "id": encode_id(customer.id or 0),
                "email": customer.email,
                "username": customer.username,
                "is_active": customer.is_active,
                "is_superuser": customer.is_superuser,
                "first_name": profile.first_name if profile else "",
                "last_name": profile.last_name if profile else "",
                "order_count": len(order_count),
                "created_at": customer.created_at.isoformat(),
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/admin/content/banners", status_code=status.HTTP_201_CREATED)
async def create_banner(
    payload: BannerCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    banner = Banner(**payload.model_dump())
    db.add(banner)
    await db.commit()
    await db.refresh(banner)
    return {"banner_id": encode_id(banner.id or 0)}


@router.get("/admin/content/banners")
async def list_admin_banners(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    banners = (await db.execute(select(Banner).order_by(Banner.sort_order.asc(), Banner.id.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(banner.id or 0),
                "title": banner.title,
                "placement": banner.placement,
                "is_active": banner.is_active,
                "sort_order": banner.sort_order,
            }
            for banner in banners
        ],
        "total": len(banners),
    }


@router.post("/admin/content/pages", status_code=status.HTTP_201_CREATED)
async def create_static_page(
    payload: StaticPageCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    page = StaticPage(
        **payload.model_dump(),
        published_at=utc_now() if payload.status == StaticPageStatus.PUBLISHED else None,
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return {"page_id": encode_id(page.id or 0)}


@router.get("/admin/content/pages")
async def list_admin_pages(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    pages = (await db.execute(select(StaticPage).order_by(StaticPage.updated_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(page.id or 0),
                "slug": page.slug,
                "title": page.title,
                "status": page.status.value,
                "published_at": page.published_at.isoformat() if page.published_at else None,
            }
            for page in pages
        ],
        "total": len(pages),
    }


@router.get("/admin/customers/{customer_id}")
async def get_customer_detail(
    customer_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    customer = await db.get(User, decode_id_or_404(customer_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == customer.id))
    ).scalars().first()
    orders = (
        await db.execute(select(Order).where(Order.user_id == customer.id).order_by(Order.created_at.desc()))
    ).scalars().all()
    return {
        "customer": {
            "id": encode_id(customer.id or 0),
            "email": customer.email,
            "username": customer.username,
            "is_active": customer.is_active,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "phone": profile.phone if profile else "",
        },
        "orders": [{"id": encode_id(order.id or 0), "order_number": order.order_number, "total": order.total, "status": order.status.value} for order in orders],
    }


@router.post("/admin/tax-rules", status_code=status.HTTP_201_CREATED)
async def create_tax_rule(
    payload: TaxRuleCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    tax_rule = TaxRule(
        name=payload.name,
        country=payload.country,
        state=payload.state,
        city=payload.city,
        pincode_prefix=payload.pincode_prefix,
        category_id=decode_id_or_404(payload.category_id) if payload.category_id else None,
        rate=payload.rate,
        priority=payload.priority,
        is_active=payload.is_active,
    )
    db.add(tax_rule)
    await db.commit()
    await db.refresh(tax_rule)
    return {
        "tax_rule": {
            "id": encode_id(tax_rule.id or 0),
            "name": tax_rule.name,
            "rate": tax_rule.rate,
            "priority": tax_rule.priority,
        }
    }


@router.get("/admin/tax-rules")
async def list_tax_rules(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    rules = (await db.execute(select(TaxRule).order_by(TaxRule.priority.asc(), TaxRule.id.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(rule.id or 0),
                "name": rule.name,
                "country": rule.country,
                "state": rule.state,
                "city": rule.city,
                "pincode_prefix": rule.pincode_prefix,
                "category_id": encode_id(rule.category_id) if rule.category_id else None,
                "rate": rule.rate,
                "priority": rule.priority,
                "is_active": rule.is_active,
            }
            for rule in rules
        ],
        "total": len(rules),
    }


@router.get("/admin/tax-rules/estimate")
async def estimate_tax(
    address_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, decode_id_or_404(address_id))
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    taxable_amount = 0.0
    category_ids: set[int] = set()
    orders = (await db.execute(select(Order).where(Order.address_id == address.id))).scalars().all()
    for order in orders:
        taxable_amount += order.subtotal
    tax_payload = await calculate_tax_amount(address=address, category_ids=category_ids, taxable_amount=taxable_amount, db=db)
    return tax_payload
