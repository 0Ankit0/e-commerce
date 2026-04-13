from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlmodel import select

from src.apps.commerce.models import Address
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import encode_id
from src.apps.logistics.api.v1.routes import (
    DispatchConfirmRequest,
    HubExceptionUpdateRequest,
    HubBulkAssignRequest,
    HubBulkScanRequest,
    HubBulkMoveNextLegRequest,
    HubSortAssignRequest,
    HubSortQueueCreateRequest,
    HubSortScanRequest,
    assign_hub_sort_item,
    confirm_hub_dispatch,
    bulk_assign_hub_sort_items,
    bulk_move_to_next_leg,
    bulk_scan_hub_sort_items,
    close_hub_queue,
    create_hub_queue,
    get_hub_operational_reports,
    get_hub_sort_workbench,
    intake_hub_shipment,
    outbound_stage_hub_shipment,
    scan_hub_sort_item,
    update_hub_exception_queue,
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
    address = Address(
        user_id=user.id or 0,
        name="Buyer",
        phone="9800000000",
        line1="Street 1",
        city="City",
        state="Bagmati",
        pincode="44600",
    )
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
    with pytest.raises(HTTPException, match="Manifest closed during sort action"):
        await bulk_scan_hub_sort_items(
            encode_id(hub.id or 0),
            queue_response["queue_id"],
            HubBulkScanRequest(shipment_ids=[encode_id(shipment.id or 0)]),
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
    rerun = await bulk_move_to_next_leg(
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
    assert rerun["moved_count"] == 0
    assert rerun["already_moved_count"] == 1


@pytest.mark.asyncio
async def test_bulk_scan_and_assign_are_idempotent(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Bulk", code="HUB-B")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-B"),
        admin,
        db_session,
    )
    scan_result = await bulk_scan_hub_sort_items(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubBulkScanRequest(shipment_ids=[encode_id(shipment.id or 0), encode_id(shipment.id or 0)]),
        admin,
        db_session,
    )
    assert scan_result["requested_count"] == 2
    assert scan_result["scanned_count"] == 1
    assert scan_result["duplicate_count"] == 1

    assign_result = await bulk_assign_hub_sort_items(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubBulkAssignRequest(
            shipment_ids=[encode_id(shipment.id or 0)],
            carrier="CarrierB",
            vehicle_number="VEH-B",
        ),
        admin,
        db_session,
    )
    assert assign_result["assigned_count"] == 1
    assign_again = await bulk_assign_hub_sort_items(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubBulkAssignRequest(
            shipment_ids=[encode_id(shipment.id or 0)],
            carrier="CarrierB",
            vehicle_number="VEH-B",
        ),
        admin,
        db_session,
    )
    assert assign_again["assigned_count"] == 0
    assert assign_again["idempotent_skip_count"] == 1


@pytest.mark.asyncio
async def test_dispatch_confirmation_rejects_invalid_operation_order(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Dispatch", code="HUB-D")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-D"),
        admin,
        db_session,
    )
    await intake_hub_shipment(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    with pytest.raises(HTTPException, match="Dispatch confirmation requires outbound staging completion"):
        await confirm_hub_dispatch(
            encode_id(hub.id or 0),
            queue_response["queue_id"],
            DispatchConfirmRequest(shipment_id=encode_id(shipment.id or 0)),
            admin,
            db_session,
        )


@pytest.mark.asyncio
async def test_hub_leg_transition_audit_timestamps_are_recorded(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Audit", code="HUB-AUD")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-AUD"),
        admin,
        db_session,
    )
    await intake_hub_shipment(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    await assign_hub_sort_item(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortAssignRequest(shipment_id=encode_id(shipment.id or 0), carrier="Carrier-A", vehicle_number="VEH-A"),
        admin,
        db_session,
    )
    await outbound_stage_hub_shipment(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortAssignRequest(shipment_id=encode_id(shipment.id or 0), carrier="Carrier-A", vehicle_number="VEH-A"),
        admin,
        db_session,
    )
    await confirm_hub_dispatch(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        DispatchConfirmRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    item = (await db_session.execute(select(HubSortQueueItem))).scalars().one()
    assert item.scanned_at is not None
    assert item.assigned_at is not None
    assert item.moved_at is not None
    operation_types = (await db_session.execute(select(HubOperationEvent.operation_type))).scalars().all()
    assert "hub_intake_recorded" in operation_types
    assert "sort_bucket_assigned" in operation_types
    assert "outbound_staged" in operation_types
    assert "dispatch_confirmed" in operation_types


@pytest.mark.asyncio
async def test_exception_queue_can_requeue_for_mis_sort_correction(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Hold", code="HUB-HOLD")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-HOLD"),
        admin,
        db_session,
    )
    await intake_hub_shipment(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    on_hold = await update_hub_exception_queue(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubExceptionUpdateRequest(
            shipment_id=encode_id(shipment.id or 0),
            exception_code="mis_sort",
            notes="Wrong lane",
            requeue_for_sorting=False,
        ),
        admin,
        db_session,
    )
    assert on_hold["status"] == "exception"
    requeued = await update_hub_exception_queue(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubExceptionUpdateRequest(
            shipment_id=encode_id(shipment.id or 0),
            exception_code="mis_sort_corrected",
            notes="Moved to correct lane",
            requeue_for_sorting=True,
        ),
        admin,
        db_session,
    )
    assert requeued["status"] == "scanned"


@pytest.mark.asyncio
async def test_sort_workbench_and_reports_include_sla_and_queue_boards(db_session):
    admin = await _seed_user(db_session)
    hub = Hub(name="Hub Bench", code="HUB-BEN")
    db_session.add(hub)
    await db_session.flush()
    shipment = await _seed_shipment(db_session)
    queue_response = await create_hub_queue(
        encode_id(hub.id or 0),
        HubSortQueueCreateRequest(code="QUEUE-BEN"),
        admin,
        db_session,
    )
    await intake_hub_shipment(
        encode_id(hub.id or 0),
        queue_response["queue_id"],
        HubSortScanRequest(shipment_id=encode_id(shipment.id or 0)),
        admin,
        db_session,
    )
    bench = await get_hub_sort_workbench(encode_id(hub.id or 0), queue_response["queue_id"], 20, admin, db_session)
    assert "hold_exception_items" in bench
    assert "sorting_lanes" in bench
    assert "sla_timers" in bench
    report = await get_hub_operational_reports(encode_id(hub.id or 0), admin, db_session)
    assert "throughput_by_shift" in report
    assert "sla_breach_heatmap" in report
