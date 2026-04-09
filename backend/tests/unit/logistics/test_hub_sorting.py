from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlmodel import select

from src.apps.commerce.models import Address
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import encode_id
from src.apps.logistics.api.v1.routes import (
    HubBulkMoveNextLegRequest,
    HubSortAssignRequest,
    HubSortQueueCreateRequest,
    HubSortScanRequest,
    assign_hub_sort_item,
    bulk_move_to_next_leg,
    close_hub_queue,
    create_hub_queue,
    scan_hub_sort_item,
)
from src.apps.logistics.models import Hub, HubOperationEvent, HubSortQueueItem, ShipmentManifest
from src.apps.orders.models import Order, OrderPaymentStatus, OrderStatus, PaymentMethod, Shipment


async def _seed_user(session) -> User:
    user = User(
        username="ops-admin",
        email="ops-admin@example.com",
        is_superuser=True,
        is_active=True,
        hashed_password="x",
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_shipment(session) -> Shipment:
    user = User(username="buyer-1", email="buyer1@example.com", is_active=True, hashed_password="x")
    session.add(user)
    await session.flush()
    address = Address(user_id=user.id or 0, name="Buyer", line1="Street 1", city="City", pincode="44600")
    session.add(address)
    await session.flush()
    order = Order(
        order_number="ORD-HUB-1",
        user_id=user.id or 0,
        address_id=address.id or 0,
        status=OrderStatus.CONFIRMED,
        payment_method=PaymentMethod.COD,
        payment_status=OrderPaymentStatus.PENDING,
    )
    session.add(order)
    await session.flush()
    shipment = Shipment(order_id=order.id or 0, awb="AWB-HUB-1")
    session.add(shipment)
    await session.flush()
    return shipment


@pytest.mark.asyncio
async def test_duplicate_scan_is_rejected_with_exception_tracking(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub A", code="HUB-A")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)

    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-A"),
        admin,
        db_session,
    )

    await scan_hub_sort_item(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    with pytest.raises(HTTPException, match="Duplicate scan"):
        await scan_hub_sort_item(
            encode_id(hub.id or 0),
            queue_response["queue_id"],
            HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
            admin,
            db_session,
        )
    duplicate_event = (
        await db_session.execute(select(HubOperationEvent).where(HubOperationEvent.operation_type == "duplicate_scan_detected"))
    ).scalars().one()
    assert duplicate_event.shipment_id == shipment.id


@pytest.mark.asyncio
async def test_wrong_hub_scan_marks_item_as_exception(db_session):
    admin = await _seed_user(db_session)
    wrong_hub = Hub(name="Hub Wrong", code="HUB-W")
    expected_hub = Hub(name="Hub Expected", code="HUB-E")
    db_session.add(wrong_hub)
    db_session.add(expected_hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    manifest = ShipmentManifest(code="MNF-1", destination_hub_id=expected_hub.id, shipment_ids_json=f"[{shipment.id}]")
    db_session.add(manifest)
    await db_session.flush()

    queue_response = await create_hub_queue(
        encode_id(wrong_hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-W"),
        admin,
        db_session,
    )
    result = await scan_hub_sort_item(
        encode_id(wrong_hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    assert result["status"] == "exception"
    assert result["exception_code"] == "wrong_hub_scan"


@pytest.mark.asyncio
async def test_manifest_closed_blocks_sort_actions(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Close", code="HUB-C")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-C"),
        admin,
        db_session,
    )
    await close_hub_queue(encode_id(hub.id or 0), queue_response["queue_id"], admin, db_session)
    with pytest.raises(HTTPException, match="Manifest closed during sort action"):
        await scan_hub_sort_item(
            encode_id(hub.id or 0),
            queue_response["queue_id"],
            HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
            admin,
            db_session,
        )


@pytest.mark.asyncio
async def test_bulk_move_requires_readiness_and_marks_items_moved(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Move", code="HUB-M")
    next_hub = Hub(name="Hub Next", code="HUB-N")
    db_session.add(hub)
    db_session.add(next_hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-M"),
        admin,
        db_session,
    )
    await scan_hub_sort_item(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    await assign_hub_sort_item(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortAssignRequest(
            shipment_id=encode_id(shipment.id or 0),
            next_hub_id=encode_id(next_hub.id or 0),
            carrier="CarrierX",
            vehicle_number="VEH-42",
        ),
        admin,
        db_session,
    )
    with pytest.raises(HTTPException, match="readiness validation failed"):
        await bulk_move_to_next_leg(
            encode_id(hub.id or 0),
            queue_response["queue_id"],
            HubBulkMoveNextLegRequest(
                shipment_ids=[encode_id(shipment.id or 0)],
                carrier="CarrierX",
                vehicle_number="VEH-42",
                carrier_ready=False,
                vehicle_ready=True,
            ),
            admin,
            db_session,
        )
    result = await bulk_move_to_next_leg(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubBulkMoveNextLegRequest(
            shipment_ids=[encode_id(shipment.id or 0)],
            carrier="CarrierX",
            vehicle_number="VEH-42",
            carrier_ready=True,
            vehicle_ready=True,
        ),
        admin,
        db_session,
    )
    assert result["moved_count"] == 1
    item = (await db_session.execute(select(HubSortQueueItem))).scalars().one()
    assert item.status.value == "moved_to_next_leg"
