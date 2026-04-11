from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.commerce.models import Address
from src.apps.core.time import utc_now
from src.apps.iam.utils.hashid import encode_id
from src.apps.logistics.models import (
    Branch,
    BranchInventoryMovement,
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
from src.apps.orders.models import Order, OrderStatus, ReturnRequest, Shipment, ShipmentTracking, VendorOrder, VendorOrderStatus

ALLOWED_SHIPMENT_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.RETURNED},
}


def validate_line_haul_assignments(
    *,
    routes: list[dict[str, object]],
    vehicles: list[dict[str, object]],
    assignments: list[dict[str, object]],
) -> dict[str, object]:
    route_ids = {str(route.get("route_id") or "") for route in routes}
    vehicle_caps = {str(vehicle.get("vehicle_id") or ""): max(int(vehicle.get("capacity_units") or 0), 0) for vehicle in vehicles}
    vehicle_loads: dict[str, int] = defaultdict(int)
    duplicate_pairs: dict[tuple[str, str], int] = defaultdict(int)
    errors: list[dict[str, object]] = []

    for idx, assignment in enumerate(assignments):
        route_id = str(assignment.get("route_id") or "")
        vehicle_id = str(assignment.get("vehicle_id") or "")
        assigned_units = max(int(assignment.get("assigned_units") or 0), 0)

        duplicate_pairs[(route_id, vehicle_id)] += 1
        vehicle_loads[vehicle_id] += assigned_units

        if route_id not in route_ids:
            errors.append(
                {
                    "code": "unknown_route",
                    "message": f"Assignment row {idx + 1} references unknown route '{route_id}'.",
                    "field": "route_id",
                    "route_id": route_id,
                    "vehicle_id": vehicle_id,
                }
            )
        if vehicle_id not in vehicle_caps:
            errors.append(
                {
                    "code": "unknown_vehicle",
                    "message": f"Assignment row {idx + 1} references unknown vehicle '{vehicle_id}'.",
                    "field": "vehicle_id",
                    "route_id": route_id,
                    "vehicle_id": vehicle_id,
                }
            )

    for (route_id, vehicle_id), count in sorted(duplicate_pairs.items()):
        if count > 1:
            errors.append(
                {
                    "code": "duplicate_assignment",
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
                    "code": "over_capacity",
                    "message": f"Vehicle '{vehicle_id}' is overloaded by {used_units - capacity_units} units.",
                    "field": "assigned_units",
                    "vehicle_id": vehicle_id,
                    "capacity_units": capacity_units,
                    "assigned_units": used_units,
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
    item.status = HubSortItemStatus.ASSIGNED
    item.assigned_next_hub_id = next_hub_id
    item.assigned_carrier = carrier
    item.assigned_vehicle_number = vehicle_number
    item.assigned_at = utc_now()
    item.updated_at = utc_now()
    await append_hub_operation_event(
        hub_id=hub_id,
        operation_type="sort_bucket_assigned",
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=item.shipment_id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={"carrier": carrier, "vehicle_number": vehicle_number, "next_hub_id": next_hub_id},
        db=db,
    )
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
    item.status = HubSortItemStatus.MOVED_TO_NEXT_LEG
    item.moved_at = utc_now()
    item.updated_at = utc_now()
    await append_hub_operation_event(
        hub_id=hub_id,
        operation_type="outbound_staged",
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=item.shipment_id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={"carrier": carrier, "vehicle_number": vehicle_number},
        db=db,
    )
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
