from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time, timezone
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.commerce.models import Address
from src.apps.analytics import get_analytics
from src.apps.core.time import utc_now
from src.apps.iam.utils.hashid import encode_id
from src.apps.logistics.models import (
    Branch,
    BranchInventoryMovement,
    BranchInventory,
    CourierLocationPing,
    DeliveryAgent,
    DeliveryAgentStatus,
    DeliveryException,
    DeliveryExceptionStatus,
    DeliveryZone,
    Hub,
    HubOperationEvent,
    HubSortQueue,
    HubSortQueueItem,
    HubSortItemStatus,
    HubSortQueueStatus,
    LineHaulTrip,
    LineHaulTripStatus,
    PickupJob,
    PickupJobStatus,
    ReversePickupJob,
    ReversePickupStatus,
    RouteOptimizationPlan,
    ShipmentProof,
    ShipmentManifest,
    ShipmentManifestStatus,
    ShippingOption,
)
from src.apps.logistics.planner import LockedAssignment, PlannerInput, RouteDefinition, VehicleCapacity, run_line_haul_optimizer
from src.apps.orders.models import Order, OrderStatus, ReturnRequest, Shipment, ShipmentTracking, VendorOrder, VendorOrderStatus
from src.apps.iam.models.user import User

ALLOWED_SHIPMENT_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.RETURNED},
}

PLANNER_ERROR_UNKNOWN_ROUTE = "LOG_PLANNER_UNKNOWN_ROUTE"
PLANNER_ERROR_UNKNOWN_VEHICLE = "LOG_PLANNER_UNKNOWN_VEHICLE"
PLANNER_ERROR_DUPLICATE_ASSIGNMENT = "LOG_PLANNER_DUPLICATE_ASSIGNMENT"
PLANNER_ERROR_OVER_CAPACITY = "LOG_PLANNER_OVER_CAPACITY"
PLANNER_ERROR_ROUTE_INCOMPATIBLE = "LOG_PLANNER_ROUTE_INCOMPATIBLE"
PLANNER_ERROR_ROUTE_UNSCHEDULED = "LOG_PLANNER_ROUTE_UNSCHEDULED"

ALLOWED_HUB_ITEM_TRANSITIONS: dict[HubSortItemStatus, set[HubSortItemStatus]] = {
    HubSortItemStatus.SCANNED: {HubSortItemStatus.ASSIGNED, HubSortItemStatus.EXCEPTION},
    HubSortItemStatus.ASSIGNED: {HubSortItemStatus.MOVED_TO_NEXT_LEG, HubSortItemStatus.EXCEPTION},
    HubSortItemStatus.MOVED_TO_NEXT_LEG: set(),
    HubSortItemStatus.EXCEPTION: {HubSortItemStatus.SCANNED},
}


def validate_line_haul_assignments(
    *,
    routes: list[dict[str, object]],
    vehicles: list[dict[str, object]],
    assignments: list[dict[str, object]],
    connectivity: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    network = connectivity or {}
    route_ids = {str(route.get("route_id") or "") for route in routes}
    route_lookup = {str(route.get("route_id") or ""): route for route in routes}
    vehicle_caps = {str(vehicle.get("vehicle_id") or ""): max(int(vehicle.get("capacity_units") or 0), 0) for vehicle in vehicles}
    vehicle_hubs = {str(vehicle.get("vehicle_id") or ""): str(vehicle.get("hub_code") or "") for vehicle in vehicles}
    vehicle_loads: dict[str, int] = defaultdict(int)
    duplicate_pairs: dict[tuple[str, str], int] = defaultdict(int)
    route_assigned_units: dict[str, int] = defaultdict(int)
    errors: list[dict[str, object]] = []

    for idx, assignment in enumerate(assignments):
        route_id = str(assignment.get("route_id") or "")
        vehicle_id = str(assignment.get("vehicle_id") or "")
        assigned_units = max(int(assignment.get("assigned_units") or 0), 0)

        duplicate_pairs[(route_id, vehicle_id)] += 1
        vehicle_loads[vehicle_id] += assigned_units
        route_assigned_units[route_id] += assigned_units

        if route_id not in route_ids:
            errors.append(
                {
                    "code": PLANNER_ERROR_UNKNOWN_ROUTE,
                    "message": f"Assignment row {idx + 1} references unknown route '{route_id}'.",
                    "field": "route_id",
                    "route_id": route_id,
                    "vehicle_id": vehicle_id,
                }
            )
        if vehicle_id not in vehicle_caps:
            errors.append(
                {
                    "code": PLANNER_ERROR_UNKNOWN_VEHICLE,
                    "message": f"Assignment row {idx + 1} references unknown vehicle '{vehicle_id}'.",
                    "field": "vehicle_id",
                    "route_id": route_id,
                    "vehicle_id": vehicle_id,
                }
            )
        if route_id in route_lookup and vehicle_id in vehicle_hubs:
            route = route_lookup[route_id]
            origin_hub = str(route.get("origin_hub") or "")
            destination_hub = str(route.get("destination_hub") or "")
            vehicle_hub = vehicle_hubs[vehicle_id]
            reachable = set(network.get(vehicle_hub, []))
            if vehicle_hub != origin_hub or (destination_hub and destination_hub not in reachable):
                errors.append(
                    {
                        "code": PLANNER_ERROR_ROUTE_INCOMPATIBLE,
                        "message": f"Vehicle '{vehicle_id}' cannot serve route '{route_id}' from hub '{vehicle_hub}'.",
                        "field": "route_id",
                        "route_id": route_id,
                        "vehicle_id": vehicle_id,
                        "origin_hub": origin_hub,
                        "destination_hub": destination_hub,
                    }
                )

    for (route_id, vehicle_id), count in sorted(duplicate_pairs.items()):
        if count > 1:
            errors.append(
                {
                    "code": PLANNER_ERROR_DUPLICATE_ASSIGNMENT,
                    "message": f"Route '{route_id}' is assigned to vehicle '{vehicle_id}' {count} times.",
                    "field": "assignments",
                    "route_id": route_id,
                    "vehicle_id": vehicle_id,
                    "duplicate_count": count,
                }
            )

    for vehicle_id, used_units in sorted(vehicle_loads.items()):
        capacity_units = vehicle_caps.get(vehicle_id)
        if capacity_units is None:
            continue
        if used_units > capacity_units:
            errors.append(
                {
                    "code": PLANNER_ERROR_OVER_CAPACITY,
                    "message": f"Vehicle '{vehicle_id}' is overloaded by {used_units - capacity_units} units.",
                    "field": "assigned_units",
                    "vehicle_id": vehicle_id,
                    "capacity_units": capacity_units,
                    "assigned_units": used_units,
                }
            )
    for route_id, route in sorted(route_lookup.items()):
        demand_units = max(int(route.get("demand_units") or 0), 0)
        assigned_units = route_assigned_units.get(route_id, 0)
        if assigned_units < demand_units:
            errors.append(
                {
                    "code": PLANNER_ERROR_ROUTE_UNSCHEDULED,
                    "message": f"Route '{route_id}' is short by {demand_units - assigned_units} units.",
                    "field": "assigned_units",
                    "route_id": route_id,
                    "demand_units": demand_units,
                    "assigned_units": assigned_units,
                }
            )

    utilization = [
        {
            "vehicle_id": vehicle_id,
            "capacity_units": capacity_units,
            "assigned_units": vehicle_loads.get(vehicle_id, 0),
            "utilization_percent": round(((vehicle_loads.get(vehicle_id, 0) / capacity_units) * 100), 2) if capacity_units else 0.0,
        }
        for vehicle_id, capacity_units in sorted(vehicle_caps.items())
    ]
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "summary": {
            "assignment_count": len(assignments),
            "error_count": len(errors),
            "utilization": utilization,
        },
    }


def optimize_line_haul_plan_assignments(
    *,
    routes: list[dict[str, object]],
    vehicles: list[dict[str, object]],
    connectivity: dict[str, list[str]],
    locked_assignments: list[dict[str, object]],
    random_seed: int,
) -> dict[str, object]:
    result = run_line_haul_optimizer(
        PlannerInput(
            routes=[
                RouteDefinition(
                    route_id=str(route.get("route_id") or ""),
                    origin_hub=str(route.get("origin_hub") or ""),
                    destination_hub=str(route.get("destination_hub") or ""),
                    demand_units=max(int(route.get("demand_units") or 0), 0),
                )
                for route in routes
            ],
            vehicles=[
                VehicleCapacity(
                    vehicle_id=str(vehicle.get("vehicle_id") or ""),
                    hub_code=str(vehicle.get("hub_code") or ""),
                    capacity_units=max(int(vehicle.get("capacity_units") or 0), 0),
                )
                for vehicle in vehicles
            ],
            connectivity=connectivity,
            locked_assignments=[
                LockedAssignment(
                    route_id=str(item.get("route_id") or ""),
                    vehicle_id=str(item.get("vehicle_id") or ""),
                    lock_units=item.get("lock_units") if item.get("lock_units") is None else max(int(item.get("lock_units") or 0), 0),
                    override_units=item.get("override_units") if item.get("override_units") is None else max(int(item.get("override_units") or 0), 0),
                )
                for item in locked_assignments
            ],
            random_seed=random_seed,
        )
    )
    assignment_rows = [
        {"route_id": item.route_id, "vehicle_id": item.vehicle_id, "assigned_units": item.assigned_units}
        for item in result.assignments
    ]
    return {"assignments": assignment_rows, "unassigned_routes": result.unassigned_routes, "metadata": result.metadata}


async def get_zone_by_pincode(pincode: str, db: AsyncSession) -> DeliveryZone | None:
    zones = (await db.execute(select(DeliveryZone).where(DeliveryZone.is_active == True))).scalars().all()  # noqa: E712
    for zone in zones:
        if pincode in json.loads(zone.pincodes_json or "[]"):
            return zone
    return None


async def quote_shipping(
    pincode: str,
    cod: bool,
    db: AsyncSession,
    *,
    shipping_option_code: str | None = None,
) -> dict[str, object]:
    zone = await get_zone_by_pincode(pincode, db)
    if zone is None:
        option = None
        if shipping_option_code:
            option = (
                await db.execute(
                    select(ShippingOption).where(
                        ShippingOption.code == shipping_option_code,
                        ShippingOption.zone_id == None,  # noqa: E711
                        ShippingOption.is_active == True,  # noqa: E712
                    )
                )
            ).scalars().first()
        else:
            option = (
                await db.execute(
                    select(ShippingOption).where(
                        ShippingOption.zone_id == None,  # noqa: E711
                        ShippingOption.is_active == True,  # noqa: E712
                    ).order_by(ShippingOption.rate.asc())
                )
            ).scalars().first()
        if option is None:
            return {
                "serviceable": False,
                "zone_code": None,
                "shipping_rate": 0.0,
                "cod_enabled": False,
                "shipping_option": None,
            }
        return {
            "serviceable": True,
            "zone_code": "GLOBAL",
            "shipping_rate": option.rate,
            "cod_enabled": option.cod_enabled,
            "shipping_option": option.code,
        }
    option_query = select(ShippingOption).where(
        ShippingOption.zone_id == zone.id,
        ShippingOption.is_active == True,  # noqa: E712
    )
    if shipping_option_code:
        option_query = option_query.where(ShippingOption.code == shipping_option_code)
    else:
        option_query = option_query.order_by(ShippingOption.rate.asc())
    option = (await db.execute(option_query)).scalars().first()
    effective_cod = option.cod_enabled if option else zone.cod_enabled
    if cod and not effective_cod:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="COD not supported for this zone")
    return {
        "serviceable": True,
        "zone_code": zone.code,
        "shipping_rate": option.rate if option else zone.shipping_rate,
        "cod_enabled": effective_cod,
        "shipping_option": option.code if option else None,
    }


async def get_pickup_job_or_404(pickup_job_id: int, db: AsyncSession) -> PickupJob:
    pickup_job = await db.get(PickupJob, pickup_job_id)
    if pickup_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup job not found")
    return pickup_job


async def get_manifest_or_404(manifest_id: int, db: AsyncSession) -> ShipmentManifest:
    manifest = await db.get(ShipmentManifest, manifest_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    return manifest


async def get_trip_or_404(trip_id: int, db: AsyncSession) -> LineHaulTrip:
    trip = await db.get(LineHaulTrip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


async def get_hub_sort_queue_or_404(queue_id: int, db: AsyncSession) -> HubSortQueue:
    queue = await db.get(HubSortQueue, queue_id)
    if queue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hub sort queue not found")
    return queue


async def append_hub_operation_event(
    *,
    hub_id: int,
    operation_type: str,
    db: AsyncSession,
    queue_id: int | None = None,
    queue_item_id: int | None = None,
    shipment_id: int | None = None,
    manifest_id: int | None = None,
    actor_type: str = "system",
    actor_id: int | None = None,
    payload: dict[str, object] | None = None,
) -> HubOperationEvent:
    event = HubOperationEvent(
        hub_id=hub_id,
        queue_id=queue_id,
        queue_item_id=queue_item_id,
        shipment_id=shipment_id,
        manifest_id=manifest_id,
        operation_type=operation_type,
        actor_type=actor_type,
        actor_id=actor_id,
        payload_json=json.dumps(payload or {}),
    )
    db.add(event)
    await db.flush()
    return event


async def transition_hub_item_state(
    *,
    item: HubSortQueueItem,
    queue: HubSortQueue,
    hub_id: int,
    to_status: HubSortItemStatus,
    actor_id: int | None,
    operation_type: str,
    db: AsyncSession,
    payload: dict[str, object] | None = None,
) -> HubSortQueueItem:
    from_status = item.status
    if to_status != from_status and to_status not in ALLOWED_HUB_ITEM_TRANSITIONS.get(from_status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal hub item transition: {from_status.value} -> {to_status.value}",
        )
    item.status = to_status
    item.updated_at = utc_now()
    await append_hub_operation_event(
        hub_id=hub_id,
        operation_type=operation_type,
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=item.shipment_id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={
            "from_status": from_status.value,
            "to_status": to_status.value,
            "operator_action": operation_type,
            **(payload or {}),
        },
        db=db,
    )
    return item


async def create_hub_sort_queue(
    *,
    hub_id: int,
    code: str,
    manifest_id: int | None,
    actor_id: int | None,
    db: AsyncSession,
) -> HubSortQueue:
    queue = HubSortQueue(hub_id=hub_id, code=code, manifest_id=manifest_id)
    db.add(queue)
    await db.flush()
    await append_hub_operation_event(
        hub_id=hub_id,
        operation_type="sort_queue_created",
        queue_id=queue.id,
        manifest_id=manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={"code": code},
        db=db,
    )
    return queue


async def close_hub_sort_queue(queue: HubSortQueue, *, actor_id: int | None, db: AsyncSession) -> HubSortQueue:
    queue.status = HubSortQueueStatus.CLOSED
    queue.closed_at = utc_now()
    await append_hub_operation_event(
        hub_id=queue.hub_id,
        operation_type="sort_queue_closed",
        queue_id=queue.id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={},
        db=db,
    )
    return queue


async def record_hub_intake_scan(
    *,
    queue: HubSortQueue,
    shipment_id: int,
    hub_id: int,
    actor_id: int | None,
    scan_code: str,
    notes: str,
    db: AsyncSession,
) -> HubSortQueueItem:
    item = HubSortQueueItem(
        queue_id=queue.id or 0,
        shipment_id=shipment_id,
        status=HubSortItemStatus.SCANNED,
        scanned_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(item)
    await db.flush()
    await append_hub_operation_event(
        hub_id=hub_id,
        operation_type="hub_intake_recorded",
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=shipment_id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={"scan_code": scan_code, "notes": notes},
        db=db,
    )
    return item


async def assign_sort_bucket(
    *,
    item: HubSortQueueItem,
    queue: HubSortQueue,
    hub_id: int,
    carrier: str,
    vehicle_number: str,
    next_hub_id: int | None,
    actor_id: int | None,
    db: AsyncSession,
) -> HubSortQueueItem:
    if item.status == HubSortItemStatus.EXCEPTION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot assign shipment with unresolved exception")
    await transition_hub_item_state(
        item=item,
        queue=queue,
        hub_id=hub_id,
        to_status=HubSortItemStatus.ASSIGNED,
        actor_id=actor_id,
        operation_type="sort_bucket_assigned",
        payload={"carrier": carrier, "vehicle_number": vehicle_number, "next_hub_id": next_hub_id},
        db=db,
    )
    item.assigned_next_hub_id = next_hub_id
    item.assigned_carrier = carrier
    item.assigned_vehicle_number = vehicle_number
    item.assigned_at = utc_now()
    return item


async def stage_outbound_shipment(
    *,
    item: HubSortQueueItem,
    queue: HubSortQueue,
    hub_id: int,
    actor_id: int | None,
    carrier: str,
    vehicle_number: str,
    db: AsyncSession,
) -> HubSortQueueItem:
    if item.status != HubSortItemStatus.ASSIGNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shipment must be assigned before outbound staging")
    if item.assigned_carrier != carrier or item.assigned_vehicle_number != vehicle_number:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assigned carrier/vehicle mismatch")
    await transition_hub_item_state(
        item=item,
        queue=queue,
        hub_id=hub_id,
        to_status=HubSortItemStatus.MOVED_TO_NEXT_LEG,
        actor_id=actor_id,
        operation_type="outbound_staged",
        payload={"carrier": carrier, "vehicle_number": vehicle_number},
        db=db,
    )
    item.moved_at = utc_now()
    return item


async def recirculate_or_rework_hub_item(
    *,
    item: HubSortQueueItem,
    queue: HubSortQueue,
    hub_id: int,
    actor_id: int | None,
    exception_code: str,
    notes: str,
    requeue_for_sorting: bool,
    db: AsyncSession,
) -> HubSortQueueItem:
    target_status = HubSortItemStatus.SCANNED if requeue_for_sorting else HubSortItemStatus.EXCEPTION
    await transition_hub_item_state(
        item=item,
        queue=queue,
        hub_id=hub_id,
        to_status=target_status,
        actor_id=actor_id,
        operation_type="exception_requeued" if requeue_for_sorting else "hold_queue_updated",
        payload={"exception_code": exception_code, "notes": notes},
        db=db,
    )
    item.exception_code = exception_code
    item.exception_notes = notes
    if requeue_for_sorting:
        item.assigned_carrier = ""
        item.assigned_vehicle_number = ""
        item.assigned_next_hub_id = None
    return item


async def confirm_dispatch(
    *,
    item: HubSortQueueItem,
    queue: HubSortQueue,
    hub_id: int,
    actor_id: int | None,
    db: AsyncSession,
) -> None:
    if item.status != HubSortItemStatus.MOVED_TO_NEXT_LEG:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dispatch confirmation requires outbound staging completion")
    await append_hub_operation_event(
        hub_id=hub_id,
        operation_type="dispatch_confirmed",
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=item.shipment_id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={"confirmed_at": utc_now().isoformat()},
        db=db,
    )


async def update_shipment_tracking(
    shipment_id: int,
    status_value: OrderStatus,
    location: str,
    remarks: str,
    db: AsyncSession,
    *,
    actor_type: str = "system",
    actor_id: int | None = None,
    context: dict[str, object] | None = None,
) -> Shipment:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    previous_status = shipment.status
    if previous_status == status_value:
        return shipment
    if status_value not in ALLOWED_SHIPMENT_TRANSITIONS.get(previous_status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal shipment transition: {previous_status.value} -> {status_value.value}",
        )
    shipment.status = status_value
    shipment.current_location = location
    shipment.updated_at = utc_now()
    db.add(
        ShipmentTracking(
            shipment_id=shipment.id,
            from_status=previous_status,
            status=status_value,
            location=location,
            remarks=remarks,
            actor_type=actor_type,
            actor_id=actor_id,
            context_json=json.dumps(context or {}),
        )
    )
    return shipment


async def create_pickup_job_for_vendor_order(
    vendor_order: VendorOrder,
    shipment: Shipment,
    branch_id: int | None,
    db: AsyncSession,
) -> PickupJob:
    pickup_job = PickupJob(
        vendor_order_id=vendor_order.id,
        shipment_id=shipment.id,
        branch_id=branch_id,
        status=PickupJobStatus.PENDING,
    )
    db.add(pickup_job)
    await db.flush()
    return pickup_job


async def assign_pickup_job(pickup_job: PickupJob, agent: DeliveryAgent, db: AsyncSession) -> None:
    if agent.status not in {DeliveryAgentStatus.AVAILABLE, DeliveryAgentStatus.ASSIGNED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is not available")
    pickup_job.agent_id = agent.id
    pickup_job.status = PickupJobStatus.ASSIGNED
    agent.status = DeliveryAgentStatus.ASSIGNED
    agent.current_load += 1
    shipment = await db.get(Shipment, pickup_job.shipment_id)
    if shipment:
        await update_shipment_tracking(shipment.id, OrderStatus.PROCESSING, "Vendor pickup scheduled", "Pickup agent assigned", db)


async def complete_pickup_job(pickup_job: PickupJob, location: str, db: AsyncSession) -> None:
    pickup_job.status = PickupJobStatus.PICKED_UP
    pickup_job.picked_up_at = utc_now()
    vendor_order = await db.get(VendorOrder, pickup_job.vendor_order_id)
    if vendor_order:
        vendor_order.status = VendorOrderStatus.SHIPPED
        vendor_order.updated_at = utc_now()
    await update_shipment_tracking(pickup_job.shipment_id, OrderStatus.SHIPPED, location, "Package picked up from vendor", db)


async def start_line_haul_trip(trip: LineHaulTrip, db: AsyncSession) -> None:
    manifest = await db.get(ShipmentManifest, trip.manifest_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    manifest.status = ShipmentManifestStatus.DISPATCHED
    manifest.updated_at = utc_now()
    trip.status = LineHaulTripStatus.IN_TRANSIT
    trip.departed_at = utc_now()
    for shipment_id in json.loads(manifest.shipment_ids_json or "[]"):
        await update_shipment_tracking(shipment_id, OrderStatus.SHIPPED, "Line haul", "Manifest dispatched", db)


async def arrive_line_haul_trip(trip: LineHaulTrip, db: AsyncSession) -> None:
    manifest = await db.get(ShipmentManifest, trip.manifest_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    manifest.status = ShipmentManifestStatus.RECEIVED
    manifest.updated_at = utc_now()
    trip.status = LineHaulTripStatus.ARRIVED
    trip.arrived_at = utc_now()
    destination_branch = await db.get(Branch, manifest.branch_id) if manifest.branch_id else None
    destination_hub = await db.get(Hub, manifest.destination_hub_id) if manifest.destination_hub_id else None
    location = destination_branch.name if destination_branch else (destination_hub.name if destination_hub else "Destination hub")
    for shipment_id in json.loads(manifest.shipment_ids_json or "[]"):
        await update_shipment_tracking(
            shipment_id,
            OrderStatus.OUT_FOR_DELIVERY,
            location,
            "Shipment received at destination hub",
            db,
            context={"manifest_id": manifest.id, "trip_id": trip.id, "branch_id": manifest.branch_id},
        )


async def create_reverse_pickup(return_request: ReturnRequest, db: AsyncSession) -> ReversePickupJob:
    reverse_pickup = ReversePickupJob(return_request_id=return_request.id)
    db.add(reverse_pickup)
    await db.flush()
    return reverse_pickup


async def assign_reverse_pickup(job: ReversePickupJob, agent: DeliveryAgent, db: AsyncSession) -> None:
    job.agent_id = agent.id
    job.status = ReversePickupStatus.ASSIGNED
    agent.status = DeliveryAgentStatus.ASSIGNED
    agent.current_load += 1


async def complete_reverse_pickup(job: ReversePickupJob, db: AsyncSession) -> None:
    job.status = ReversePickupStatus.PICKED_UP
    job.picked_up_at = utc_now()


async def record_branch_inventory_movement(
    *,
    branch_id: int,
    shipment_id: int | None,
    variant_id: int | None,
    movement_type: str,
    quantity: int,
    notes: str,
    db: AsyncSession,
) -> BranchInventoryMovement:
    movement = BranchInventoryMovement(
        branch_id=branch_id,
        shipment_id=shipment_id,
        variant_id=variant_id,
        movement_type=movement_type,
        quantity=quantity,
        notes=notes,
    )
    db.add(movement)
    await db.flush()
    return movement


async def create_delivery_exception(
    *,
    shipment: Shipment,
    exception_type: str,
    failure_reason: str,
    notes: str,
    agent_id: int | None,
    rescheduled_for: datetime | None,
    db: AsyncSession,
) -> DeliveryException:
    if shipment.status != OrderStatus.OUT_FOR_DELIVERY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Delivery exceptions can only be reported from {OrderStatus.OUT_FOR_DELIVERY.value}",
        )
    exception = DeliveryException(
        shipment_id=shipment.id or 0,
        agent_id=agent_id,
        exception_type=exception_type,
        failure_reason=failure_reason,
        notes=notes,
        rescheduled_for=rescheduled_for,
    )
    shipment.updated_at = utc_now()
    shipment.current_location = "Delivery exception"
    db.add(exception)
    db.add(
        ShipmentTracking(
            shipment_id=shipment.id or 0,
            from_status=shipment.status,
            status=shipment.status,
            location="Delivery exception",
            remarks=failure_reason or exception_type,
            actor_type="ops",
            actor_id=agent_id,
            context_json=json.dumps(
                {
                    "event": "delivery_exception_reported",
                    "exception_type": exception_type,
                    "rescheduled_for": rescheduled_for.isoformat() if rescheduled_for else None,
                }
            ),
        )
    )
    await db.flush()
    return exception


async def reschedule_delivery_exception(
    exception: DeliveryException,
    shipment: Shipment,
    rescheduled_for: datetime,
    db: AsyncSession,
) -> None:
    if exception.status == DeliveryExceptionStatus.RTO_INITIATED or shipment.status == OrderStatus.RETURNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot reschedule after RTO initiation")
    exception.status = DeliveryExceptionStatus.RESCHEDULED
    exception.rescheduled_for = rescheduled_for
    exception.updated_at = utc_now()
    shipment.updated_at = utc_now()
    db.add(
        ShipmentTracking(
            shipment_id=shipment.id or 0,
            from_status=shipment.status,
            status=shipment.status,
            location=shipment.current_location or "Delivery branch",
            remarks=f"Delivery rescheduled for {rescheduled_for.isoformat()}",
            actor_type="ops",
            actor_id=exception.agent_id,
            context_json=json.dumps({"event": "delivery_rescheduled", "exception_id": exception.id}),
        )
    )


async def initiate_rto_for_exception(
    exception: DeliveryException,
    shipment: Shipment,
    db: AsyncSession,
) -> None:
    if exception.status == DeliveryExceptionStatus.RTO_INITIATED and shipment.status == OrderStatus.RETURNED:
        return
    if shipment.status != OrderStatus.OUT_FOR_DELIVERY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"RTO can only be initiated from {OrderStatus.OUT_FOR_DELIVERY.value}",
        )
    exception.status = DeliveryExceptionStatus.RTO_INITIATED
    exception.rto_initiated_at = utc_now()
    exception.updated_at = utc_now()
    await update_shipment_tracking(
        shipment.id or 0,
        OrderStatus.RETURNED,
        "RTO initiated",
        "Return to origin initiated",
        db,
        actor_type="ops",
        actor_id=exception.agent_id,
        context={"event": "rto_initiated", "exception_id": exception.id},
    )


async def create_shipment_proof(
    *,
    shipment_id: int,
    agent_id: int | None,
    proof_type: str,
    otp_code: str,
    photo_url: str,
    signature_url: str,
    notes: str,
    db: AsyncSession,
) -> ShipmentProof:
    proof = ShipmentProof(
        shipment_id=shipment_id,
        agent_id=agent_id,
        proof_type=proof_type,
        otp_code=otp_code,
        photo_url=photo_url,
        signature_url=signature_url,
        notes=notes,
    )
    db.add(proof)
    await db.flush()
    return proof


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * radius_km * asin(sqrt(a))


def _route_distance_km(stops: list[dict[str, object]]) -> float:
    if len(stops) < 2:
        return 0.0
    total = 0.0
    for index in range(1, len(stops)):
        previous = stops[index - 1]
        current = stops[index]
        total += _haversine_km(
            float(previous["latitude"]),
            float(previous["longitude"]),
            float(current["latitude"]),
            float(current["longitude"]),
        )
    return total


def _nearest_neighbor_route(stops: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(stops) <= 2:
        return stops[:]

    unvisited = stops[1:]
    route = [stops[0]]
    while unvisited:
        last = route[-1]
        next_stop = min(
            unvisited,
            key=lambda candidate: _haversine_km(
                float(last["latitude"]),
                float(last["longitude"]),
                float(candidate["latitude"]),
                float(candidate["longitude"]),
            ),
        )
        route.append(next_stop)
        unvisited.remove(next_stop)
    return route


def _two_opt_route(stops: list[dict[str, object]]) -> list[dict[str, object]]:
    best = stops[:]
    improved = True
    while improved and len(best) > 3:
        improved = False
        best_distance = _route_distance_km(best)
        for start in range(1, len(best) - 2):
            for end in range(start + 1, len(best) - 1):
                candidate = best[:start] + list(reversed(best[start : end + 1])) + best[end + 1 :]
                candidate_distance = _route_distance_km(candidate)
                if candidate_distance + 0.001 < best_distance:
                    best = candidate
                    best_distance = candidate_distance
                    improved = True
    return best


async def _shipment_route_stop(shipment_id: int, db: AsyncSession) -> dict[str, object] | None:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        return None
    order = await db.get(Order, shipment.order_id)
    address = await db.get(Address, order.address_id) if order else None
    if address is None or address.latitude is None or address.longitude is None:
        return {
            "shipment_id": encode_id(shipment.id or 0),
            "awb": shipment.awb,
            "routable": False,
            "reason": "destination_coordinates_missing",
        }
    return {
        "shipment_db_id": shipment.id,
        "shipment_id": encode_id(shipment.id or 0),
        "order_id": encode_id(order.id or 0) if order else None,
        "awb": shipment.awb,
        "name": address.name,
        "line1": address.line1,
        "city": address.city,
        "pincode": address.pincode,
        "latitude": float(address.latitude),
        "longitude": float(address.longitude),
        "routable": True,
    }


async def optimize_manifest_route(
    *,
    manifest: ShipmentManifest,
    db: AsyncSession,
    trip: LineHaulTrip | None = None,
    average_speed_kph: float = 28.0,
    service_minutes_per_stop: int = 8,
) -> RouteOptimizationPlan:
    shipment_ids = [int(shipment_id) for shipment_id in json.loads(manifest.shipment_ids_json or "[]")]
    raw_stops = [await _shipment_route_stop(shipment_id, db) for shipment_id in shipment_ids]
    routable = [stop for stop in raw_stops if stop and stop.get("routable")]
    unroutable = [stop for stop in raw_stops if stop and not stop.get("routable")]

    ordered = _two_opt_route(_nearest_neighbor_route(routable))
    total_distance_km = _route_distance_km(ordered)
    speed = max(average_speed_kph, 5.0)
    estimated_duration = int(round((total_distance_km / speed) * 60 + len(ordered) * max(service_minutes_per_stop, 1)))

    traveled = 0.0
    enriched_stops: list[dict[str, object]] = []
    for index, stop in enumerate(ordered):
        leg_distance = 0.0
        if index > 0:
            previous = ordered[index - 1]
            leg_distance = _haversine_km(
                float(previous["latitude"]),
                float(previous["longitude"]),
                float(stop["latitude"]),
                float(stop["longitude"]),
            )
            traveled += leg_distance
        eta_minutes = int(round((traveled / speed) * 60 + (index + 1) * max(service_minutes_per_stop, 1)))
        enriched_stops.append(
            {
                **stop,
                "sequence": index + 1,
                "distance_from_previous_km": round(leg_distance, 2),
                "eta_minutes": eta_minutes,
            }
        )

    plan = (
        await db.execute(
            select(RouteOptimizationPlan).where(
                RouteOptimizationPlan.manifest_id == manifest.id,
                RouteOptimizationPlan.trip_id == (trip.id if trip else None),
            )
        )
    ).scalars().first()
    if plan is None:
        plan = RouteOptimizationPlan(manifest_id=manifest.id, trip_id=trip.id if trip else None)
        db.add(plan)

    routed_stop_count = len(enriched_stops)
    total_stop_count = routed_stop_count + len(unroutable)
    plan.strategy = "nearest_neighbor_2opt_v1"
    plan.total_distance_km = round(total_distance_km, 2)
    plan.estimated_duration_minutes = estimated_duration
    plan.routed_stop_count = routed_stop_count
    plan.unroutable_stop_count = len(unroutable)
    plan.score = round((routed_stop_count / total_stop_count) * 100, 2) if total_stop_count else 0.0
    plan.stops_json = json.dumps(enriched_stops)
    plan.metrics_json = json.dumps(
        {
            "average_speed_kph": speed,
            "service_minutes_per_stop": max(service_minutes_per_stop, 1),
            "unroutable_stops": unroutable,
        }
    )
    plan.updated_at = utc_now()
    await db.flush()
    return plan


async def get_route_plan(
    *,
    manifest_id: int | None = None,
    trip_id: int | None = None,
    db: AsyncSession,
) -> RouteOptimizationPlan | None:
    query = select(RouteOptimizationPlan)
    if trip_id is not None:
        query = query.where(RouteOptimizationPlan.trip_id == trip_id)
    if manifest_id is not None:
        query = query.where(RouteOptimizationPlan.manifest_id == manifest_id)
    query = query.order_by(RouteOptimizationPlan.updated_at.desc())
    return (await db.execute(query)).scalars().first()


async def ingest_courier_location_ping(
    *,
    trip: LineHaulTrip,
    latitude: float,
    longitude: float,
    shipment_id: int | None,
    agent_id: int | None,
    speed_kph: float | None,
    heading: float | None,
    accuracy_meters: float | None,
    source: str,
    label: str,
    recorded_at: datetime | None,
    db: AsyncSession,
) -> CourierLocationPing:
    ping = CourierLocationPing(
        trip_id=trip.id,
        shipment_id=shipment_id,
        agent_id=agent_id,
        latitude=latitude,
        longitude=longitude,
        speed_kph=speed_kph,
        heading=heading,
        accuracy_meters=accuracy_meters,
        source=source,
        label=label,
        recorded_at=recorded_at or utc_now(),
    )
    trip.last_latitude = latitude
    trip.last_longitude = longitude
    trip.last_gps_at = ping.recorded_at
    db.add(ping)
    if shipment_id:
        shipment = await db.get(Shipment, shipment_id)
        if shipment:
            shipment.current_location = label or f"{latitude:.5f}, {longitude:.5f}"
            shipment.updated_at = utc_now()
    await db.flush()
    return ping


async def resolve_user_branch_scope(current_user: User, db: AsyncSession) -> set[int] | None:
    """Return allowed branch IDs for the caller, or ``None`` for unrestricted access."""
    if current_user.is_superuser:
        return None
    scoped_agents = (
        await db.execute(select(DeliveryAgent).where(DeliveryAgent.user_id == current_user.id))
    ).scalars().all()
    return {agent.branch_id for agent in scoped_agents}


def ensure_branch_scope_access(
    *,
    allowed_branch_ids: set[int] | None,
    requested_branch_id: int | None,
) -> None:
    """Raise when a caller requests data outside their authorized branch scope."""
    if allowed_branch_ids is None:
        return
    if requested_branch_id is None:
        if allowed_branch_ids:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch-scoped access denied")
    if requested_branch_id not in allowed_branch_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch-scoped access denied")


def calculate_branch_kpi_snapshot(
    *,
    movement_count: int,
    total_moved_units: int,
    agent_count: int,
    active_agent_count: int,
    pickup_jobs: list[PickupJob],
    reverse_pickups: list[ReversePickupJob],
    exceptions: list[DeliveryException],
) -> dict[str, float | int]:
    completed_pickups = len([job for job in pickup_jobs if job.status == PickupJobStatus.PICKED_UP])
    reverse_completed = len(
        [
            job
            for job in reverse_pickups
            if job.status in {ReversePickupStatus.PICKED_UP, ReversePickupStatus.RECEIVED, ReversePickupStatus.RETURNED_TO_VENDOR}
        ]
    )
    open_exceptions = len([item for item in exceptions if item.status in {DeliveryExceptionStatus.OPEN, DeliveryExceptionStatus.RESCHEDULED}])
    total_delivery_attempts = len(pickup_jobs) + len(exceptions)
    failed_deliveries = len([item for item in exceptions if item.exception_type.lower() in {"failed_delivery", "delivery_failed"}])
    delivery_success_rate = round((completed_pickups / len(pickup_jobs)) * 100, 2) if pickup_jobs else 0.0
    return {
        "inventory_movements": movement_count,
        "total_moved_units": total_moved_units,
        "agent_count": agent_count,
        "active_agent_count": active_agent_count,
        "pickup_jobs": len(pickup_jobs),
        "completed_pickups": completed_pickups,
        "reverse_pickups": len(reverse_pickups),
        "reverse_completed": reverse_completed,
        "open_exceptions": open_exceptions,
        "failed_deliveries": failed_deliveries,
        "delivery_success_rate_percent": delivery_success_rate,
        "delivery_attempts": total_delivery_attempts,
        "backlog_shipments": max(total_delivery_attempts - completed_pickups, 0),
    }


def _resolve_window_bounds(date_from: date | None, date_to: date | None, timezone_name: str) -> tuple[datetime | None, datetime | None]:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = timezone.utc
    start_at = (
        datetime.combine(date_from, time.min).replace(tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
        if date_from
        else None
    )
    end_at = (
        datetime.combine(date_to, time.max).replace(tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
        if date_to
        else None
    )
    return start_at, end_at


async def build_branch_kpi_snapshot(
    *,
    db: AsyncSession,
    branch_id: int | None,
    allowed_branch_ids: set[int] | None,
    agent_id: int | None,
    zone_id: int | None,
    date_from: date | None,
    date_to: date | None,
    timezone_name: str = "UTC",
) -> dict[str, object]:
    ensure_branch_scope_access(allowed_branch_ids=allowed_branch_ids, requested_branch_id=branch_id)
    scoped_branch_ids = allowed_branch_ids if branch_id is None else {branch_id}

    pickup_query = select(PickupJob)
    reverse_query = select(ReversePickupJob)
    exception_query = select(DeliveryException)
    movement_query = select(BranchInventoryMovement)
    inventory_query = select(BranchInventory)
    agent_query = select(DeliveryAgent)
    branch_query = select(Branch)
    if scoped_branch_ids is not None:
        pickup_query = pickup_query.where(PickupJob.branch_id.in_(scoped_branch_ids))
        reverse_query = reverse_query.where(ReversePickupJob.branch_id.in_(scoped_branch_ids))
        movement_query = movement_query.where(BranchInventoryMovement.branch_id.in_(scoped_branch_ids))
        agent_query = agent_query.where(DeliveryAgent.branch_id.in_(scoped_branch_ids))
        exception_query = exception_query.where(
            DeliveryException.agent_id.in_(select(DeliveryAgent.id).where(DeliveryAgent.branch_id.in_(scoped_branch_ids)))
        )
        inventory_query = inventory_query.where(BranchInventory.branch_id.in_(scoped_branch_ids))
        branch_query = branch_query.where(Branch.id.in_(scoped_branch_ids))
    if zone_id is not None:
        branch_query = branch_query.where(Branch.zone_id == zone_id)
    if agent_id is not None:
        pickup_query = pickup_query.where(PickupJob.agent_id == agent_id)
        reverse_query = reverse_query.where(ReversePickupJob.agent_id == agent_id)
        exception_query = exception_query.where(DeliveryException.agent_id == agent_id)

    start_at, end_at = _resolve_window_bounds(date_from, date_to, timezone_name)
    if start_at:
        pickup_query = pickup_query.where(PickupJob.created_at >= start_at)
        reverse_query = reverse_query.where(ReversePickupJob.created_at >= start_at)
        exception_query = exception_query.where(DeliveryException.created_at >= start_at)
        movement_query = movement_query.where(BranchInventoryMovement.created_at >= start_at)
    if end_at:
        pickup_query = pickup_query.where(PickupJob.created_at <= end_at)
        reverse_query = reverse_query.where(ReversePickupJob.created_at <= end_at)
        exception_query = exception_query.where(DeliveryException.created_at <= end_at)
        movement_query = movement_query.where(BranchInventoryMovement.created_at <= end_at)

    scoped_branches = (await db.execute(branch_query)).scalars().all()
    filtered_branch_ids = {branch.id for branch in scoped_branches if branch.id is not None}
    if scoped_branch_ids is None and filtered_branch_ids:
        pickup_query = pickup_query.where(PickupJob.branch_id.in_(filtered_branch_ids))
        reverse_query = reverse_query.where(ReversePickupJob.branch_id.in_(filtered_branch_ids))
        movement_query = movement_query.where(BranchInventoryMovement.branch_id.in_(filtered_branch_ids))
        agent_query = agent_query.where(DeliveryAgent.branch_id.in_(filtered_branch_ids))
        inventory_query = inventory_query.where(BranchInventory.branch_id.in_(filtered_branch_ids))
        exception_query = exception_query.where(
            DeliveryException.agent_id.in_(select(DeliveryAgent.id).where(DeliveryAgent.branch_id.in_(filtered_branch_ids)))
        )

    pickup_jobs = (await db.execute(pickup_query)).scalars().all()
    reverse_pickups = (await db.execute(reverse_query)).scalars().all()
    exceptions = (await db.execute(exception_query)).scalars().all()
    movements = (await db.execute(movement_query)).scalars().all()
    inventory_rows = (await db.execute(inventory_query)).scalars().all()
    agents = (await db.execute(agent_query)).scalars().all()
    snapshot = calculate_branch_kpi_snapshot(
        movement_count=len(movements),
        total_moved_units=sum(movement.quantity for movement in movements),
        agent_count=len(agents),
        active_agent_count=len([agent for agent in agents if agent.status == DeliveryAgentStatus.AVAILABLE]),
        pickup_jobs=pickup_jobs,
        reverse_pickups=reverse_pickups,
        exceptions=exceptions,
    )
    success_attempts = len([job for job in pickup_jobs if job.status == PickupJobStatus.PICKED_UP])
    failed_attempts = len([job for job in pickup_jobs if job.status == PickupJobStatus.FAILED]) + len(
        [item for item in exceptions if item.exception_type.lower() in {"failed_delivery", "delivery_failed"}]
    )
    total_attempts = success_attempts + failed_attempts
    rto_count = len([item for item in exceptions if item.status == DeliveryExceptionStatus.RTO_INITIATED])
    pending_jobs = [job for job in pickup_jobs if job.status in {PickupJobStatus.PENDING, PickupJobStatus.ASSIGNED}]
    now = utc_now()
    analytics = get_analytics()
    inventory_health = analytics.build_branch_inventory_health(
        inventory_on_hand_units=sum(item.quantity for item in inventory_rows),
        items_at_risk=len([item for item in inventory_rows if item.quantity <= 0]),
        total_items=len(inventory_rows),
    )
    aging_buckets = analytics.build_branch_undelivered_aging_buckets(
        over_2h=len([job for job in pending_jobs if (now - job.created_at).total_seconds() >= 2 * 3600]),
        over_6h=len([job for job in pending_jobs if (now - job.created_at).total_seconds() >= 6 * 3600]),
        over_12h=len([job for job in pending_jobs if (now - job.created_at).total_seconds() >= 12 * 3600]),
    )
    attempt_and_exception_metrics = analytics.build_branch_attempt_and_exception_metrics(
        first_attempt_successes=success_attempts,
        total_attempts=total_attempts,
        rto_count=rto_count,
        open_exceptions=len([item for item in exceptions if item.status in {DeliveryExceptionStatus.OPEN, DeliveryExceptionStatus.RESCHEDULED}]),
    )
    avg_utilization = (
        sum(((agent.current_load / agent.capacity) * 100) if agent.capacity else 0 for agent in agents) / len(agents)
        if agents
        else 0.0
    )
    agent_utilization = analytics.build_branch_agent_utilization(
        assigned_agents=len([agent for agent in agents if agent.status == DeliveryAgentStatus.ASSIGNED]),
        active_agents=len([agent for agent in agents if agent.status == DeliveryAgentStatus.AVAILABLE]),
        average_utilization_percent=avg_utilization,
    )

    snapshot.update(
        {
            "attempt_success_rate_percent": round((success_attempts / total_attempts) * 100, 2) if total_attempts else 0.0,
            "attempt_failure_rate_percent": round((failed_attempts / total_attempts) * 100, 2) if total_attempts else 0.0,
            "rto_rate_percent": round((rto_count / len(exceptions)) * 100, 2) if exceptions else 0.0,
            **inventory_health,
            **aging_buckets,
            **attempt_and_exception_metrics,
            **agent_utilization,
        }
    )
    branch_code_map: dict[int, str] = {}
    branch_code_map = {branch.id or 0: branch.code for branch in scoped_branches if branch.id is not None}

    return {
        "snapshot": snapshot,
        "branch_scope": [encode_id(branch) for branch in sorted(scoped_branch_ids)] if scoped_branch_ids is not None else [],
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "timezone": timezone_name,
        "agent_id": encode_id(agent_id) if agent_id else None,
        "branch_codes": {encode_id(branch_id): code for branch_id, code in branch_code_map.items()},
    }


async def build_branch_kpi_drilldown(
    *,
    db: AsyncSession,
    branch_id: int | None,
    allowed_branch_ids: set[int] | None,
    agent_id: int | None,
    zone_id: int | None,
    date_from: date | None,
    date_to: date | None,
    timezone_name: str = "UTC",
) -> dict[str, object]:
    ensure_branch_scope_access(allowed_branch_ids=allowed_branch_ids, requested_branch_id=branch_id)
    scoped_branch_ids = allowed_branch_ids if branch_id is None else {branch_id}
    pickup_query = select(PickupJob)
    exception_query = select(DeliveryException)
    movement_query = select(BranchInventoryMovement)
    branch_query = select(Branch)

    if scoped_branch_ids is not None:
        pickup_query = pickup_query.where(PickupJob.branch_id.in_(scoped_branch_ids))
        movement_query = movement_query.where(BranchInventoryMovement.branch_id.in_(scoped_branch_ids))
        exception_query = exception_query.where(
            DeliveryException.agent_id.in_(select(DeliveryAgent.id).where(DeliveryAgent.branch_id.in_(scoped_branch_ids)))
        )
        branch_query = branch_query.where(Branch.id.in_(scoped_branch_ids))
    if zone_id is not None:
        branch_query = branch_query.where(Branch.zone_id == zone_id)
    if agent_id is not None:
        pickup_query = pickup_query.where(PickupJob.agent_id == agent_id)
        exception_query = exception_query.where(DeliveryException.agent_id == agent_id)
    start_at, end_at = _resolve_window_bounds(date_from, date_to, timezone_name)
    if start_at:
        pickup_query = pickup_query.where(PickupJob.created_at >= start_at)
        exception_query = exception_query.where(DeliveryException.created_at >= start_at)
        movement_query = movement_query.where(BranchInventoryMovement.created_at >= start_at)
    if end_at:
        pickup_query = pickup_query.where(PickupJob.created_at <= end_at)
        exception_query = exception_query.where(DeliveryException.created_at <= end_at)
        movement_query = movement_query.where(BranchInventoryMovement.created_at <= end_at)

    scoped_branches = (await db.execute(branch_query)).scalars().all()
    filtered_branch_ids = {branch.id for branch in scoped_branches if branch.id is not None}
    if filtered_branch_ids:
        pickup_query = pickup_query.where(PickupJob.branch_id.in_(filtered_branch_ids))
        movement_query = movement_query.where(BranchInventoryMovement.branch_id.in_(filtered_branch_ids))
        exception_query = exception_query.where(
            DeliveryException.agent_id.in_(select(DeliveryAgent.id).where(DeliveryAgent.branch_id.in_(filtered_branch_ids)))
        )

    pickups = (await db.execute(pickup_query)).scalars().all()
    exceptions = (await db.execute(exception_query)).scalars().all()
    movements = (await db.execute(movement_query)).scalars().all()

    agent_ids = {job.agent_id for job in pickups if job.agent_id} | {item.agent_id for item in exceptions if item.agent_id}
    agents = []
    if agent_ids:
        agents = (await db.execute(select(DeliveryAgent).where(DeliveryAgent.id.in_(agent_ids)))).scalars().all()
    agent_names = {agent.id or 0: agent.name for agent in agents if agent.id is not None}

    productivity: dict[int, dict[str, int]] = defaultdict(lambda: {"assigned": 0, "completed": 0, "failed": 0})
    for job in pickups:
        if not job.agent_id:
            continue
        productivity[job.agent_id]["assigned"] += 1
        if job.status == PickupJobStatus.PICKED_UP:
            productivity[job.agent_id]["completed"] += 1
    for item in exceptions:
        if not item.agent_id:
            continue
        productivity[item.agent_id]["failed"] += 1

    movement_totals: dict[str, int] = defaultdict(int)
    for movement in movements:
        movement_totals[movement.movement_type] += movement.quantity

    return {
        "productivity": [
            {
                "agent_id": encode_id(agent_key),
                "agent_name": agent_names.get(agent_key, f"Agent {agent_key}"),
                "assigned": totals["assigned"],
                "completed": totals["completed"],
                "failed": totals["failed"],
            }
            for agent_key, totals in sorted(productivity.items(), key=lambda item: item[1]["completed"], reverse=True)
        ],
        "delivery_outcomes": {
            "success": len([job for job in pickups if job.status == PickupJobStatus.PICKED_UP]),
            "failed": len([item for item in exceptions if item.exception_type.lower() in {"failed_delivery", "delivery_failed"}]),
        },
        "backlog": {
            "pending_pickups": len([job for job in pickups if job.status in {PickupJobStatus.PENDING, PickupJobStatus.ASSIGNED}]),
            "open_exceptions": len([item for item in exceptions if item.status in {DeliveryExceptionStatus.OPEN, DeliveryExceptionStatus.RESCHEDULED}]),
        },
        "inventory_flow": movement_totals,
        "actionable_queues": {
            "reassign_agent": [
                {
                    "agent_id": encode_id(agent_key),
                    "agent_name": agent_names.get(agent_key, f"Agent {agent_key}"),
                    "assigned": totals["assigned"],
                    "recommended_target": "lower_load_agent",
                }
                for agent_key, totals in sorted(productivity.items(), key=lambda item: item[1]["assigned"], reverse=True)[:5]
            ],
            "escalate_delayed": [
                {
                    "exception_id": encode_id(item.id or 0),
                    "shipment_id": encode_id(item.shipment_id) if item.shipment_id else None,
                    "agent_id": encode_id(item.agent_id) if item.agent_id else None,
                    "age_hours": round((utc_now() - item.created_at).total_seconds() / 3600, 2),
                }
                for item in sorted(
                    [
                        exception
                        for exception in exceptions
                        if exception.status in {DeliveryExceptionStatus.OPEN, DeliveryExceptionStatus.RESCHEDULED}
                    ],
                    key=lambda exception: exception.created_at,
                )[:20]
            ],
            "prioritize_aging": [
                {
                    "pickup_job_id": encode_id(job.id or 0),
                    "shipment_id": encode_id(job.shipment_id) if job.shipment_id else None,
                    "age_hours": round((utc_now() - job.created_at).total_seconds() / 3600, 2),
                }
                for job in sorted(
                    [job for job in pickups if job.status in {PickupJobStatus.PENDING, PickupJobStatus.ASSIGNED}],
                    key=lambda item: item.created_at,
                )[:20]
            ],
        },
        "timezone": timezone_name,
    }


async def list_branch_dashboard_alerts(
    *,
    db: AsyncSession,
    branch_id: int | None,
    allowed_branch_ids: set[int] | None,
    agent_id: int | None,
    zone_id: int | None,
    date_from: date | None,
    date_to: date | None,
    timezone_name: str = "UTC",
    backlog_threshold: int = 25,
    low_staff_threshold: int = 2,
    failure_rate_threshold: float = 20.0,
    sla_breach_threshold: int = 1,
) -> dict[str, object]:
    payload = await build_branch_kpi_snapshot(
        db=db,
        branch_id=branch_id,
        allowed_branch_ids=allowed_branch_ids,
        agent_id=agent_id,
        zone_id=zone_id,
        date_from=date_from,
        date_to=date_to,
        timezone_name=timezone_name,
    )
    snapshot = payload["snapshot"]
    alerts: list[dict[str, object]] = []
    if int(snapshot.get("backlog_shipments", 0)) >= backlog_threshold:
        alerts.append({"code": "backlog", "severity": "high", "message": "Backlog exceeded threshold."})
    if int(snapshot.get("active_agent_count", 0)) <= low_staff_threshold:
        alerts.append({"code": "low_staff", "severity": "medium", "message": "Active staffing is below threshold."})
    if float(snapshot.get("attempt_failure_rate_percent", 0.0)) >= failure_rate_threshold:
        alerts.append({"code": "high_failure", "severity": "high", "message": "Failure rate exceeded threshold."})
    if int(snapshot.get("open_exceptions", 0)) >= sla_breach_threshold:
        alerts.append({"code": "sla_violation", "severity": "high", "message": "SLA violation threshold breached."})
    escalation_hooks = []
    for alert in alerts:
        if alert["code"] == "backlog":
            escalation_hooks.append({"action": "prioritize_aging", "path": "/logistics/branch-dashboard/actions/prioritize-aging"})
        if alert["code"] == "sla_violation":
            escalation_hooks.append({"action": "escalate_issues", "path": "/logistics/branch-dashboard/actions/escalate-issues"})
        if alert["code"] == "high_failure":
            escalation_hooks.append({"action": "reassign_load", "path": "/logistics/branch-dashboard/actions/reassign-load"})
    return {
        "alerts": alerts,
        "thresholds": {
            "backlog": backlog_threshold,
            "low_staff": low_staff_threshold,
            "failure_rate": failure_rate_threshold,
            "sla_breach": sla_breach_threshold,
        },
        "escalation_hooks": escalation_hooks,
    }


async def reassign_branch_load(*, db: AsyncSession, branch_id: int, from_agent_id: int, to_agent_id: int, limit: int = 10) -> dict[str, int]:
    jobs = (
        await db.execute(
            select(PickupJob)
            .where(PickupJob.branch_id == branch_id, PickupJob.agent_id == from_agent_id, PickupJob.status.in_([PickupJobStatus.ASSIGNED, PickupJobStatus.PENDING]))
            .order_by(PickupJob.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    for job in jobs:
        job.agent_id = to_agent_id
        job.status = PickupJobStatus.ASSIGNED
    return {"reassigned_jobs": len(jobs)}


async def prioritize_aging_shipments(*, db: AsyncSession, branch_id: int, assignee_agent_id: int | None = None, limit: int = 20) -> dict[str, int]:
    stale_jobs = (
        await db.execute(
            select(PickupJob)
            .where(PickupJob.branch_id == branch_id, PickupJob.status == PickupJobStatus.PENDING)
            .order_by(PickupJob.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    for job in stale_jobs:
        job.status = PickupJobStatus.ASSIGNED
        if assignee_agent_id is not None:
            job.agent_id = assignee_agent_id
    return {"prioritized_jobs": len(stale_jobs)}


async def escalate_branch_issues(*, db: AsyncSession, branch_id: int, note: str = "Escalated from branch cockpit") -> dict[str, int]:
    exceptions = (
        await db.execute(
            select(DeliveryException).where(
                DeliveryException.status.in_([DeliveryExceptionStatus.OPEN, DeliveryExceptionStatus.RESCHEDULED]),
                DeliveryException.agent_id.in_(select(DeliveryAgent.id).where(DeliveryAgent.branch_id == branch_id)),
            )
        )
    ).scalars().all()
    for item in exceptions:
        item.notes = f"{item.notes}\n{note}".strip()
        item.updated_at = utc_now()
    return {"escalated_issues": len(exceptions)}
