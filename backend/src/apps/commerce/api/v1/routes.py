from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.catalog.models import Product, ProductVariant
from src.apps.commerce.models import Address, CartItem, WishlistItem
from src.apps.commerce.services import build_cart_payload, get_or_create_cart
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.orders.models import Order
from src.apps.promotions.models import Coupon
from src.apps.recommendations.models import RecommendationEventType, UserProductEvent

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
        db.add(
            UserProductEvent(
                user_id=current_user.id,
                product_id=product.id,
                event_type=RecommendationEventType.ADD_TO_CART,
            )
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
    cart.updated_at = datetime.utcnow()
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
            payload.append({"id": encode_id(item.id or 0), "product_id": encode_id(product.id or 0), "name": product.name})
    return {"items": payload, "total": len(payload)}


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
        db.add(
            UserProductEvent(
                user_id=current_user.id,
                product_id=decoded_id,
                event_type=RecommendationEventType.ADD_TO_WISHLIST,
            )
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
