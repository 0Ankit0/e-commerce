from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.config import settings
from src.apps.core.security import TokenType, create_access_token, get_password_hash, verify_token
from src.apps.notification.models.notification import Notification
from src.apps.finance.models.payment import PaymentProvider, PaymentStatus, PaymentTransaction
from src.apps.commerce.models import Address, WishlistShareLink
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.logistics.models import CourierLocationPing, DeliveryException, RouteOptimizationPlan, ShipmentManifest, ShipmentManifestStatus
from src.apps.messaging.models import ChatMessageEnvelope
from src.apps.multitenancy.models.tenant import Tenant, TenantMember, TenantRole
from src.apps.orders.models import Order, OrderStatus, ReturnRequest, Shipment, ShipmentTracking
from src.apps.vendors.models import VendorDocument, VendorTimelineEvent


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




async def _advance_vendor_to_resubmission(client: AsyncClient, admin_headers: dict[str, str], vendor_id: str) -> None:
    under_review_resp = await client.post(f"/api/v1/admin/vendors/{vendor_id}/mark-under-review", headers=admin_headers)
    assert under_review_resp.status_code == 200, under_review_resp.text
    resubmission_resp = await client.post(
        f"/api/v1/admin/vendors/{vendor_id}/request-resubmission",
        headers=admin_headers,
        json={"reason": "Verification details requested"},
    )
    assert resubmission_resp.status_code == 200, resubmission_resp.text


async def _approve_vendor_for_tests(client: AsyncClient, admin_headers: dict[str, str], vendor_id: str):
    await _advance_vendor_to_resubmission(client, admin_headers, vendor_id)
    approve_vendor_resp = await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    assert approve_vendor_resp.status_code == 200, approve_vendor_resp.text
    return approve_vendor_resp

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

    approve_vendor = await _approve_vendor_for_tests(client, admin_headers, vendor_id)
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
    recommendations_payload = recommendations_resp.json()
    assert recommendations_payload["strategy"] == "ml_ranker_v2"
    assert recommendations_payload["items"]
    assert "ranking_features" in recommendations_payload["items"][0]


@pytest.mark.asyncio
async def test_route_optimization_and_courier_gps_ingestion(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="route_admin",
        email="route-admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="route_vendor",
        email="route-vendor@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="route_customer",
        email="route-customer@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "route-vendor-tenant")

    vendor_create = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": tenant.id and __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id(tenant.id),
            "business_name": "Route Vendor Pvt Ltd",
            "display_name": "Route Vendor",
            "slug": "route-vendor-store",
            "description": "Optimized delivery seller",
        },
    )
    assert vendor_create.status_code == 201, vendor_create.text
    vendor_id = vendor_create.json()["vendor"]["id"]

    approve_vendor = await _approve_vendor_for_tests(client, admin_headers, vendor_id)
    await _create_delivery_zone(client, admin_headers, code="route-zone")

    category_resp = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Wearables", "slug": "wearables", "level": 1, "attributes": []},
    )
    assert category_resp.status_code == 201, category_resp.text
    category_id = category_resp.json()["category"]["id"]

    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Trail Tech", "slug": "trail-tech"},
    )
    assert brand_resp.status_code == 201, brand_resp.text
    brand_id = brand_resp.json()["brand"]["id"]

    warehouse_resp = await client.post(
        "/api/v1/vendor/warehouses",
        headers=vendor_headers,
        json={"name": "Route Warehouse", "city": "Kathmandu", "is_default": True},
    )
    assert warehouse_resp.status_code == 201, warehouse_resp.text

    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "GPS Messenger",
            "slug": "gps-messenger",
            "short_description": "Field-ready courier tracker",
            "description": "Compact device for route-tracked delivery workflows",
            "status": "pending",
            "variants": [
                {
                    "sku": "GPS-001",
                    "name": "Standard",
                    "mrp": 90,
                    "selling_price": 75,
                    "quantity": 10,
                    "is_default": True,
                }
            ],
            "images": [{"url": "https://example.com/gps.jpg", "is_primary": True}],
        },
    )
    assert product_resp.status_code == 201, product_resp.text
    product_id = product_resp.json()["product"]["id"]

    approve_product = await client.post(
        f"/api/v1/admin/catalog/products/{product_id}/approve",
        headers=admin_headers,
    )
    assert approve_product.status_code == 200, approve_product.text
    variant_id = approve_product.json()["product"]["variants"][0]["id"]

    address_1_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={
            "name": "First stop",
            "phone": "+9779800000001",
            "line1": "Kalanki",
            "city": "Kathmandu",
            "state": "Bagmati",
            "pincode": "44600",
            "is_default": True,
        },
    )
    assert address_1_resp.status_code == 201, address_1_resp.text
    address_1_id = address_1_resp.json()["address"]["id"]

    address_2_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={
            "name": "Second stop",
            "phone": "+9779800000002",
            "line1": "Bhaktapur",
            "city": "Bhaktapur",
            "state": "Bagmati",
            "pincode": "44700",
            "is_default": False,
        },
    )
    assert address_2_resp.status_code == 201, address_2_resp.text
    address_2_id = address_2_resp.json()["address"]["id"]

    decode_id = __import__("src.apps.iam.utils.hashid", fromlist=["decode_id_or_404"]).decode_id_or_404
    first_address = await db_session.get(Address, decode_id(address_1_id))
    second_address = await db_session.get(Address, decode_id(address_2_id))
    assert first_address is not None and second_address is not None
    first_address.latitude = 27.6935
    first_address.longitude = 85.2812
    second_address.latitude = 27.6710
    second_address.longitude = 85.4298
    await db_session.commit()

    shipment_ids: list[str] = []
    for address_id in [address_1_id, address_2_id]:
        add_cart = await client.post(
            "/api/v1/cart/items",
            headers=customer_headers,
            json={"variant_id": variant_id, "quantity": 1},
        )
        assert add_cart.status_code == 201, add_cart.text

        checkout_resp = await client.post(
            "/api/v1/checkout",
            headers=customer_headers,
            json={"address_id": address_id, "payment_method": "cod"},
        )
        assert checkout_resp.status_code == 201, checkout_resp.text
        shipment_ids.append(checkout_resp.json()["order"]["shipments"][0]["id"])

    manifest_resp = await client.post(
        "/api/v1/logistics/manifests",
        headers=admin_headers,
        json={"code": "MNF-ROUTE-001", "shipment_ids": shipment_ids},
    )
    assert manifest_resp.status_code == 201, manifest_resp.text
    manifest_id = manifest_resp.json()["manifest_id"]

    trip_resp = await client.post(
        "/api/v1/logistics/trips",
        headers=admin_headers,
        json={
            "manifest_id": manifest_id,
            "vehicle_number": "BA-1-PA-1000",
            "driver_name": "Route Driver",
            "driver_phone": "9800001234",
        },
    )
    assert trip_resp.status_code == 201, trip_resp.text
    trip_id = trip_resp.json()["trip_id"]

    optimize_resp = await client.post(
        f"/api/v1/logistics/trips/{trip_id}/optimize-route",
        headers=admin_headers,
        json={"average_speed_kph": 24, "service_minutes_per_stop": 6},
    )
    assert optimize_resp.status_code == 200, optimize_resp.text
    plan = optimize_resp.json()
    assert plan["strategy"] == "nearest_neighbor_2opt_v1"
    assert plan["routed_stop_count"] == 2
    assert plan["unroutable_stop_count"] == 0
    assert plan["total_distance_km"] > 0
    assert {stop["shipment_id"] for stop in plan["stops"]} == set(shipment_ids)

    stored_plan = (
        await db_session.execute(select(RouteOptimizationPlan).where(RouteOptimizationPlan.trip_id == decode_id(trip_id)))
    ).scalars().first()
    assert stored_plan is not None

    gps_resp = await client.post(
        f"/api/v1/logistics/trips/{trip_id}/gps",
        headers=admin_headers,
        json={
            "shipment_id": shipment_ids[0],
            "latitude": 27.7019,
            "longitude": 85.3206,
            "speed_kph": 32.5,
            "heading": 45,
            "accuracy_meters": 6,
            "source": "device",
            "label": "Ring Road corridor",
        },
    )
    assert gps_resp.status_code == 201, gps_resp.text

    gps_list_resp = await client.get(f"/api/v1/logistics/trips/{trip_id}/gps", headers=admin_headers)
    assert gps_list_resp.status_code == 200, gps_list_resp.text
    gps_items = gps_list_resp.json()["items"]
    assert gps_items
    assert gps_items[0]["label"] == "Ring Road corridor"
    assert gps_items[0]["shipment_id"] == shipment_ids[0]

    stored_ping = (
        await db_session.execute(select(CourierLocationPing).where(CourierLocationPing.trip_id == decode_id(trip_id)))
    ).scalars().first()
    assert stored_ping is not None
    first_shipment = await db_session.get(Shipment, decode_id(shipment_ids[0]))
    assert first_shipment is not None
    assert first_shipment.current_location == "Ring Road corridor"


@pytest.mark.asyncio
async def test_line_haul_planner_draft_save_and_apply_flow(client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await _create_user_headers(
        db_session,
        username="planner_admin",
        email="planner-admin@example.com",
        is_superuser=True,
    )

    planner_payload = {
        "routes": [
            {"route_id": "KTM-PKR", "origin_hub": "KTM", "destination_hub": "PKR", "demand_units": 45},
            {"route_id": "KTM-BWA", "origin_hub": "KTM", "destination_hub": "BWA", "demand_units": 12},
        ],
        "vehicles": [
            {"vehicle_id": "VAN-1", "hub_code": "KTM", "capacity_units": 30},
            {"vehicle_id": "VAN-2", "hub_code": "KTM", "capacity_units": 20},
        ],
        "connectivity": {"KTM": ["PKR", "BWA"], "PKR": ["KTM"], "BWA": ["KTM"]},
        "locked_assignments": [],
        "random_seed": 17,
    }

    run_resp = await client.post("/api/v1/logistics/line-haul-planner/run", headers=admin_headers, json=planner_payload)
    assert run_resp.status_code == 200, run_resp.text
    run_data = run_resp.json()
    assert run_data["validation"]["is_valid"] is True

    conflicting_assignments = run_data["assignments"] + [
        {"route_id": "KTM-PKR", "vehicle_id": "VAN-1", "assigned_units": 25},
        {"route_id": "KTM-PKR", "vehicle_id": "VAN-1", "assigned_units": 10},
    ]
    validate_resp = await client.post(
        "/api/v1/logistics/line-haul-planner/assignments/validate",
        headers=admin_headers,
        json={
            "name": "conflicting-draft",
            "status": "draft",
            "routes": planner_payload["routes"],
            "vehicles": planner_payload["vehicles"],
            "connectivity": planner_payload["connectivity"],
            "locked_assignments": planner_payload["locked_assignments"],
            "assignments": conflicting_assignments,
            "optimizer_metadata": run_data["metadata"],
        },
    )
    assert validate_resp.status_code == 200, validate_resp.text
    assert validate_resp.json()["is_valid"] is False
    error_codes = {err["code"] for err in validate_resp.json()["errors"]}
    assert "LOG_PLANNER_OVER_CAPACITY" in error_codes
    assert "LOG_PLANNER_DUPLICATE_ASSIGNMENT" in error_codes

    save_resp = await client.post(
        "/api/v1/logistics/line-haul-planner/drafts",
        headers=admin_headers,
        json={
            "name": "Conflicting planner draft",
            "status": "draft",
            "routes": planner_payload["routes"],
            "vehicles": planner_payload["vehicles"],
            "connectivity": planner_payload["connectivity"],
            "locked_assignments": planner_payload["locked_assignments"],
            "assignments": conflicting_assignments,
            "optimizer_metadata": run_data["metadata"],
        },
    )
    assert save_resp.status_code == 201, save_resp.text
    draft_id = save_resp.json()["draft_id"]
    assert save_resp.json()["validation"]["is_valid"] is False

    apply_conflicting_resp = await client.post(
        f"/api/v1/logistics/line-haul-planner/drafts/{draft_id}/apply?expected_version={save_resp.json()['version']}",
        headers=admin_headers,
    )
    assert apply_conflicting_resp.status_code == 409, apply_conflicting_resp.text

    valid_save_resp = await client.post(
        "/api/v1/logistics/line-haul-planner/drafts",
        headers=admin_headers,
        json={
            "name": "Valid planner draft",
            "status": "draft",
            "routes": planner_payload["routes"],
            "vehicles": planner_payload["vehicles"],
            "connectivity": planner_payload["connectivity"],
            "locked_assignments": planner_payload["locked_assignments"],
            "assignments": run_data["assignments"],
            "optimizer_metadata": run_data["metadata"],
        },
    )
    assert valid_save_resp.status_code == 201, valid_save_resp.text
    valid_draft_id = valid_save_resp.json()["draft_id"]

    apply_valid_resp = await client.post(
        f"/api/v1/logistics/line-haul-planner/drafts/{valid_draft_id}/apply?expected_version={valid_save_resp.json()['version']}",
        headers=admin_headers,
    )
    assert apply_valid_resp.status_code == 200, apply_valid_resp.text
    assert apply_valid_resp.json()["status"] == "published"

    list_drafts_resp = await client.get("/api/v1/logistics/line-haul-planner/drafts", headers=admin_headers)
    assert list_drafts_resp.status_code == 200, list_drafts_resp.text
    assert len(list_drafts_resp.json()["items"]) >= 2


@pytest.mark.asyncio
async def test_line_haul_planner_draft_lifecycle_with_versioning_and_manifest_generation(client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await _create_user_headers(
        db_session,
        username="planner_lifecycle_admin",
        email="planner-lifecycle-admin@example.com",
        is_superuser=True,
    )

    create_resp = await client.post(
        "/api/v1/logistics/line-haul-planner/drafts",
        headers=admin_headers,
        json={
            "name": "Lifecycle draft",
            "status": "draft",
            "routes": [{"route_id": "KTM-PKR", "origin_hub": "KTM", "destination_hub": "PKR", "demand_units": 10}],
            "vehicles": [{"vehicle_id": "TRUCK-1", "hub_code": "KTM", "capacity_units": 20}],
            "connectivity": {"KTM": ["PKR"], "PKR": ["KTM"]},
            "locked_assignments": [],
            "assignments": [],
            "optimizer_metadata": {},
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    draft = create_resp.json()

    conflict_resp = await client.post(
        f"/api/v1/logistics/line-haul-planner/drafts/{draft['draft_id']}/apply?expected_version=999",
        headers=admin_headers,
    )
    assert conflict_resp.status_code == 409, conflict_resp.text

    optimize_resp = await client.post(
        f"/api/v1/logistics/line-haul-planner/drafts/{draft['draft_id']}/optimize?expected_version={draft['version']}&random_seed=7",
        headers=admin_headers,
    )
    assert optimize_resp.status_code == 200, optimize_resp.text
    optimized = optimize_resp.json()
    assert optimized["validation"]["is_valid"] is True

    publish_resp = await client.post(
        f"/api/v1/logistics/line-haul-planner/drafts/{draft['draft_id']}/apply?expected_version={optimized['version']}",
        headers=admin_headers,
    )
    assert publish_resp.status_code == 200, publish_resp.text
    published = publish_resp.json()
    assert published["status"] == "published"
    assert len(published["generated_manifest_ids"]) == 1

    manifest_db = await db_session.get(ShipmentManifest, decode_id_or_404(published["generated_manifest_ids"][0]))
    assert manifest_db is not None


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
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
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
    return_request_id = return_resp.json()["return_request_id"]

    admin_approve_return = await client.post(
        f"/api/v1/admin/returns/{return_request_id}/status",
        headers=admin_headers,
        json={"status": "approved", "note": "Return approved"},
    )
    assert admin_approve_return.status_code == 200, admin_approve_return.text

    return_timeline_resp = await client.get(
        f"/api/v1/returns/{return_request_id}/timeline",
        headers=customer_headers,
    )
    assert return_timeline_resp.status_code == 200, return_timeline_resp.text
    assert len(return_timeline_resp.json()["items"]) >= 2

    result = await db_session.execute(select(ReturnRequest))
    assert result.scalars().first() is not None


@pytest.mark.asyncio
async def test_wishlist_sharing_and_price_drop_notifications(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="wishlist_admin",
        email="wishlist_admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="wishlist_vendor",
        email="wishlist_vendor@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="wishlist_customer",
        email="wishlist_customer@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "wishlist-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Wishlist Vendor",
            "display_name": "Wishlist Vendor",
            "slug": "wishlist-vendor",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
    await _create_delivery_zone(client, admin_headers, code="wishlist-zone")
    await client.post("/api/v1/admin/categories", headers=admin_headers, json={"name": "Accessories", "slug": "accessories", "level": 1})
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Wishlist Brand", "slug": "wishlist-brand"},
    )
    brand_id = brand_resp.json()["brand"]["id"]
    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Wishlist WH"})
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Leather Wallet",
            "slug": "leather-wallet",
            "short_description": "Classic wallet",
            "description": "Handmade leather wallet",
            "variants": [{"sku": "WL-001", "name": "Brown", "mrp": 80, "selling_price": 65, "quantity": 10, "is_default": True}],
            "images": [{"url": "https://example.com/wallet.jpg", "is_primary": True}],
        },
    )
    product_id = product_resp.json()["product"]["id"]
    await client.post(f"/api/v1/admin/catalog/products/{product_id}/approve", headers=admin_headers)

    wishlist_add_resp = await client.post(f"/api/v1/wishlist/{product_id}", headers=customer_headers)
    assert wishlist_add_resp.status_code == 201, wishlist_add_resp.text
    share_resp = await client.post("/api/v1/wishlist/share-links", headers=customer_headers, json={"title": "Birthday ideas"})
    assert share_resp.status_code == 201, share_resp.text
    share_id = share_resp.json()["share_link"]["id"]
    token = share_resp.json()["share_link"]["token"]

    list_share_resp = await client.get("/api/v1/wishlist/share-links", headers=customer_headers)
    assert list_share_resp.status_code == 200, list_share_resp.text
    assert list_share_resp.json()["total"] == 1

    public_resp = await client.get(f"/api/v1/wishlist/shared/{token}")
    assert public_resp.status_code == 200, public_resp.text
    assert public_resp.json()["items"][0]["name"] == "Leather Wallet"

    update_resp = await client.patch(
        f"/api/v1/vendor/products/{product_id}",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Leather Wallet",
            "slug": "leather-wallet",
            "short_description": "Classic wallet",
            "description": "Handmade leather wallet",
            "status": "active",
            "variants": [{"sku": "WL-001", "name": "Brown", "mrp": 80, "selling_price": 55, "quantity": 10, "is_default": True}],
            "images": [{"url": "https://example.com/wallet.jpg", "is_primary": True}],
        },
    )
    assert update_resp.status_code == 200, update_resp.text

    notifications = (
        await db_session.execute(select(Notification).where(Notification.user_id == customer_user.id).order_by(Notification.id.desc()))
    ).scalars().all()
    assert any(notification.title == "Price drop on your wishlist" for notification in notifications)

    revoke_resp = await client.delete(f"/api/v1/wishlist/share-links/{share_id}", headers=customer_headers)
    assert revoke_resp.status_code == 200, revoke_resp.text
    expired_public_resp = await client.get(f"/api/v1/wishlist/shared/{token}")
    assert expired_public_resp.status_code == 404
    share_links = (await db_session.execute(select(WishlistShareLink))).scalars().all()
    assert share_links[0].is_active is False


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
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
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
    order_id = order_resp.json()["order"]["id"]

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
    vendor_label_resp = await client.post(f"/api/v1/vendor/shipments/{shipment_id}/label", headers=vendor_headers)
    assert vendor_label_resp.status_code == 200, vendor_label_resp.text
    vendor_label_again_resp = await client.get(f"/api/v1/vendor/shipments/{shipment_id}/label", headers=vendor_headers)
    assert vendor_label_again_resp.status_code == 200, vendor_label_again_resp.text
    assert vendor_label_again_resp.json()["label_url"] == vendor_label_resp.json()["label_url"]

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
    ticket_id = ticket_resp.json()["ticket_id"]
    admin_ticket_comment = await client.post(
        f"/api/v1/admin/support/tickets/{ticket_id}/comments",
        headers=admin_headers,
        json={"body": "We are checking with the branch", "is_internal": False},
    )
    assert admin_ticket_comment.status_code == 201, admin_ticket_comment.text
    admin_ticket_status = await client.post(
        f"/api/v1/admin/support/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={"status": "in_progress", "assignee_user_id": encode_id(admin.id)},
    )
    assert admin_ticket_status.status_code == 200, admin_ticket_status.text
    customer_ticket_detail = await client.get(f"/api/v1/support/tickets/{ticket_id}", headers=customer_headers)
    assert customer_ticket_detail.status_code == 200, customer_ticket_detail.text
    assert customer_ticket_detail.json()["comments"][0]["body"] == "We are checking with the branch"

    exception_resp = await client.post(
        f"/api/v1/logistics/shipments/{shipment_id}/exceptions",
        headers=admin_headers,
        json={
            "exception_type": "failed_delivery",
            "failure_reason": "Customer unavailable",
            "notes": "Will retry tomorrow",
            "agent_id": agent_id,
        },
    )
    assert exception_resp.status_code == 201, exception_resp.text
    exception_id = exception_resp.json()["exception_id"]
    reschedule_resp = await client.post(
        f"/api/v1/logistics/exceptions/{exception_id}/reschedule",
        headers=admin_headers,
        json={"rescheduled_for": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
    )
    assert reschedule_resp.status_code == 200, reschedule_resp.text
    rto_resp = await client.post(
        f"/api/v1/logistics/exceptions/{exception_id}/rto",
        headers=admin_headers,
    )
    assert rto_resp.status_code == 200, rto_resp.text
    live_feed_resp = await client.get("/api/v1/admin/orders/live-feed", headers=admin_headers)
    assert live_feed_resp.status_code == 200, live_feed_resp.text
    assert any(item["payload"].get("order_id") == order_id for item in live_feed_resp.json()["items"])
    agent_availability_resp = await client.get("/api/v1/logistics/agents/availability", headers=admin_headers)
    assert agent_availability_resp.status_code == 200, agent_availability_resp.text
    branch_performance_resp = await client.get(
        f"/api/v1/logistics/branches/{branch_id}/performance",
        headers=admin_headers,
    )
    assert branch_performance_resp.status_code == 200, branch_performance_resp.text
    hub_performance_resp = await client.get(
        f"/api/v1/logistics/hubs/{hub_id}/performance",
        headers=admin_headers,
    )
    assert hub_performance_resp.status_code == 200, hub_performance_resp.text
    admin_tickets = await client.get("/api/v1/admin/support/tickets", headers=admin_headers)
    assert admin_tickets.status_code == 200
    assert admin_tickets.json()["total"] == 1


@pytest.mark.asyncio
async def test_shipment_transition_rules_and_idempotency(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="ops_admin_transition",
        email="ops_admin_transition@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="vendor_transition",
        email="vendor_transition@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="customer_transition",
        email="customer_transition@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "vendor-transition-tenant")
    hashid = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id", "decode_id"])
    encode_id = hashid.encode_id
    decode_id = hashid.decode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Transition Vendor",
            "display_name": "Transition Vendor",
            "slug": "transition-vendor",
        },
    )
    vendor_id = vendor_resp.json()["vendor"]["id"]
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
    await _create_delivery_zone(client, admin_headers, code="transition-zone")
    hub_resp = await client.post(
        "/api/v1/logistics/hubs",
        headers=admin_headers,
        json={"name": "Transition Hub", "code": "HUB-TRN", "city": "Kathmandu"},
    )
    hub_id = hub_resp.json()["hub_id"]
    zone_id = (await client.get("/api/v1/logistics/zones", headers=admin_headers)).json()["items"][0]["id"]
    first_branch_resp = await client.post(
        "/api/v1/logistics/branches",
        headers=admin_headers,
        json={"hub_id": hub_id, "zone_id": zone_id, "name": "Branch One", "code": "BR-TRN-1"},
    )
    second_branch_resp = await client.post(
        "/api/v1/logistics/branches",
        headers=admin_headers,
        json={"hub_id": hub_id, "zone_id": zone_id, "name": "Branch Two", "code": "BR-TRN-2"},
    )
    first_branch_id = first_branch_resp.json()["branch_id"]
    second_branch_id = second_branch_resp.json()["branch_id"]
    agent_resp = await client.post(
        "/api/v1/logistics/agents",
        headers=admin_headers,
        json={"branch_id": first_branch_id, "name": "Rider Two", "phone": "+9779800009999"},
    )
    agent_id = agent_resp.json()["agent_id"]

    await client.post("/api/v1/vendor/warehouses", headers=vendor_headers, json={"name": "Transition Warehouse"})
    await client.post("/api/v1/admin/categories", headers=admin_headers, json={"name": "Shoes", "slug": "shoes", "level": 1})
    category_id = (await client.get("/api/v1/categories")).json()["items"][0]["id"]
    brand_resp = await client.post(
        "/api/v1/admin/catalog/brands",
        headers=admin_headers,
        json={"name": "Transition Brand", "slug": "transition-brand"},
    )
    brand_id = brand_resp.json()["brand"]["id"]
    product_resp = await client.post(
        "/api/v1/vendor/products",
        headers=vendor_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "name": "Sneaker",
            "slug": "sneaker-transition",
            "variants": [{"sku": "SN-1", "name": "42", "mrp": 120, "selling_price": 100, "quantity": 2, "is_default": True}],
        },
    )
    product_id = product_resp.json()["product"]["id"]
    approve_resp = await client.post(f"/api/v1/admin/catalog/products/{product_id}/approve", headers=admin_headers)
    variant_id = approve_resp.json()["product"]["variants"][0]["id"]
    address_resp = await client.post(
        "/api/v1/addresses",
        headers=customer_headers,
        json={"name": "Home", "phone": "+9779801000000", "line1": "Koteshwor", "city": "Kathmandu", "state": "Bagmati", "pincode": "44600"},
    )
    await client.post("/api/v1/cart/items", headers=customer_headers, json={"variant_id": variant_id, "quantity": 1})
    order_resp = await client.post(
        "/api/v1/checkout",
        headers={**customer_headers, "Idempotency-Key": "transition-order-1"},
        json={"address_id": address_resp.json()["address"]["id"], "payment_method": "cod"},
    )
    assert order_resp.status_code == 201, order_resp.text
    vendor_order_id = order_resp.json()["order"]["vendor_orders"][0]["id"]
    shipment_id = order_resp.json()["order"]["shipments"][0]["id"]
    shipment_db_id = decode_id(shipment_id)

    illegal_transition_resp = await client.post(
        f"/api/v1/logistics/shipments/{shipment_id}/status",
        headers=admin_headers,
        json={"status": "out_for_delivery", "location": "Bad jump", "remarks": "skip graph"},
    )
    assert illegal_transition_resp.status_code == 409, illegal_transition_resp.text
    shipment = await db_session.get(Shipment, shipment_db_id)
    assert shipment is not None
    assert shipment.status == OrderStatus.CONFIRMED

    pickup_job_resp = await client.post(
        f"/api/v1/vendor/orders/{vendor_order_id}/pickup-jobs",
        headers=vendor_headers,
        params={"branch_id": first_branch_id},
    )
    pickup_job_id = pickup_job_resp.json()["pickup_job_id"]
    await client.post(
        f"/api/v1/logistics/pickup-jobs/{pickup_job_id}/assign",
        headers=admin_headers,
        json={"agent_id": agent_id},
    )
    await client.post(
        f"/api/v1/logistics/pickup-jobs/{pickup_job_id}/complete",
        headers=admin_headers,
        params={"location": "Branch One"},
    )
    shipped_count_before = len(
        (
            await db_session.execute(
                select(ShipmentTracking).where(ShipmentTracking.shipment_id == shipment_db_id, ShipmentTracking.status == OrderStatus.SHIPPED)
            )
        ).scalars().all()
    )
    shipped_repeat_resp = await client.post(
        f"/api/v1/logistics/shipments/{shipment_id}/status",
        headers=admin_headers,
        json={"status": "shipped", "location": "Branch One", "remarks": "idempotent repeat"},
    )
    assert shipped_repeat_resp.status_code == 200, shipped_repeat_resp.text
    shipped_count_after = len(
        (
            await db_session.execute(
                select(ShipmentTracking).where(ShipmentTracking.shipment_id == shipment_db_id, ShipmentTracking.status == OrderStatus.SHIPPED)
            )
        ).scalars().all()
    )
    assert shipped_count_after == shipped_count_before

    manifest_resp = await client.post(
        "/api/v1/logistics/manifests",
        headers=admin_headers,
        json={"code": "MNF-TRN-001", "origin_hub_id": hub_id, "destination_hub_id": hub_id, "branch_id": first_branch_id, "shipment_ids": [shipment_id]},
    )
    manifest_db_id = decode_id(manifest_resp.json()["manifest_id"])
    trip_resp = await client.post(
        "/api/v1/logistics/trips",
        headers=admin_headers,
        json={"manifest_id": manifest_resp.json()["manifest_id"], "vehicle_number": "BA-1-PA-9999"},
    )
    await client.post(f"/api/v1/logistics/trips/{trip_resp.json()['trip_id']}/dispatch", headers=admin_headers)

    manifest = await db_session.get(ShipmentManifest, manifest_db_id)
    assert manifest is not None
    manifest.branch_id = decode_id(second_branch_id)
    db_session.add(manifest)
    await db_session.commit()

    arrive_resp = await client.post(f"/api/v1/logistics/trips/{trip_resp.json()['trip_id']}/arrive", headers=admin_headers)
    assert arrive_resp.status_code == 200, arrive_resp.text
    latest_out_for_delivery = (
        (
            await db_session.execute(
                select(ShipmentTracking)
                .where(ShipmentTracking.shipment_id == shipment_db_id, ShipmentTracking.status == OrderStatus.OUT_FOR_DELIVERY)
                .order_by(ShipmentTracking.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert latest_out_for_delivery is not None
    assert latest_out_for_delivery.location == "Branch Two"

    exception_resp = await client.post(
        f"/api/v1/logistics/shipments/{shipment_id}/exceptions",
        headers=admin_headers,
        json={"exception_type": "failed_delivery", "failure_reason": "Customer unavailable", "agent_id": agent_id},
    )
    assert exception_resp.status_code == 201, exception_resp.text
    exception_id = exception_resp.json()["exception_id"]
    rto_resp = await client.post(f"/api/v1/logistics/exceptions/{exception_id}/rto", headers=admin_headers)
    assert rto_resp.status_code == 200, rto_resp.text

    repeated_rto_resp = await client.post(f"/api/v1/logistics/exceptions/{exception_id}/rto", headers=admin_headers)
    assert repeated_rto_resp.status_code == 200, repeated_rto_resp.text
    returned_events = (
        (
            await db_session.execute(
                select(ShipmentTracking).where(ShipmentTracking.shipment_id == shipment_db_id, ShipmentTracking.status == OrderStatus.RETURNED)
            )
        )
        .scalars()
        .all()
    )
    assert len(returned_events) == 1

    reschedule_after_rto_resp = await client.post(
        f"/api/v1/logistics/exceptions/{exception_id}/reschedule",
        headers=admin_headers,
        json={"rescheduled_for": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()},
    )
    assert reschedule_after_rto_resp.status_code == 409, reschedule_after_rto_resp.text
    exception_db = await db_session.get(DeliveryException, decode_id(exception_id))
    assert exception_db is not None
    assert exception_db.status.value == "rto_initiated"


@pytest.mark.asyncio
async def test_vendor_payout_content_and_reporting_flow(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(
        db_session,
        username="ops_admin_two",
        email="ops_admin_two@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="vendor_finance",
        email="vendor_finance@example.com",
    )
    customer_user, customer_headers = await _create_user_headers(
        db_session,
        username="content_customer",
        email="content_customer@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "vendor-finance-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Finance Vendor",
            "display_name": "Finance Vendor",
            "slug": "finance-vendor",
        },
    )
    assert vendor_resp.status_code == 201, vendor_resp.text
    vendor_id = vendor_resp.json()["vendor"]["id"]
    under_review_resp = await client.post(f"/api/v1/admin/vendors/{vendor_id}/mark-under-review", headers=admin_headers)
    assert under_review_resp.status_code == 200, under_review_resp.text
    resubmission_resp = await client.post(
        f"/api/v1/admin/vendors/{vendor_id}/request-resubmission",
        headers=admin_headers,
        json={"reason": "Upload KYC files"},
    )
    assert resubmission_resp.status_code == 200, resubmission_resp.text

    document_resp = await client.post(
        "/api/v1/vendor/documents",
        headers=vendor_headers,
        json={"doc_type": "pan", "doc_number": "PAN123", "file_url": "https://example.com/pan.pdf"},
    )
    assert document_resp.status_code == 201, document_resp.text
    bank_resp = await client.post(
        "/api/v1/vendor/bank-accounts",
        headers=vendor_headers,
        json={"account_name": "Finance Vendor", "account_number": "1234567890", "ifsc_code": "NMBL0001", "bank_name": "NMB"},
    )
    assert bank_resp.status_code == 201, bank_resp.text
    document_db = await db_session.get(VendorDocument, decode_id_or_404(document_resp.json()["document_id"]))
    assert document_db is not None
    mark_doc_review_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_resp.json()['document_id']}/mark-under-review",
        headers=admin_headers,
        json={"remarks": "triaged", "expected_uploaded_at": document_db.uploaded_at.isoformat(), "expected_version": document_db.version},
    )
    assert mark_doc_review_resp.status_code == 200, mark_doc_review_resp.text
    verify_doc_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_resp.json()['document_id']}/verify",
        headers=admin_headers,
        json={"remarks": "Looks good", "expected_uploaded_at": document_db.uploaded_at.isoformat(), "expected_version": document_db.version},
    )
    assert verify_doc_resp.status_code == 200, verify_doc_resp.text
    verify_bank_resp = await client.post(
        f"/api/v1/admin/vendor-bank-accounts/{bank_resp.json()['bank_account_id']}/verify",
        headers=admin_headers,
    )
    assert verify_bank_resp.status_code == 200, verify_bank_resp.text
    approve_vendor_resp = await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    assert approve_vendor_resp.status_code == 200, approve_vendor_resp.text

    payout_request_resp = await client.post(
        "/api/v1/vendor/payout-requests",
        headers=vendor_headers,
        json={"amount": 1250, "notes": "Weekly settlement"},
    )
    assert payout_request_resp.status_code == 201, payout_request_resp.text
    payout_request_id = payout_request_resp.json()["payout_request"]["id"]
    approve_payout_request_resp = await client.post(
        f"/api/v1/admin/vendor-payout-requests/{payout_request_id}/approve",
        headers=admin_headers,
    )
    assert approve_payout_request_resp.status_code == 200, approve_payout_request_resp.text
    payout_batch_resp = await client.post(
        "/api/v1/admin/vendor-payouts/batches",
        headers=admin_headers,
        json={"payout_request_ids": [payout_request_id], "notes": "Friday batch"},
    )
    assert payout_batch_resp.status_code == 201, payout_batch_resp.text
    live_feed_resp = await client.get("/api/v1/admin/orders/live-feed", headers=admin_headers)
    assert live_feed_resp.status_code == 200, live_feed_resp.text
    assert any(item["event_type"] == "vendor.payout_requested" for item in live_feed_resp.json()["items"])
    settlement_export_resp = await client.get(
        f"/api/v1/admin/vendors/{vendor_id}/settlement-export",
        headers=admin_headers,
    )
    assert settlement_export_resp.status_code == 200, settlement_export_resp.text
    assert "reference,amount,commission_amount,status" in settlement_export_resp.text

    banner_resp = await client.post(
        "/api/v1/admin/content/banners",
        headers=admin_headers,
        json={"title": "Dashain Sale", "subtitle": "Up to 40% off", "placement": "home", "image_url": "https://example.com/banner.jpg"},
    )
    assert banner_resp.status_code == 201, banner_resp.text
    page_resp = await client.post(
        "/api/v1/admin/content/pages",
        headers=admin_headers,
        json={"slug": "about-us", "title": "About Us", "body_markdown": "Trusted marketplace", "status": "published"},
    )
    assert page_resp.status_code == 201, page_resp.text
    list_banners_resp = await client.get("/api/v1/content/banners", headers=customer_headers)
    assert list_banners_resp.status_code == 200, list_banners_resp.text
    assert list_banners_resp.json()["total"] == 1
    static_page_resp = await client.get("/api/v1/content/pages/about-us", headers=customer_headers)
    assert static_page_resp.status_code == 200, static_page_resp.text
    assert static_page_resp.json()["page"]["title"] == "About Us"

    report_job_resp = await client.post(
        "/api/v1/admin/reports/jobs",
        headers=admin_headers,
        json={"report_type": "orders", "output_format": "csv"},
    )
    assert report_job_resp.status_code == 201, report_job_resp.text
    report_jobs_resp = await client.get("/api/v1/admin/reports/jobs", headers=admin_headers)
    assert report_jobs_resp.status_code == 200, report_jobs_resp.text
    report_export_resp = await client.get("/api/v1/admin/reports/export?report_type=orders", headers=admin_headers)
    assert report_export_resp.status_code == 200, report_export_resp.text
    assert "order_id,order_number,status,payment_status,total,created_at" in report_export_resp.text


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
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
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
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
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
    await _approve_vendor_for_tests(client, admin_headers, vendor_id)
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


@pytest.mark.asyncio
async def test_vendor_onboarding_transitions_and_audit_consistency(client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await _create_user_headers(
        db_session,
        username="workflow_admin",
        email="workflow_admin@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="workflow_vendor",
        email="workflow_vendor@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "workflow-vendor-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Workflow Vendor",
            "display_name": "Workflow Vendor",
            "slug": "workflow-vendor",
        },
    )
    assert vendor_resp.status_code == 201, vendor_resp.text
    vendor_id = vendor_resp.json()["vendor"]["id"]

    invalid_approve_resp = await client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers)
    assert invalid_approve_resp.status_code == 409, invalid_approve_resp.text

    under_review_resp = await client.post(f"/api/v1/admin/vendors/{vendor_id}/mark-under-review", headers=admin_headers)
    assert under_review_resp.status_code == 200, under_review_resp.text

    invalid_reject_without_reason = await client.post(
        f"/api/v1/admin/vendors/{vendor_id}/request-resubmission",
        headers=admin_headers,
        json={"reason": ""},
    )
    assert invalid_reject_without_reason.status_code == 422, invalid_reject_without_reason.text

    resubmission_resp = await client.post(
        f"/api/v1/admin/vendors/{vendor_id}/request-resubmission",
        headers=admin_headers,
        json={"reason": "Please re-submit PAN with clear image"},
    )
    assert resubmission_resp.status_code == 200, resubmission_resp.text

    upload_1_resp = await client.post(
        "/api/v1/vendor/documents",
        headers=vendor_headers,
        json={"doc_type": "pan", "doc_number": "PAN111", "file_url": "https://example.com/pan-v1.pdf"},
    )
    assert upload_1_resp.status_code == 201, upload_1_resp.text
    document_id = upload_1_resp.json()["document_id"]
    doc_v1 = await db_session.get(VendorDocument, decode_id_or_404(document_id))
    assert doc_v1 is not None
    stale_uploaded_at = doc_v1.uploaded_at.isoformat()
    stale_document_id = document_id

    upload_2_resp = await client.post(
        "/api/v1/vendor/documents",
        headers=vendor_headers,
        json={"doc_type": "pan", "doc_number": "PAN222", "file_url": "https://example.com/pan-v2.pdf"},
    )
    assert upload_2_resp.status_code == 201, upload_2_resp.text
    assert upload_2_resp.json()["document_id"] == document_id

    doc_v2 = await db_session.get(VendorDocument, decode_id_or_404(document_id))
    assert doc_v2 is not None
    assert doc_v2.doc_number == "PAN222"
    assert doc_v2.version == 2
    assert doc_v2.uploaded_at.isoformat() != stale_uploaded_at
    assert doc_v2.status.value == "submitted"

    duplicate_upload_resp = await client.post(
        "/api/v1/vendor/documents",
        headers=vendor_headers,
        json={"doc_type": "pan", "doc_number": "PAN222", "file_url": "https://example.com/pan-v2.pdf"},
    )
    assert duplicate_upload_resp.status_code == 409, duplicate_upload_resp.text

    mark_review_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/mark-under-review",
        headers=admin_headers,
        json={"remarks": "starting review", "expected_uploaded_at": doc_v2.uploaded_at.isoformat(), "expected_version": doc_v2.version},
    )
    assert mark_review_resp.status_code == 200, mark_review_resp.text

    missing_notes_resubmission = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/request-resubmission",
        headers=admin_headers,
        json={"remarks": "", "expected_uploaded_at": doc_v2.uploaded_at.isoformat(), "expected_version": doc_v2.version},
    )
    assert missing_notes_resubmission.status_code == 422, missing_notes_resubmission.text

    request_doc_resubmission = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/request-resubmission",
        headers=admin_headers,
        json={"remarks": "Image is blurry, upload a clearer PAN scan", "expected_uploaded_at": doc_v2.uploaded_at.isoformat(), "expected_version": doc_v2.version},
    )
    assert request_doc_resubmission.status_code == 200, request_doc_resubmission.text

    vendor_resubmit_resp = await client.post(
        f"/api/v1/vendor/documents/{document_id}/resubmit",
        headers=vendor_headers,
        json={"doc_type": "pan", "doc_number": "PAN333", "file_url": "https://example.com/pan-v3.pdf"},
    )
    assert vendor_resubmit_resp.status_code == 200, vendor_resubmit_resp.text
    document_id = vendor_resubmit_resp.json()["document_id"]
    doc_v3 = await db_session.get(VendorDocument, decode_id_or_404(document_id))
    assert doc_v3 is not None
    assert doc_v3.version == 3

    stale_verify_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/verify",
        headers=admin_headers,
        json={"remarks": "approved", "expected_uploaded_at": stale_uploaded_at, "expected_version": doc_v3.version},
    )
    assert stale_verify_resp.status_code == 409, stale_verify_resp.text

    mark_review_v3_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/mark-under-review",
        headers=admin_headers,
        json={"remarks": "starting review", "expected_uploaded_at": doc_v3.uploaded_at.isoformat(), "expected_version": doc_v3.version},
    )
    assert mark_review_v3_resp.status_code == 200, mark_review_v3_resp.text

    verify_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/verify",
        headers=admin_headers,
        json={"remarks": "approved", "expected_uploaded_at": doc_v3.uploaded_at.isoformat(), "expected_version": doc_v3.version},
    )
    assert verify_resp.status_code == 200, verify_resp.text
    profile_resp = await client.get("/api/v1/vendor/profile", headers=vendor_headers)
    assert profile_resp.status_code == 200, profile_resp.text
    pan_docs = [doc for doc in profile_resp.json()["documents"] if doc["doc_type"] == "pan"]
    assert len(pan_docs) >= 2
    assert pan_docs[0]["version"] >= pan_docs[1]["version"]
    assert pan_docs[0]["remarks"] == "approved"
    assert pan_docs[0]["is_current"] is True
    assert [entry["status"] for entry in pan_docs[0]["review_reason_history"]] == [
        "submitted",
        "under_review",
        "needs_resubmission",
        "submitted",
        "under_review",
        "verified",
    ]
    kyc_history_resp = await client.get("/api/v1/vendor/kyc/history", headers=vendor_headers)
    assert kyc_history_resp.status_code == 200, kyc_history_resp.text
    assert "checks" in kyc_history_resp.json()
    assert "kyc_status" in kyc_history_resp.json()

    stale_non_current_approval = await client.post(
        f"/api/v1/admin/vendor-documents/{stale_document_id}/verify",
        headers=admin_headers,
        json={"remarks": "stale", "expected_uploaded_at": stale_uploaded_at, "expected_version": 1},
    )
    assert stale_non_current_approval.status_code == 409, stale_non_current_approval.text

    admin_timeline_resp = await client.get(f"/api/v1/admin/vendors/{vendor_id}/timeline", headers=admin_headers)
    assert admin_timeline_resp.status_code == 200, admin_timeline_resp.text
    admin_resubmission_entries = [
        item for item in admin_timeline_resp.json()["items"] if item["event_type"] == "vendor.document_resubmission_requested"
    ]
    assert admin_resubmission_entries
    assert "remarks" in admin_resubmission_entries[0]["payload"]
    admin_kyc_history = await client.get(f"/api/v1/admin/vendors/{vendor_id}/kyc/history", headers=admin_headers)
    assert admin_kyc_history.status_code == 200, admin_kyc_history.text
    assert admin_kyc_history.json()["vendor_id"] == vendor_id

    unauthorized_doc_action = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/request-resubmission",
        headers=vendor_headers,
        json={"remarks": "not allowed", "expected_uploaded_at": doc_v3.uploaded_at.isoformat(), "expected_version": doc_v3.version},
    )
    assert unauthorized_doc_action.status_code == 403, unauthorized_doc_action.text

    concurrent_approve, concurrent_reject = await asyncio.gather(
        client.post(f"/api/v1/admin/vendors/{vendor_id}/approve", headers=admin_headers),
        client.post(
            f"/api/v1/admin/vendors/{vendor_id}/reject",
            headers=admin_headers,
            json={"reason": "Concurrent reject should fail"},
        ),
    )
    assert sorted([concurrent_approve.status_code, concurrent_reject.status_code]) == [200, 409]

    timeline_events = (
        await db_session.execute(
            select(VendorTimelineEvent.event_type)
            .where(VendorTimelineEvent.vendor_id == decode_id_or_404(vendor_id))
            .order_by(VendorTimelineEvent.created_at.asc(), VendorTimelineEvent.id.asc())
        )
    ).scalars().all()
    assert "vendor.under_review" in timeline_events
    assert "vendor.resubmission_requested" in timeline_events
    assert "vendor.document_reuploaded" in timeline_events
    assert "vendor.approved" in timeline_events or "vendor.rejected" in timeline_events


@pytest.mark.asyncio
async def test_vendor_document_concurrent_admin_review_actions(client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await _create_user_headers(
        db_session,
        username="workflow_admin_concurrent",
        email="workflow_admin_concurrent@example.com",
        is_superuser=True,
    )
    vendor_user, vendor_headers = await _create_user_headers(
        db_session,
        username="workflow_vendor_concurrent",
        email="workflow_vendor_concurrent@example.com",
    )
    tenant = await _create_tenant_for_owner(db_session, vendor_user, "workflow-vendor-concurrent-tenant")
    encode_id = __import__("src.apps.iam.utils.hashid", fromlist=["encode_id"]).encode_id

    vendor_resp = await client.post(
        "/api/v1/vendor/profile",
        headers=vendor_headers,
        json={
            "tenant_id": encode_id(tenant.id),
            "business_name": "Concurrent Vendor",
            "display_name": "Concurrent Vendor",
            "slug": "concurrent-vendor",
        },
    )
    assert vendor_resp.status_code == 201, vendor_resp.text

    upload_resp = await client.post(
        "/api/v1/vendor/documents",
        headers=vendor_headers,
        json={"doc_type": "pan", "doc_number": "PANC111", "file_url": "https://example.com/panc-v1.pdf"},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    document_id = upload_resp.json()["document_id"]
    document = await db_session.get(VendorDocument, decode_id_or_404(document_id))
    assert document is not None

    review_resp = await client.post(
        f"/api/v1/admin/vendor-documents/{document_id}/mark-under-review",
        headers=admin_headers,
        json={"remarks": "triage", "expected_uploaded_at": document.uploaded_at.isoformat(), "expected_version": document.version},
    )
    assert review_resp.status_code == 200, review_resp.text

    concurrent_verify, concurrent_resubmit = await asyncio.gather(
        client.post(
            f"/api/v1/admin/vendor-documents/{document_id}/verify",
            headers=admin_headers,
            json={"remarks": "looks good", "expected_uploaded_at": document.uploaded_at.isoformat(), "expected_version": document.version},
        ),
        client.post(
            f"/api/v1/admin/vendor-documents/{document_id}/request-resubmission",
            headers=admin_headers,
            json={"remarks": "image corners cropped", "expected_uploaded_at": document.uploaded_at.isoformat(), "expected_version": document.version},
        ),
    )

    assert sorted([concurrent_verify.status_code, concurrent_resubmit.status_code]) == [200, 409]

    updated_document = await db_session.get(VendorDocument, decode_id_or_404(document_id))
    assert updated_document is not None
    assert updated_document.status.value in {"verified", "needs_resubmission"}


@pytest.mark.asyncio
async def test_line_haul_planning_full_lifecycle_with_conflict_resolution(client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await _create_user_headers(
        db_session,
        username="planning_admin",
        email="planning-admin@example.com",
        is_superuser=True,
    )

    create_resp = await client.post(
        "/api/v1/logistics/planning/plans",
        headers=admin_headers,
        json={
            "name": "April Line Haul",
            "routes": [
                {
                    "route_id": "KTM-PKR",
                    "origin_hub": "KTM",
                    "destination_hub": "PKR",
                    "demand_units": 18,
                    "demand_weight_kg": 1800,
                    "demand_volume_m3": 15,
                },
                {
                    "route_id": "KTM-BWA",
                    "origin_hub": "KTM",
                    "destination_hub": "BWA",
                    "demand_units": 8,
                    "demand_weight_kg": 500,
                    "demand_volume_m3": 4,
                },
            ],
            "vehicles": [
                {
                    "vehicle_id": "TRK-1",
                    "hub_code": "KTM",
                    "capacity_units": 15,
                    "capacity_weight_kg": 1500,
                    "capacity_volume_m3": 10,
                    "available_count": 1,
                }
            ],
            "connectivity": {"KTM": ["PKR", "BWA"], "PKR": ["KTM"], "BWA": ["KTM"]},
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    plan = create_resp.json()
    plan_id = plan["plan_id"]

    optimize_resp = await client.post(
        f"/api/v1/logistics/planning/plans/{plan_id}/optimize",
        headers=admin_headers,
        json={"expected_version": plan["version"], "random_seed": 9, "manual_overrides": [], "locked_assignments": []},
    )
    assert optimize_resp.status_code == 200, optimize_resp.text
    optimized = optimize_resp.json()
    assert optimized["conflicts"]
    assert any(item["state"] == "unscheduled" for item in optimized["ui_states"])

    resolve_resp = await client.put(
        f"/api/v1/logistics/planning/plans/{plan_id}",
        headers=admin_headers,
        json={
            "name": "April Line Haul",
            "expected_version": optimized["version"],
            "routes": optimized["routes"],
            "vehicles": optimized["vehicles"]
            + [
                {
                    "vehicle_id": "TRK-2",
                    "hub_code": "KTM",
                    "capacity_units": 15,
                    "capacity_weight_kg": 2000,
                    "capacity_volume_m3": 12,
                    "available_count": 1,
                }
            ],
            "connectivity": optimized["connectivity"],
            "assignments": [],
        },
    )
    assert resolve_resp.status_code == 200, resolve_resp.text

    reoptimize_resp = await client.post(
        f"/api/v1/logistics/planning/plans/{plan_id}/optimize",
        headers=admin_headers,
        json={"expected_version": resolve_resp.json()["version"], "random_seed": 9, "manual_overrides": [], "locked_assignments": []},
    )
    assert reoptimize_resp.status_code == 200, reoptimize_resp.text
    reoptimized = reoptimize_resp.json()
    assert reoptimized["conflicts"] == []
    assert all(item["state"] == "ready-to-publish" for item in reoptimized["ui_states"])

    publish_resp = await client.post(
        f"/api/v1/logistics/planning/plans/{plan_id}/publish",
        headers=admin_headers,
        json={"expected_version": reoptimized["version"]},
    )
    assert publish_resp.status_code == 200, publish_resp.text
    published = publish_resp.json()
    assert published["status"] == "published"

    board_resp = await client.get(f"/api/v1/logistics/planning/plans/{plan_id}/board", headers=admin_headers)
    assert board_resp.status_code == 200, board_resp.text
    board = board_resp.json()
    assert len(board["route_network"]["list"]) == 2
    assert len(board["shipment_pool_by_destination_hub"]) == 2
    assert len(board["vehicle_fleet_capacity_board"]) == 2

    manifest_resp = await client.post(
        f"/api/v1/logistics/planning/plans/{plan_id}/dispatch/manifest",
        headers=admin_headers,
        json={"expected_version": published["version"], "code": "PLAN-MANIFEST-1", "shipment_ids": []},
    )
    assert manifest_resp.status_code == 201, manifest_resp.text
    with_manifest = manifest_resp.json()["plan"]

    assign_resp = await client.post(
        f"/api/v1/logistics/planning/plans/{plan_id}/dispatch/assign",
        headers=admin_headers,
        json={
            "expected_version": with_manifest["version"],
            "vehicle_number": "BA-2-PA-1122",
            "driver_name": "Test Driver",
            "driver_phone": "+9779800000000",
        },
    )
    assert assign_resp.status_code == 200, assign_resp.text
    with_trip = assign_resp.json()["plan"]

    execution_resp = await client.post(
        f"/api/v1/logistics/planning/plans/{plan_id}/dispatch/publish",
        headers=admin_headers,
        json={"expected_version": with_trip["version"]},
    )
    assert execution_resp.status_code == 200, execution_resp.text
    assert execution_resp.json()["manifest_status"] == "dispatched"

    manifest_db = await db_session.get(ShipmentManifest, decode_id_or_404(execution_resp.json()["manifest_id"]))
    assert manifest_db is not None
    assert manifest_db.status == ShipmentManifestStatus.DISPATCHED
