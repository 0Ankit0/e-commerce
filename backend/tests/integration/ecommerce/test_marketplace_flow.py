from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.config import settings
from src.apps.core.security import TokenType, create_access_token, get_password_hash, verify_token
from src.apps.finance.models.payment import PaymentProvider, PaymentStatus, PaymentTransaction
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User, UserProfile
from src.apps.messaging.models import ChatMessageEnvelope
from src.apps.multitenancy.models.tenant import Tenant, TenantMember, TenantRole
from src.apps.orders.models import Order, ReturnRequest, VendorOrder


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


async def _create_delivery_zone(client: AsyncClient, admin_headers: dict[str, str], code: str = "ktm-zone") -> None:
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


@pytest.mark.asyncio
async def test_marketplace_checkout_and_recommendations(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="market_admin",
        email="admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="vendor_owner",
        email="vendor@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="shopper",
        email="shopper@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "vendor-tenant")

    vendor_create = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": tenant.id and __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id(tenant.id),
            "business_name": "Vendor Pvt Ltd",
            "display_name": "Vendor Store",
            "slug": "vendor-store",
            "description": "Trusted electronics seller",
        },
    )
    assert vendor_create.status_code == 201, vendor_create.text
    vendor_id = vendor_create.json()["vendor"]["id"]

    approve_vendor = await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    assert approve_vendor.status_code == 200, approve_vendor.text
    await _create_delivery_zone(client, admin_headers)

    category_resp = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Electronics", "slug": "electronics", "level": 1, "attributes": [{"name": "color"}]},
    )
    assert category_resp.status_code == 201, category_resp.text
    category_id = category_resp.json()["category"]["id"]

    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Acme Audio", "slug": "acme-audio"},
    )
    assert brand_resp.status_code == 201, brand_resp.text
    brand_id = brand_resp.json()["brand"]["id"]

    coupon_resp = await client.post(
        "/api/v1/admin/promotions/coupons",
        headers=admin_headers,
        json={"code": "WELCOME10", "value": 10, "type": "percentage", "max_discount": 100},
    )
    assert coupon_resp.status_code == 201, coupon_resp.text

    warehouse_resp = await client.post(
        "/api/v1/vendor/warehouses",
        headers=vendor_headers,
        json={"name": "Main Warehouse", "city": "Kathmandu", "is_default": True},
    )
    assert warehouse_resp.status_code == 201, warehouse_resp.text

    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Wireless Headphones",
            "slug": "wireless-headphones",
            "short_description": "Noise cancelling",
            "description": "Premium over-ear wireless headphones",
            "status": "pending",
            "variants": [
                {
                    "sku": "WH-001",
                    "name": "Black",
                    "mrp": 120,
                    "selling_price": 99,
                    "quantity": 5,
                    "is_default": True,
                }
            ],
            "images": [{"url": "https://example.com/headphones.jpg", "is_primary": True}],
        },
    )
    assert product_resp.status_code == 201, product_resp.text
    product_id = product_resp.json()["product"]["id"]

    approve_product = await client.post(
        f"/api/v1/admin/catalog/products/{product_id}/approve",
        headers=admin_headers,
    )
    assert approve_product.status_code == 200, approve_product.text

    product_list = await client.get("/api/v1/products")
    assert product_list.status_code == 200
    assert product_list.json()["total"] == 1

    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={
            "name": "Home",
            "phone": "+9779800000000",
            "line1": "Baneshwor",
            "city": "Kathmandu",
            "state": "Bagmati",
            "pincode": "44600",
            "is_default": True,
        },
    )
    assert address_resp.status_code == 201, address_resp.text
    address_id = address_resp.json()["address"]["id"]
    update_address = await client.patch(
        f"/api/v1/addresses/{address_id}",
        headers=customer_headers,
        json={"landmark": "Near temple"},
    )
    assert update_address.status_code == 200, update_address.text
    assert update_address.json()["address"]["landmark"] == "Near temple"

    add_cart = await client.post(
        "/api/v1/cart/items",
        headers=customer_headers,
        json={"variant_id": approve_product.json()["product"]["variants"][0]["id"], "quantity": 2},
    )
    assert add_cart.status_code == 201, add_cart.text
    assert add_cart.json()["subtotal"] == 198

    apply_coupon = await client.post(
        "/api/v1/cart/coupon",
        headers=customer_headers,
        json={"code": "WELCOME10"},
    )
    assert apply_coupon.status_code == 200, apply_coupon.text
    assert apply_coupon.json()["discount"] == 19.8

    checkout_resp = await client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"address_id": address_id, "payment_method": "cod"},
    )
    assert checkout_resp.status_code == 201, checkout_resp.text
    order = checkout_resp.json()["order"]
    assert order["status"] == "confirmed"
    assert order["shipping_charge"] == 15
    assert len(order["vendor_orders"]) == 1
    assert len(order["shipments"]) == 1

    tracking_resp = await client.get(f"/api/v1/tracking/{order['id']}", headers=customer_headers)
    assert tracking_resp.status_code == 200, tracking_resp.text
    assert tracking_resp.json()["shipments"][0]["events"][0]["status"] == "confirmed"

    event_resp = await client.post(
        "/api/v1/recommendations/events",
        headers=customer_headers,
        json={"event_type": "view", "product_id": product_id, "placement": "home"},
    )
    assert event_resp.status_code == 201, event_resp.text

    recommendations_resp = await client.get(
        "/api/v1/recommendations",
        headers=customer_headers,
        params={"type": "home", "limit": 5},
    )
    assert recommendations_resp.status_code == 200, recommendations_resp.text
    assert recommendations_resp.json()["items"]


@pytest.mark.asyncio
async def test_vendor_delivery_and_customer_return_flow(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="admin_two",
        email="admin2@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="vendor_two",
        email="vendor2@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="customer_two",
        email="customer2@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "vendor-two-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Vendor Two",
            "display_name": "Vendor Two",
            "slug": "vendor-two",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    await _create_delivery_zone(client, admin_headers, code="lalitpur-zone")
    await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Books", "slug": "books", "level": 1},
    )
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Warehouse"})
    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Book House", "slug": "book-house"},
    )
    brand_id = brand_resp.json()["brand"]["id"]
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Hardcover Notebook",
            "slug": "hardcover-notebook",
            "variants": [{"sku": "NB-001", "name": "Default", "mrp": 25, "selling_price": 20, "quantity": 3, "is_default": True}],
        },
    )
    product_id = product_resp.json()["product"]["id"]
    approve_resp = await client.post(f"/api/v1/admin/catalog/products/{product_id}/approve", headers=admin_headers)
    variant_id = approve_resp.json()["product"]["variants"][0]["id"]

    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={
            "name": "Office",
            "phone": "+9779811111111",
            "line1": "Patan",
            "city": "Lalitpur",
            "state": "Bagmati",
            "pincode": "44700",
        },
    )
    await client.post("/api/v1/cart/items", headers=customer_headers, json={"variant_id": variant_id, "quantity": 1})
    checkout_resp = await client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    order = checkout_resp.json()["order"]
    vendor_orders_resp = await client.get("/api/v1/vendor/orders", headers=vendor_headers)
    vendor_order_id = vendor_orders_resp.json()["items"][0]["id"]

    shipped_resp = await client.post(
        f"/api/v1/vendor/orders/{vendor_order_id}/status",
        headers=vendor_headers,
        json={"status": "shipped", "location": "City hub", "remarks": "Dispatched"},
    )
    assert shipped_resp.status_code == 200, shipped_resp.text
    delivered_resp = await client.post(
        f"/api/v1/vendor/orders/{vendor_order_id}/status",
        headers=vendor_headers,
        json={"status": "delivered", "location": "Customer address", "remarks": "Delivered successfully"},
    )
    assert delivered_resp.status_code == 200, delivered_resp.text

    refreshed_order = await client.get(f"/api/v1/orders/{order['id']}", headers=customer_headers)
    assert refreshed_order.status_code == 200
    assert refreshed_order.json()["order"]["status"] == "delivered"
    order_item_id = refreshed_order.json()["order"]["items"][0]["id"]

    return_resp = await client.post(
        "/api/v1/returns",
        headers=customer_headers,
        json={
            "order_id": order["id"],
            "order_item_id": order_item_id,
            "reason": "Wrong item delivered",
            "details": "Color mismatch",
        },
    )
    assert return_resp.status_code == 201, return_resp.text

    result = await db_session.execute(select(ReturnRequest))
    assert result.scalars().first() is not None


@pytest.mark.asyncio
async def test_internal_logistics_and_support_flow(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="ops_admin",
        email="ops_admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="vendor_logistics",
        email="vendor_logistics@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="customer_logistics",
        email="customer_logistics@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "vendor-logistics-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Logistics Vendor",
            "display_name": "Logistics Vendor",
            "slug": "logistics-vendor",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    await _create_delivery_zone(client, admin_headers, code="ops-zone")
    hub_resp = await client.post(
        "/api/v1/logistics/hubs",
        headers=admin_headers,
        json={"name": "Central Hub", "code": "HUB-KTM", "city": "Kathmandu"},
    )
    hub_id = hub_resp.json()["hub_id"]
    zone_id = (await client.get("/api/v1/logistics/zones", headers=admin_headers)).json()["items"][0]["id"]
    branch_resp = await client.post(
        "/api/v1/logistics/branches",
        headers=admin_headers,
        json={"hub_id": hub_id, "zone_id": zone_id, "name": "Baneshwor Branch", "code": "BR-KTM"},
    )
    branch_id = branch_resp.json()["branch_id"]
    agent_resp = await client.post(
        "/api/v1/logistics/agents",
        headers=admin_headers,
        json={"branch_id": branch_id, "name": "Rider One", "phone": "+9779800000001"},
    )
    agent_id = agent_resp.json()["agent_id"]

    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Vendor Warehouse"})
    await client.post("/api/v1/admin/categories", headers=admin_headers, json={"name": "Clothes", "slug": "clothes", "level": 1})
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Fashion Co", "slug": "fashion-co"},
    )
    brand_id = brand_resp.json()["brand"]["id"]
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Jacket",
            "slug": "jacket",
            "variants": [{"sku": "JK-1", "name": "M", "mrp": 100, "selling_price": 80, "quantity": 2, "is_default": True}],
        },
    )
    product_id = product_resp.json()["product"]["id"]
    approve_resp = await client.post(f"/api/v1/admin/catalog/products/{product_id}/approve", headers=admin_headers)
    variant_id = approve_resp.json()["product"]["variants"][0]["id"]
    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={"name": "Home", "phone": "+9779800000002", "line1": "Koteshwor", "city": "Kathmandu", "state": "Bagmati", "pincode": "44600"},
    )
    await client.post("/api/v1/cart/items", headers=customer_headers, json={"variant_id": variant_id, "quantity": 1})
    quote_resp = await client.get(
        "/api/v1/checkout/quote",
        headers=customer_headers,
        params={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    assert quote_resp.status_code == 200, quote_resp.text
    order_resp = await client.post(
        "/api/v1/checkout",
        headers={**customer_headers, "Idempotency-Key": "order-1"},
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    same_order_resp = await client.post(
        "/api/v1/checkout",
        headers={**customer_headers, "Idempotency-Key": "order-1"},
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    assert order_resp.status_code == 201, order_resp.text
    assert same_order_resp.json()["order"]["id"] == order_resp.json()["order"]["id"]
    vendor_order_id = order_resp.json()["order"]["vendor_orders"][0]["id"]
    shipment_id = order_resp.json()["order"]["shipments"][0]["id"]

    pickup_job_resp = await client.post(
        f"/api/v1/vendor/orders/{vendor_order_id}/pickup-jobs",
        headers=vendor_headers,
        params={"branch_id": branch_id},
    )
    pickup_job_id = pickup_job_resp.json()["pickup_job_id"]
    assign_resp = await client.post(
        f"/api/v1/logistics/pickup-jobs/{pickup_job_id}/assign",
        headers=admin_headers,
        json={"agent_id": agent_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text
    complete_pickup_resp = await client.post(
        f"/api/v1/logistics/pickup-jobs/{pickup_job_id}/complete",
        headers=admin_headers,
        params={"location": "Baneshwor Branch"},
    )
    assert complete_pickup_resp.status_code == 200, complete_pickup_resp.text

    manifest_resp = await client.post(
        "/api/v1/logistics/manifests",
        headers=admin_headers,
        json={"code": "MNF-001", "origin_hub_id": hub_id, "destination_hub_id": hub_id, "branch_id": branch_id, "shipment_ids": [shipment_id]},
    )
    trip_resp = await client.post(
        "/api/v1/logistics/trips",
        headers=admin_headers,
        json={"manifest_id": manifest_resp.json()["manifest_id"], "vehicle_number": "BA-1-PA-1234"},
    )
    dispatch_resp = await client.post(f"/api/v1/logistics/trips/{trip_resp.json()['trip_id']}/dispatch", headers=admin_headers)
    arrive_resp = await client.post(f"/api/v1/logistics/trips/{trip_resp.json()['trip_id']}/arrive", headers=admin_headers)
    assert dispatch_resp.status_code == 200
    assert arrive_resp.status_code == 200

    ticket_resp = await client.post(
        "/api/v1/support/tickets",
        headers=customer_headers,
        json={"subject": "Need delivery update", "description": "Where is my parcel?", "order_id": order_resp.json()["order"]["id"]},
    )
    assert ticket_resp.status_code == 201, ticket_resp.text
    admin_tickets = await client.get("/api/v1/admin/support/tickets", headers=admin_headers)
    assert admin_tickets.status_code == 200
    assert admin_tickets.json()["total"] == 1


@pytest.mark.asyncio
async def test_strict_e2ee_chat_device_and_envelope_flow(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="chat_admin",
        email="chat_admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="chat_vendor",
        email="chat_vendor@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="chat_customer",
        email="chat_customer@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "chat-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Chat Vendor",
            "display_name": "Chat Vendor",
            "slug": "chat-vendor",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    await _create_delivery_zone(client, admin_headers, code="chat-zone")
    await client.post("/api/v1/admin/categories", headers=admin_headers, json={"name": "Tech", "slug": "tech", "level": 1})
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    brand_resp = await client.post("/api/v1/admin/catalog/brands", headers=admin_headers, json={"name": "Chat Brand", "slug": "chat-brand"})
    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Chat WH"})
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_resp.json()["brand"]["id"],
            "name": "Phone",
            "slug": "phone",
            "variants": [{"sku": "PH-1", "name": "Std", "mrp": 1000, "selling_price": 900, "quantity": 1, "is_default": True}],
        },
    )
    approve_resp = await client.post(f"/api/v1/admin/catalog/products/{product_resp.json()['product']['id']}/approve", headers=admin_headers)
    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={"name": "Chat Home", "phone": "+9779812345678", "line1": "Bhaktapur", "city": "Bhaktapur", "state": "Bagmati", "pincode": "44600"},
    )
    await client.post("/api/v1/cart/items", headers=customer_headers, json={"variant_id": approve_resp.json()["product"]["variants"][0]["id"], "quantity": 1})
    checkout_resp = await client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    order_id = checkout_resp.json()["order"]["id"]

    customer_device_resp = await client.post(
        "/api/v1/chat/devices",
        headers=customer_headers,
        json={
            "device_id": "cust-device-1",
            "device_label": "Customer phone",
            "identity_key_public": "cust-ident-pub",
            "signed_prekey_public": "cust-signed-pub",
            "signed_prekey_signature": "cust-signature",
        },
    )
    vendor_device_resp = await client.post(
        "/api/v1/chat/devices",
        headers=vendor_headers,
        json={
            "device_id": "vendor-device-1",
            "device_label": "Vendor phone",
            "identity_key_public": "vendor-ident-pub",
            "signed_prekey_public": "vendor-signed-pub",
            "signed_prekey_signature": "vendor-signature",
        },
    )
    assert customer_device_resp.status_code == 201
    assert vendor_device_resp.status_code == 201

    await client.post(
        "/api/v1/chat/prekeys/one-time?device_id=vendor-device-1",
        headers=vendor_headers,
        json={"keys": [{"key_id": 1001, "public_key": "vendor-onetime-pub"}]},
    )
    prekey_bundle = await client.get(f"/api/v1/chat/prekeys/{encode_id(vendor_user.id)}", headers=customer_headers)
    assert prekey_bundle.status_code == 200
    assert prekey_bundle.json()["one_time_prekey_public"] == "vendor-onetime-pub"

    conversation_resp = await client.post(
        "/api/v1/chat/conversations",
        headers=customer_headers,
        json={"order_id": order_id, "vendor_id": vendor_id},
    )
    conversation_id = conversation_resp.json()["conversation_id"]
    send_resp = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=customer_headers,
        json={
            "device_id": "cust-device-1",
            "ciphertext": "encrypted-message-payload",
            "header": {"ratchet_key": "rk1", "message_index": 1},
            "attachments": [],
        },
    )
    assert send_resp.status_code == 201, send_resp.text
    messages_resp = await client.get(f"/api/v1/chat/conversations/{conversation_id}/messages", headers=vendor_headers)
    assert messages_resp.status_code == 200, messages_resp.text
    assert messages_resp.json()["items"][0]["ciphertext"] == "encrypted-message-payload"
    attachment_manifest_resp = await client.post(
        "/api/v1/chat/attachments",
        headers=customer_headers,
        json={
            "message_id": send_resp.json()["message_id"],
            "attachments": [
                {
                    "blob_url": "https://example.com/cipher.bin",
                    "media_type": "application/octet-stream",
                    "size_bytes": 128,
                    "encrypted_file_key": "enc-key",
                    "nonce": "nonce-1",
                    "sha256": "hash-1",
                }
            ],
        },
    )
    assert attachment_manifest_resp.status_code == 201, attachment_manifest_resp.text
    attachments_resp = await client.get(
        f"/api/v1/chat/attachments/{send_resp.json()['message_id']}",
        headers=vendor_headers,
    )
    assert attachments_resp.status_code == 200, attachments_resp.text
    assert attachments_resp.json()["items"][0]["sha256"] == "hash-1"

    backup_resp = await client.put(
        "/api/v1/chat/backup",
        headers=customer_headers,
        json={"backup_blob": "encrypted-backup", "salt": "salt123", "metadata": {"version": 1}},
    )
    assert backup_resp.status_code == 200
    get_backup_resp = await client.get("/api/v1/chat/backup", headers=customer_headers)
    assert get_backup_resp.status_code == 200
    assert get_backup_resp.json()["backup_blob"] == "encrypted-backup"

    report_resp = await client.post(
        f"/api/v1/chat/reports?conversation_id={conversation_id}",
        headers=customer_headers,
        json={"reason": "spam", "metadata": {"message_id": send_resp.json()["message_id"]}},
    )
    assert report_resp.status_code == 201
    revoke_resp = await client.post("/api/v1/chat/devices/cust-device-1/revoke", headers=customer_headers)
    assert revoke_resp.status_code == 200

    result = await db_session.execute(select(ChatMessageEnvelope))
    envelope = result.scalars().first()
    assert envelope is not None
    assert envelope.ciphertext == "encrypted-message-payload"


@pytest.mark.asyncio
async def test_wallet_gift_card_and_payment_lifecycle_flow(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="finance_admin",
        email="finance_admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="wallet_vendor",
        email="wallet_vendor@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="wallet_customer",
        email="wallet_customer@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "wallet-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Wallet Vendor",
            "display_name": "Wallet Vendor",
            "slug": "wallet-vendor",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    await _create_delivery_zone(client, admin_headers, code="wallet-zone")
    await client.post("/api/v1/admin/categories", headers=admin_headers, json={"name": "Wallet Cat", "slug": "wallet-cat", "level": 1})
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    brand_resp = await client.post("/api/v1/admin/catalog/brands", headers=admin_headers, json={"name": "Wallet Brand", "slug": "wallet-brand"})
    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Wallet WH"})
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_resp.json()["brand"]["id"],
            "name": "Wallet Product",
            "slug": "wallet-product",
            "variants": [{"sku": "WP-1", "name": "Std", "mrp": 100, "selling_price": 80, "quantity": 2, "is_default": True}],
        },
    )
    approve_resp = await client.post(f"/api/v1/admin/catalog/products/{product_resp.json()['product']['id']}/approve", headers=admin_headers)
    variant_id = approve_resp.json()["product"]["variants"][0]["id"]
    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={"name": "Wallet Home", "phone": "+9779812340000", "line1": "KTM", "city": "Kathmandu", "state": "Bagmati", "pincode": "44600"},
    )

    gift_card_resp = await client.post(
        "/api/v1/payments/stored-value/gift-cards/",
        headers=admin_headers,
        params={"code": "NPR5000", "amount": 500000},
    )
    assert gift_card_resp.status_code == 200, gift_card_resp.text
    redeem_resp = await client.post(
        "/api/v1/payments/stored-value/gift-cards/redeem/",
        headers=customer_headers,
        params={"code": "NPR5000"},
    )
    assert redeem_resp.status_code == 200, redeem_resp.text
    assert redeem_resp.json()["wallet_balance"] == 500000

    await client.post("/api/v1/cart/items", headers=customer_headers, json={"variant_id": variant_id, "quantity": 1})
    wallet_checkout = await client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "wallet"},
    )
    assert wallet_checkout.status_code == 201, wallet_checkout.text
    assert wallet_checkout.json()["order"]["payment_status"] == "paid"
    assert wallet_checkout.json()["order"]["pricing_snapshot"]["total"] > 0

    wallet_state = await client.get("/api/v1/payments/stored-value/wallet/", headers=customer_headers)
    assert wallet_state.status_code == 200, wallet_state.text
    assert wallet_state.json()["balance"] < 500000

    order_row = (await db_session.execute(select(Order).order_by(Order.id.desc()))).scalars().first()
    assert order_row is not None and order_row.payment_transaction_id is not None
    tx_id = encode_id(order_row.payment_transaction_id)
    refund_resp = await client.post(
        f"/api/v1/payments/{tx_id}/refunds/",
        headers=customer_headers,
        json={"amount": 500, "destination": "wallet", "reason": "customer appeasement"},
    )
    assert refund_resp.status_code == 200, refund_resp.text
    wallet_after_refund = await client.get("/api/v1/payments/stored-value/wallet/", headers=customer_headers)
    assert wallet_after_refund.json()["balance"] == wallet_state.json()["balance"] + 500

    manual_tx = PaymentTransaction(
        provider=PaymentProvider.STRIPE,
        amount=1000,
        purchase_order_id="manual-1",
        purchase_order_name="Manual Transaction",
        return_url="https://example.com/return",
        website_url="https://example.com",
        status=PaymentStatus.INITIATED,
        provider_pidx="sess_manual_1",
        user_id=customer_user.id,
    )
    db_session.add(manual_tx)
    await db_session.commit()
    await db_session.refresh(manual_tx)

    capture_resp = await client.post(
        f"/api/v1/payments/{encode_id(manual_tx.id)}/capture/",
        headers=customer_headers,
        json={"amount": 1000},
    )
    assert capture_resp.status_code == 200, capture_resp.text
    webhook_resp = await client.post(
        "/api/v1/payments/webhooks/stripe",
        headers={"X-Webhook-Signature": settings.STRIPE_WEBHOOK_SECRET, "X-Webhook-Event": "payment.refund"} | customer_headers,
        json={"session_id": "sess_manual_1"},
    )
    assert webhook_resp.status_code == 200, webhook_resp.text


@pytest.mark.asyncio
async def test_catalog_admin_settings_and_pod_extensions(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="ext_admin",
        email="ext_admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="ext_vendor",
        email="ext_vendor@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="ext_customer",
        email="ext_customer@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "ext-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Extension Vendor",
            "display_name": "Extension Vendor",
            "slug": "extension-vendor",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    await _create_delivery_zone(client, admin_headers, code="ext-zone")
    zone_id = (await client.get("/api/v1/logistics/zones", headers=admin_headers)).json()["items"][0]["id"]
    shipping_option_resp = await client.post(
        "/api/v1/logistics/shipping-options",
        headers=admin_headers,
        json={"zone_id": zone_id, "name": "Express", "code": "EXPRESS", "rate": 25, "estimated_days": 1},
    )
    assert shipping_option_resp.status_code == 201, shipping_option_resp.text
    shipping_options = await client.get("/api/v1/logistics/shipping-options", headers=admin_headers)
    assert shipping_options.status_code == 200
    assert shipping_options.json()["items"][0]["code"] == "EXPRESS"

    category_resp = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Accessories", "slug": "accessories", "level": 1, "sort_order": 3},
    )
    category_id = category_resp.json()["category"]["id"]
    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Extensions", "slug": "extensions"},
    )
    brand_id = brand_resp.json()["brand"]["id"]
    update_category = await client.patch(
        f"/api/v1/admin/categories/{category_id}",
        headers=admin_headers,
        json={"name": "Accessories Updated", "slug": "accessories", "level": 1, "sort_order": 1, "attributes": []},
    )
    assert update_category.status_code == 200, update_category.text
    update_brand = await client.patch(
        f"/api/v1/admin/catalog/brands/{brand_id}",
        headers=admin_headers,
        json={"name": "Extensions Updated", "slug": "extensions", "description": "Updated", "logo_url": ""},
    )
    assert update_brand.status_code == 200, update_brand.text
    autocomplete_resp = await client.get("/api/v1/search/autocomplete", params={"q": "Acc"})
    assert autocomplete_resp.status_code == 200

    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Ext WH"})
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Accessory Pack",
            "slug": "accessory-pack",
            "variants": [{"sku": "AP-1", "name": "Std", "mrp": 120, "selling_price": 90, "quantity": 1, "is_default": True}],
        },
    )
    product_id = product_resp.json()["product"]["id"]
    await client.post(f"/api/v1/admin/catalog/products/{product_id}/approve", headers=admin_headers)
    patch_product = await client.patch(
        f"/api/v1/vendor/products/{product_id}",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Accessory Pack Plus",
            "slug": "accessory-pack",
            "variants": [{"sku": "AP-1", "name": "Std", "mrp": 120, "selling_price": 90, "quantity": 1, "is_default": True}],
        },
    )
    assert patch_product.status_code == 200, patch_product.text
    variant_id = patch_product.json()["product"]["variants"][0]["id"]
    inventory_update = await client.patch(
        f"/api/v1/vendor/inventory/{variant_id}",
        headers=vendor_headers,
        json={"quantity": 4, "reorder_level": 1, "reorder_qty": 10},
    )
    assert inventory_update.status_code == 200, inventory_update.text

    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={"name": "POD Home", "phone": "+9779801234567", "line1": "POD", "city": "Kathmandu", "state": "Bagmati", "pincode": "44600"},
    )
    await client.post("/api/v1/cart/items", headers=customer_headers, json={"variant_id": variant_id, "quantity": 1})
    order_resp = await client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    shipment_id = order_resp.json()["order"]["shipments"][0]["id"]
    pod_resp = await client.post(
        f"/api/v1/logistics/shipments/{shipment_id}/pod",
        headers=admin_headers,
        json={"proof_type": "otp", "otp_code": "123456", "photo_url": "https://example.com/pod.jpg", "signature_url": "https://example.com/sign.png", "notes": "Delivered to customer"},
    )
    assert pod_resp.status_code == 201, pod_resp.text
    pod_list_resp = await client.get(f"/api/v1/logistics/shipments/{shipment_id}/pod", headers=admin_headers)
    assert pod_list_resp.status_code == 200, pod_list_resp.text
    assert pod_list_resp.json()["items"][0]["otp_code"] == "123456"

    admin_customers = await client.get("/api/v1/admin/customers", headers=admin_headers)
    assert admin_customers.status_code == 200, admin_customers.text
    assert admin_customers.json()["total"] >= 1
    admin_settings = await client.get("/api/v1/system/admin/settings/", headers=admin_headers)
    assert admin_settings.status_code == 200, admin_settings.text
    updatable_setting = next(item for item in admin_settings.json() if item["is_runtime_editable"])
    patch_setting = await client.patch(
        f"/api/v1/system/admin/settings/{updatable_setting['key']}",
        headers=admin_headers,
        json={"db_value": "patched-value", "use_db_value": True},
    )
    assert patch_setting.status_code == 200, patch_setting.text
