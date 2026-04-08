from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.security import TokenType, create_access_token, get_password_hash, verify_token
from src.apps.catalog.models import Inventory
from src.apps.finance.models.payment import PaymentProvider, PaymentStatus, PaymentTransaction
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.multitenancy.models.tenant import Tenant, TenantMember, TenantRole
from src.apps.orders.models import InventoryReservation, InventoryReservationStatus, Order


async def _create_user_headers(
    db_session: AsyncSession,
    *,
    username: str,
    email: str,
    is_superuser: bool = False,
) -> tuple[User, dict[str, str]]:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        is_superuser=is_superuser,
        is_confirmed=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProfile(user_id=user.id, first_name=username.title()))

    token = create_access_token(user.id, expires_delta=timedelta(hours=1))
    payload = verify_token(token, token_type=TokenType.ACCESS)
    exp = payload["exp"]
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if isinstance(exp, (int, float)) else datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.add(
        TokenTracking(
            user_id=user.id,
            token_jti=payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address="127.0.0.1",
            user_agent="pytest",
            is_active=True,
            expires_at=expires_at,
        )
    )
    await db_session.commit()
    return user, {"Authorization": f"Bearer {token}"}


async def _create_tenant_for_owner(db_session: AsyncSession, owner: User, slug: str) -> Tenant:
    tenant = Tenant(name=f"{owner.username}-tenant", slug=slug, owner_id=owner.id)
    db_session.add(tenant)
    await db_session.flush()
    db_session.add(TenantMember(tenant_id=tenant.id, user_id=owner.id, role=TenantRole.OWNER))
    await db_session.commit()
    return tenant


async def _create_delivery_zone(client: AsyncClient, admin_headers: dict[str, str], code: str) -> None:
    await client.post(
        "/api/v1/logistics/zones",
        headers=admin_headers,
        json={
            "name": "Kathmandu Valley",
            "code": code,
            "state": "Bagmati",
            "city": "Kathmandu",
            "pincodes": ["44600", "44700"],
            "shipping_rate": 15,
            "cod_enabled": True,
        },
    )


async def _bootstrap_catalog(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(db_session, username="inv_admin", email="inv-admin@example.com", is_superuser=True)
    vendor_user, vendor_headers = await _create_user_headers(db_session, username="inv_vendor", email="inv-vendor@example.com")
    customer_a, customer_a_headers = await _create_user_headers(db_session, username="inv_customer_a", email="inv-a@example.com")
    customer_b, customer_b_headers = await _create_user_headers(db_session, username="inv_customer_b", email="inv-b@example.com")

    tenant = await _create_tenant_for_owner(db_session, vendor_user, "inv-tenant")

    vendor_create = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Inventory Vendor Pvt Ltd",
            "display_name": "Inventory Vendor",
            "slug": "inventory-vendor",
            "description": "Vendor for inventory reservation tests",
        },
    )
    assert vendor_create.status_code == 201, vendor_create.text
    vendor_id = vendor_create.json()["vendor"]["id"]
    approve_vendor = await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    assert approve_vendor.status_code == 200, approve_vendor.text

    await _create_delivery_zone(client, admin_headers, code="inv-zone")

    wh_1 = await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "WH-1"})
    wh_2 = await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "WH-2"})
    assert wh_1.status_code == 201, wh_1.text
    assert wh_2.status_code == 201, wh_2.text

    await client.post("/api/v1/admin/categories", headers=admin_headers, json={"name": "Accessories", "slug": "accessories", "level": 1})
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Inventory Brand", "slug": "inventory-brand"},
    )
    brand_id = brand_resp.json()["brand"]["id"]

    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Inventory Test Product",
            "slug": "inventory-test-product",
            "variants": [{"sku": "INV-1", "name": "Default", "mrp": 100, "selling_price": 90, "quantity": 2, "is_default": True}],
        },
    )
    product_id = product_resp.json()["product"]["id"]
    approve_product = await client.post(f"/api/v1/admin/catalog/products/{product_id}/approve", headers=admin_headers)
    variant_id = approve_product.json()["product"]["variants"][0]["id"]

    address_payload = {
        "name": "Home",
        "phone": "+9779800000002",
        "line1": "Koteshwor",
        "city": "Kathmandu",
        "state": "Bagmati",
        "pincode": "44600",
    }
    address_a = await client.post("/api/v1/addresses", headers=customer_a_headers, json=address_payload)
    address_b = await client.post("/api/v1/addresses", headers=customer_b_headers, json=address_payload | {"name": "Office"})

    return {
        "admin": admin,
        "admin_headers": admin_headers,
        "vendor_headers": vendor_headers,
        "customer_a": customer_a,
        "customer_a_headers": customer_a_headers,
        "customer_b": customer_b,
        "customer_b_headers": customer_b_headers,
        "variant_id": variant_id,
        "address_a_id": address_a.json()["address"]["id"],
        "address_b_id": address_b.json()["address"]["id"],
    }


async def _create_online_tx(db_session: AsyncSession, *, user_id: int, purchase_order_id: str) -> PaymentTransaction:
    tx = PaymentTransaction(
        provider=PaymentProvider.STRIPE,
        amount=10_000,
        currency="NPR",
        status=PaymentStatus.INITIATED,
        purchase_order_id=purchase_order_id,
        purchase_order_name=f"Order {purchase_order_id}",
        provider_pidx=f"session-{purchase_order_id}",
        return_url="http://localhost/payment/callback",
        website_url="http://localhost",
        user_id=user_id,
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)
    return tx


@pytest.mark.asyncio
async def test_online_checkout_reservation_commit_and_release(client: AsyncClient, db_session: AsyncSession):
    ctx = await _bootstrap_catalog(client, db_session)

    await client.post("/api/v1/cart/items", headers=ctx["customer_a_headers"], json={"variant_id": ctx["variant_id"], "quantity": 1})
    tx_commit = await _create_online_tx(db_session, user_id=ctx["customer_a"].id, purchase_order_id="reserve-commit")
    checkout_commit = await client.post(
        "/api/v1/checkout",
        headers=ctx["customer_a_headers"],
        json={"address_id": ctx["address_a_id"], "payment_method": "stripe", "payment_transaction_id": encode_id(tx_commit.id)},
    )
    assert checkout_commit.status_code == 201, checkout_commit.text

    order_id = decode_id_or_404(checkout_commit.json()["order"]["id"])
    reserve_rows = (
        await db_session.execute(
            select(InventoryReservation).where(
                InventoryReservation.order_id == order_id,
                InventoryReservation.status == InventoryReservationStatus.ACTIVE,
            )
        )
    ).scalars().all()
    assert sum(row.quantity for row in reserve_rows) == 1

    capture_resp = await client.post(f"/api/v1/payments/{encode_id(tx_commit.id)}/capture/", headers=ctx["customer_a_headers"], json={"amount": tx_commit.amount})
    assert capture_resp.status_code == 200, capture_resp.text
    committed_order = await db_session.get(Order, order_id)
    assert committed_order is not None
    assert committed_order.status.value == "confirmed"
    assert committed_order.payment_status.value == "paid"

    await client.post("/api/v1/cart/items", headers=ctx["customer_a_headers"], json={"variant_id": ctx["variant_id"], "quantity": 1})
    tx_void = await _create_online_tx(db_session, user_id=ctx["customer_a"].id, purchase_order_id="reserve-release")
    checkout_void = await client.post(
        "/api/v1/checkout",
        headers=ctx["customer_a_headers"],
        json={"address_id": ctx["address_a_id"], "payment_method": "stripe", "payment_transaction_id": encode_id(tx_void.id)},
    )
    assert checkout_void.status_code == 201, checkout_void.text

    void_resp = await client.post(f"/api/v1/payments/{encode_id(tx_void.id)}/void/", headers=ctx["customer_a_headers"])
    assert void_resp.status_code == 200, void_resp.text
    void_order_id = decode_id_or_404(checkout_void.json()["order"]["id"])
    void_order = await db_session.get(Order, void_order_id)
    assert void_order is not None
    assert void_order.status.value == "cancelled"
    assert void_order.payment_status.value == "failed"


@pytest.mark.asyncio
async def test_expired_reservation_does_not_commit_on_late_callback(client: AsyncClient, db_session: AsyncSession):
    ctx = await _bootstrap_catalog(client, db_session)

    await client.post("/api/v1/cart/items", headers=ctx["customer_a_headers"], json={"variant_id": ctx["variant_id"], "quantity": 1})
    tx = await _create_online_tx(db_session, user_id=ctx["customer_a"].id, purchase_order_id="expired-callback")
    checkout_resp = await client.post(
        "/api/v1/checkout",
        headers=ctx["customer_a_headers"],
        json={"address_id": ctx["address_a_id"], "payment_method": "stripe", "payment_transaction_id": encode_id(tx.id)},
    )
    assert checkout_resp.status_code == 201, checkout_resp.text

    order_id = decode_id_or_404(checkout_resp.json()["order"]["id"])
    rows = (await db_session.execute(select(InventoryReservation).where(InventoryReservation.order_id == order_id))).scalars().all()
    assert rows
    for row in rows:
        row.reserved_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    capture_resp = await client.post(f"/api/v1/payments/{encode_id(tx.id)}/capture/", headers=ctx["customer_a_headers"], json={"amount": tx.amount})
    assert capture_resp.status_code == 200, capture_resp.text

    order = await db_session.get(Order, order_id)
    assert order is not None
    assert order.status.value == "cancelled"
    assert order.payment_status.value == "failed"


@pytest.mark.asyncio
async def test_partial_stock_across_warehouses_and_cart_changes_do_not_overcommit(client: AsyncClient, db_session: AsyncSession):
    ctx = await _bootstrap_catalog(client, db_session)

    inventory_rows = (await db_session.execute(select(Inventory).where(Inventory.variant_id == decode_id_or_404(ctx["variant_id"])))).scalars().all()
    assert inventory_rows
    inventory_rows[0].quantity = 1
    if len(inventory_rows) == 1:
        db_session.add(Inventory(variant_id=inventory_rows[0].variant_id, warehouse_id=None, quantity=1, reserved_qty=0))
    else:
        inventory_rows[1].quantity = 1
    await db_session.commit()

    await client.post("/api/v1/cart/items", headers=ctx["customer_a_headers"], json={"variant_id": ctx["variant_id"], "quantity": 2})
    tx = await _create_online_tx(db_session, user_id=ctx["customer_a"].id, purchase_order_id="partial-wh")
    checkout_resp = await client.post(
        "/api/v1/checkout",
        headers=ctx["customer_a_headers"],
        json={"address_id": ctx["address_a_id"], "payment_method": "stripe", "payment_transaction_id": encode_id(tx.id)},
    )
    assert checkout_resp.status_code == 201, checkout_resp.text

    order_id = decode_id_or_404(checkout_resp.json()["order"]["id"])
    reserved_rows = (
        await db_session.execute(
            select(InventoryReservation).where(
                InventoryReservation.order_id == order_id,
                InventoryReservation.status == InventoryReservationStatus.ACTIVE,
            )
        )
    ).scalars().all()
    assert len(reserved_rows) >= 2
    assert sum(row.quantity for row in reserved_rows) == 2

    await client.post("/api/v1/cart/items", headers=ctx["customer_a_headers"], json={"variant_id": ctx["variant_id"], "quantity": 4})
    capture_resp = await client.post(f"/api/v1/payments/{encode_id(tx.id)}/capture/", headers=ctx["customer_a_headers"], json={"amount": tx.amount})
    assert capture_resp.status_code == 200, capture_resp.text

    order = await db_session.get(Order, order_id)
    assert order is not None
    assert order.status.value == "confirmed"
    assert len(checkout_resp.json()["order"]["items"]) == 1
    assert checkout_resp.json()["order"]["items"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_concurrent_low_stock_checkout_allows_single_winner(client: AsyncClient, db_session: AsyncSession):
    ctx = await _bootstrap_catalog(client, db_session)

    await client.patch(
        f"/api/v1/vendor/inventory/{ctx['variant_id']}",
        headers=ctx["vendor_headers"],
        json={"quantity": 1, "reorder_level": 1, "reorder_qty": 1},
    )

    await client.post("/api/v1/cart/items", headers=ctx["customer_a_headers"], json={"variant_id": ctx["variant_id"], "quantity": 1})
    await client.post("/api/v1/cart/items", headers=ctx["customer_b_headers"], json={"variant_id": ctx["variant_id"], "quantity": 1})

    tx_a = await _create_online_tx(db_session, user_id=ctx["customer_a"].id, purchase_order_id="race-a")
    tx_b = await _create_online_tx(db_session, user_id=ctx["customer_b"].id, purchase_order_id="race-b")

    async def _checkout(headers: dict[str, str], address_id: str, tx_id: int):
        return await client.post(
            "/api/v1/checkout",
            headers=headers,
            json={"address_id": address_id, "payment_method": "stripe", "payment_transaction_id": encode_id(tx_id)},
        )

    resp_a, resp_b = await asyncio.gather(
        _checkout(ctx["customer_a_headers"], ctx["address_a_id"], tx_a.id),
        _checkout(ctx["customer_b_headers"], ctx["address_b_id"], tx_b.id),
    )

    status_codes = sorted([resp_a.status_code, resp_b.status_code])
    assert status_codes == [201, 400]
