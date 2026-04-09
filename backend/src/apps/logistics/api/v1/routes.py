from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.commerce.models import Address
from src.apps.core.storage import save_media_bytes
from src.apps.core.time import utc_now
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.logistics.planner import (
    LockedAssignment,
    PlannerInput,
    RouteDefinition,
    VehicleCapacity,
    run_line_haul_optimizer,
)
from src.apps.logistics.models import (
    Branch,
    BranchInventoryMovement,
    CourierLocationPing,
    DeliveryAgent,
    DeliveryAgentStatus,
    DeliveryException,
    DeliveryZone,
    Hub,
    HubOperationEvent,
    HubSortItemStatus,
    HubSortQueue,
    HubSortQueueItem,
    HubSortQueueStatus,
    HubType,
    LineHaulTrip,
    PickupJob,
    ReversePickupJob,
    RouteOptimizationPlan,
    ShipmentProof,
    ShipmentManifest,
    ShipmentManifestStatus,
    ShippingOption,
)
from src.apps.logistics.services import (
    append_hub_operation_event,
    arrive_line_haul_trip,
    assign_pickup_job,
    assign_reverse_pickup,
    complete_pickup_job,
    complete_reverse_pickup,
    create_delivery_exception,
    create_hub_sort_queue,
    create_shipment_proof,
    create_pickup_job_for_vendor_order,
    create_reverse_pickup,
    get_manifest_or_404,
    get_hub_sort_queue_or_404,
    get_route_plan,
    get_pickup_job_or_404,
    get_trip_or_404,
    ingest_courier_location_ping,
    optimize_manifest_route,
    initiate_rto_for_exception,
    quote_shipping,
    record_branch_inventory_movement,
    reschedule_delivery_exception,
    close_hub_sort_queue,
    start_line_haul_trip,
    update_shipment_tracking,
)
from src.apps.orders.models import Order, OrderStatus, ReturnRequest, ReturnStatus, Shipment, ShipmentTracking, VendorOrder
from src.apps.notification.services.commerce_events import notify_delivery_exception, notify_order_event, notify_return_event
from src.apps.orders.services import update_return_request_status
from src.apps.vendors.services import get_vendor_for_user

router = APIRouter()


class DeliveryZoneCreateRequest(BaseModel):
    name: str
    code: str
    state: str = ""
    city: str = ""
    pincodes: list[str] = []
    cod_enabled: bool = True
    shipping_rate: float = Field(default=0, ge=0)


class HubCreateRequest(BaseModel):
    name: str
    code: str
    address: str = ""
    city: str = ""
    state: str = ""
    hub_type: HubType = HubType.LOCAL


class BranchCreateRequest(BaseModel):
    hub_id: str
    zone_id: str | None = None
    name: str
    code: str
    address: str = ""
    city: str = ""
    state: str = ""
    contact_phone: str = ""


class AgentCreateRequest(BaseModel):
    branch_id: str
    name: str
    phone: str = ""
    capacity: int = Field(default=20, ge=0)


class ManifestCreateRequest(BaseModel):
    code: str
    origin_hub_id: str | None = None
    destination_hub_id: str | None = None
    branch_id: str | None = None
    shipment_ids: list[str] = []


class TripCreateRequest(BaseModel):
    manifest_id: str
    vehicle_number: str = ""
    driver_name: str = ""
    driver_phone: str = ""


class AssignPickupRequest(BaseModel):
    agent_id: str


class ShipmentStatusRequest(BaseModel):
    status: OrderStatus
    location: str = ""
    remarks: str = ""


class ShippingOptionCreateRequest(BaseModel):
    zone_id: str | None = None
    name: str
    code: str
    rate: float = Field(default=0, ge=0)
    cod_enabled: bool = True
    estimated_days: int = Field(default=3, ge=0)


class ShipmentProofRequest(BaseModel):
    agent_id: str | None = None
    proof_type: str = "otp"
    otp_code: str = ""
    photo_url: str = ""
    signature_url: str = ""
    notes: str = ""


class DeliveryExceptionCreateRequest(BaseModel):
    exception_type: str = Field(default="failed_delivery", min_length=3, max_length=80)
    failure_reason: str = Field(default="", max_length=255)
    notes: str = ""
    agent_id: str | None = None
    rescheduled_for: datetime | None = None


class DeliveryExceptionRescheduleRequest(BaseModel):
    rescheduled_for: datetime


class BranchInventoryMovementCreateRequest(BaseModel):
    branch_id: str
    shipment_id: str | None = None
    variant_id: str | None = None
    movement_type: str = Field(min_length=3, max_length=40)
    quantity: int
    notes: str = ""


class RouteOptimizationRequest(BaseModel):
    average_speed_kph: float = Field(default=28, gt=0)
    service_minutes_per_stop: int = Field(default=8, ge=1)


class PlannerRouteInput(BaseModel):
    route_id: str = Field(min_length=2, max_length=80)
    origin_hub: str = Field(min_length=2, max_length=40)
    destination_hub: str = Field(min_length=2, max_length=40)
    demand_units: int = Field(ge=0)


class PlannerVehicleInput(BaseModel):
    vehicle_id: str = Field(min_length=2, max_length=80)
    hub_code: str = Field(min_length=2, max_length=40)
    capacity_units: int = Field(ge=0)


class PlannerLockedAssignmentInput(BaseModel):
    route_id: str
    vehicle_id: str
    lock_units: int | None = Field(default=None, ge=0)
    override_units: int | None = Field(default=None, ge=0)


class LineHaulPlannerRunRequest(BaseModel):
    routes: list[PlannerRouteInput]
    vehicles: list[PlannerVehicleInput]
    connectivity: dict[str, list[str]] = Field(default_factory=dict)
    locked_assignments: list[PlannerLockedAssignmentInput] = Field(default_factory=list)
    random_seed: int = Field(default=7, ge=0)


class CourierGpsIngestionRequest(BaseModel):
    shipment_id: str | None = None
    agent_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kph: float | None = Field(default=None, ge=0)
    heading: float | None = Field(default=None, ge=0, le=360)
    accuracy_meters: float | None = Field(default=None, ge=0)
    source: str = Field(default="device", min_length=2, max_length=40)
    label: str = Field(default="", max_length=120)
    recorded_at: datetime | None = None


class HubSortQueueCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=64)
    manifest_id: str | None = None


class HubSortScanRequest(BaseModel):
    shipment_id: str
    scan_code: str = Field(default="inbound_scan", min_length=3, max_length=80)
    notes: str = ""


class HubSortAssignRequest(BaseModel):
    shipment_id: str
    next_hub_id: str | None = None
    carrier: str = Field(min_length=2, max_length=80)
    vehicle_number: str = Field(min_length=2, max_length=64)


class HubBulkMoveNextLegRequest(BaseModel):
    shipment_ids: list[str] = Field(default_factory=list, min_length=1)
    carrier: str = Field(min_length=2, max_length=80)
    vehicle_number: str = Field(min_length=2, max_length=64)
    carrier_ready: bool = True
    vehicle_ready: bool = True


class HubBulkScanRequest(BaseModel):
    shipment_ids: list[str] = Field(default_factory=list, min_length=1)
    scan_code: str = Field(default="inbound_scan", min_length=3, max_length=80)
    notes: str = ""


class HubBulkAssignRequest(BaseModel):
    shipment_ids: list[str] = Field(default_factory=list, min_length=1)
    next_hub_id: str | None = None
    carrier: str = Field(min_length=2, max_length=80)
    vehicle_number: str = Field(min_length=2, max_length=64)


def _serialize_sort_queue_item(item: HubSortQueueItem) -> dict[str, object]:
    return {
        "queue_item_id": encode_id(item.id or 0),
        "shipment_id": encode_id(item.shipment_id),
        "status": item.status.value,
        "scan_count": item.scan_count,
        "assigned_next_hub_id": encode_id(item.assigned_next_hub_id) if item.assigned_next_hub_id else None,
        "assigned_carrier": item.assigned_carrier,
        "assigned_vehicle_number": item.assigned_vehicle_number,
        "exception_code": item.exception_code or None,
        "exception_notes": item.exception_notes or None,
        "scanned_at": item.scanned_at.isoformat(),
        "assigned_at": item.assigned_at.isoformat() if item.assigned_at else None,
        "moved_at": item.moved_at.isoformat() if item.moved_at else None,
        "updated_at": item.updated_at.isoformat(),
    }


def _serialize_route_plan(plan: RouteOptimizationPlan) -> dict[str, object]:
    return {
        "plan_id": encode_id(plan.id or 0),
        "manifest_id": encode_id(plan.manifest_id) if plan.manifest_id else None,
        "trip_id": encode_id(plan.trip_id) if plan.trip_id else None,
        "strategy": plan.strategy,
        "total_distance_km": plan.total_distance_km,
        "estimated_duration_minutes": plan.estimated_duration_minutes,
        "routed_stop_count": plan.routed_stop_count,
        "unroutable_stop_count": plan.unroutable_stop_count,
        "score": plan.score,
        "stops": json.loads(plan.stops_json or "[]"),
        "metrics": json.loads(plan.metrics_json or "{}"),
        "updated_at": plan.updated_at.isoformat(),
    }


def _shipment_ids_in_manifest(manifest: ShipmentManifest) -> set[int]:
    return {int(shipment_id) for shipment_id in json.loads(manifest.shipment_ids_json or "[]")}


async def _find_expected_hub_for_shipment(shipment_id: int, db: AsyncSession) -> int | None:
    manifests = (
        await db.execute(
            select(ShipmentManifest).where(ShipmentManifest.destination_hub_id != None)  # noqa: E711
        )
    ).scalars().all()
    for manifest in manifests:
        if shipment_id in _shipment_ids_in_manifest(manifest):
            return manifest.destination_hub_id
    return None


async def _ensure_sort_action_allowed(queue: HubSortQueue, db: AsyncSession) -> None:
    if queue.status == HubSortQueueStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manifest closed during sort action")
    if queue.manifest_id:
        manifest = await db.get(ShipmentManifest, queue.manifest_id)
        if manifest and manifest.status == ShipmentManifestStatus.RECONCILED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manifest closed during sort action")


def _build_label_payload(
    *,
    shipment: Shipment,
    vendor_order: VendorOrder | None,
    address: Address | None,
) -> dict[str, object]:
    destination = {
        "name": address.name if address else "",
        "phone": address.phone if address else "",
        "line1": address.line1 if address else "",
        "line2": address.line2 if address else "",
        "city": address.city if address else "",
        "state": address.state if address else "",
        "pincode": address.pincode if address else "",
        "country": address.country if address else "",
    }
    return {
        "awb": shipment.awb,
        "shipment_id": encode_id(shipment.id or 0),
        "vendor_order_id": encode_id(shipment.vendor_order_id) if shipment.vendor_order_id else None,
        "vendor_order_number": vendor_order.vendor_order_number if vendor_order else "",
        "shipment_status": shipment.status.value,
        "current_location": shipment.current_location,
        "generated_at": utc_now().isoformat(),
        "destination_address": destination,
    }


async def _ensure_shipping_label(
    *,
    shipment: Shipment,
    db: AsyncSession,
    force: bool = False,
) -> dict[str, object]:
    vendor_order = await db.get(VendorOrder, shipment.vendor_order_id) if shipment.vendor_order_id else None
    parent_order = await db.get(Order, shipment.order_id)
    address = await db.get(Address, parent_order.address_id) if parent_order else None
    existing_payload = json.loads(shipment.label_payload_json or "{}")
    if shipment.label_url and shipment.label_generated_at and existing_payload and not force:
        return {
            "url": shipment.label_url,
            "generated_at": shipment.label_generated_at.isoformat(),
            "payload": existing_payload,
        }

    payload = _build_label_payload(shipment=shipment, vendor_order=vendor_order, address=address)
    label_text = "\n".join(
        [
            "Platform Shipping Label",
            f"AWB: {payload['awb']}",
            f"Shipment ID: {payload['shipment_id']}",
            f"Vendor Order: {payload['vendor_order_number'] or '-'}",
            f"Status: {payload['shipment_status']}",
            f"Destination: {payload['destination_address']['name']}",
            f"Phone: {payload['destination_address']['phone']}",
            f"Address: {payload['destination_address']['line1']} {payload['destination_address']['line2']}".strip(),
            f"City/State: {payload['destination_address']['city']}, {payload['destination_address']['state']}",
            f"Pincode: {payload['destination_address']['pincode']}",
            f"Generated At: {payload['generated_at']}",
        ]
    )
    relative_path = str(Path("shipping-labels") / f"{shipment.awb.lower()}.txt")
    shipment.label_url = save_media_bytes(relative_path, label_text.encode("utf-8"), content_type="text/plain")
    shipment.label_payload_json = json.dumps(payload)
    shipment.label_generated_at = utc_now()
    shipment.updated_at = utc_now()
    await db.commit()
    await db.refresh(shipment)
    return {
        "url": shipment.label_url,
        "generated_at": shipment.label_generated_at.isoformat() if shipment.label_generated_at else None,
        "payload": payload,
    }


async def _notify_customer_for_shipment_status(
    *,
    shipment: Shipment,
    db: AsyncSession,
    title: str,
    body: str,
) -> None:
    order = await db.get(Order, shipment.order_id)
    if order is None:
        return
    await notify_order_event(
        db=db,
        user_id=order.user_id,
        order_id=encode_id(order.id or 0),
        order_number=order.order_number,
        event=f"order.{shipment.status.value}",
        title=title,
        body=body,
        status=shipment.status.value,
        payment_status=order.payment_status.value,
    )


@router.get("/logistics/serviceability")
async def get_serviceability(
    pincode: str = Query(...),
    cod: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    return await quote_shipping(pincode, cod, db)


@router.post("/logistics/zones", status_code=status.HTTP_201_CREATED)
async def create_zone(
    payload: DeliveryZoneCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    zone = DeliveryZone(
        name=payload.name,
        code=payload.code,
        state=payload.state,
        city=payload.city,
        pincodes_json=json.dumps(payload.pincodes),
        cod_enabled=payload.cod_enabled,
        shipping_rate=payload.shipping_rate,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return {"zone_id": encode_id(zone.id or 0)}


@router.post("/logistics/shipping-options", status_code=status.HTTP_201_CREATED)
async def create_shipping_option(
    payload: ShippingOptionCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    option = ShippingOption(
        zone_id=decode_id_or_404(payload.zone_id) if payload.zone_id else None,
        name=payload.name,
        code=payload.code,
        rate=payload.rate,
        cod_enabled=payload.cod_enabled,
        estimated_days=payload.estimated_days,
    )
    db.add(option)
    await db.commit()
    await db.refresh(option)
    return {"shipping_option_id": encode_id(option.id or 0)}


@router.get("/logistics/zones")
async def list_zones(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    zones = (await db.execute(select(DeliveryZone).order_by(DeliveryZone.created_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(zone.id or 0),
                "name": zone.name,
                "code": zone.code,
                "pincodes": json.loads(zone.pincodes_json or "[]"),
                "shipping_rate": zone.shipping_rate,
                "cod_enabled": zone.cod_enabled,
            }
            for zone in zones
        ],
        "total": len(zones),
    }


@router.get("/logistics/shipping-options")
async def list_shipping_options(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    options = (await db.execute(select(ShippingOption).order_by(ShippingOption.created_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(option.id or 0),
                "zone_id": encode_id(option.zone_id) if option.zone_id else None,
                "name": option.name,
                "code": option.code,
                "rate": option.rate,
                "cod_enabled": option.cod_enabled,
                "estimated_days": option.estimated_days,
            }
            for option in options
        ],
        "total": len(options),
    }


@router.post("/logistics/hubs", status_code=status.HTTP_201_CREATED)
async def create_hub(
    payload: HubCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    hub = Hub(**payload.model_dump())
    db.add(hub)
    await db.commit()
    await db.refresh(hub)
    return {"hub_id": encode_id(hub.id or 0)}


@router.get("/logistics/hubs")
async def list_hubs(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    hubs = (await db.execute(select(Hub).order_by(Hub.created_at.desc()))).scalars().all()
    return {"items": [{"id": encode_id(hub.id or 0), "name": hub.name, "code": hub.code, "city": hub.city} for hub in hubs], "total": len(hubs)}


@router.post("/logistics/hubs/{hub_id}/sort-queues", status_code=status.HTTP_201_CREATED)
async def create_hub_queue(
    hub_id: str,
    payload: HubSortQueueCreateRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    hub = await db.get(Hub, decoded_hub_id)
    if hub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hub not found")
    decoded_manifest_id = decode_id_or_404(payload.manifest_id) if payload.manifest_id else None
    if decoded_manifest_id:
        manifest = await get_manifest_or_404(decoded_manifest_id, db)
        if manifest.status == ShipmentManifestStatus.RECONCILED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manifest is closed")
    queue = await create_hub_sort_queue(
        hub_id=decoded_hub_id,
        code=payload.code,
        manifest_id=decoded_manifest_id,
        actor_id=current_user.id,
        db=db,
    )
    await db.commit()
    return {"queue_id": encode_id(queue.id or 0), "status": queue.status.value}


@router.post("/logistics/hubs/{hub_id}/sort-queues/{queue_id}/scan")
async def scan_hub_sort_item(
    hub_id: str,
    queue_id: str,
    payload: HubSortScanRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue = await get_hub_sort_queue_or_404(decode_id_or_404(queue_id), db)
    if queue.hub_id != decoded_hub_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue does not belong to hub")
    await _ensure_sort_action_allowed(queue, db)
    shipment = await db.get(Shipment, decode_id_or_404(payload.shipment_id))
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    existing_item = (
        await db.execute(
            select(HubSortQueueItem).where(
                HubSortQueueItem.queue_id == queue.id,
                HubSortQueueItem.shipment_id == shipment.id,
            )
        )
    ).scalars().first()
    if existing_item is not None:
        existing_item.scan_count += 1
        existing_item.exception_code = "duplicate_scan"
        existing_item.exception_notes = "Duplicate scan received for shipment in same queue."
        existing_item.status = HubSortItemStatus.EXCEPTION
        existing_item.updated_at = utc_now()
        await append_hub_operation_event(
            hub_id=decoded_hub_id,
            operation_type="duplicate_scan_detected",
            queue_id=queue.id,
            queue_item_id=existing_item.id,
            shipment_id=shipment.id,
            manifest_id=queue.manifest_id,
            actor_type="admin",
            actor_id=current_user.id,
            payload={"scan_code": payload.scan_code},
            db=db,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate scan")

    expected_hub_id = await _find_expected_hub_for_shipment(shipment.id or 0, db)
    item_status = HubSortItemStatus.SCANNED
    exception_code = ""
    exception_notes = ""
    if expected_hub_id and expected_hub_id != decoded_hub_id:
        item_status = HubSortItemStatus.EXCEPTION
        exception_code = "wrong_hub_scan"
        exception_notes = f"Shipment expected at hub {encode_id(expected_hub_id)}"

    item = HubSortQueueItem(
        queue_id=queue.id or 0,
        shipment_id=shipment.id or 0,
        status=item_status,
        exception_code=exception_code,
        exception_notes=exception_notes,
    )
    db.add(item)
    await db.flush()
    await append_hub_operation_event(
        hub_id=decoded_hub_id,
        operation_type="hub_scan_recorded" if item_status == HubSortItemStatus.SCANNED else "wrong_hub_scan_detected",
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=shipment.id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=current_user.id,
        payload={"scan_code": payload.scan_code, "notes": payload.notes},
        db=db,
    )
    await db.commit()
    return {"queue_item_id": encode_id(item.id or 0), "status": item.status.value, "exception_code": item.exception_code or None}


@router.post("/logistics/hubs/{hub_id}/sort-queues/{queue_id}/assign")
async def assign_hub_sort_item(
    hub_id: str,
    queue_id: str,
    payload: HubSortAssignRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue = await get_hub_sort_queue_or_404(decode_id_or_404(queue_id), db)
    if queue.hub_id != decoded_hub_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue does not belong to hub")
    await _ensure_sort_action_allowed(queue, db)
    decoded_shipment_id = decode_id_or_404(payload.shipment_id)
    item = (
        await db.execute(
            select(HubSortQueueItem).where(HubSortQueueItem.queue_id == queue.id, HubSortQueueItem.shipment_id == decoded_shipment_id)
        )
    ).scalars().first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment scan not found in queue")
    if item.status == HubSortItemStatus.EXCEPTION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot assign shipment with unresolved exception")
    item.status = HubSortItemStatus.ASSIGNED
    item.assigned_next_hub_id = decode_id_or_404(payload.next_hub_id) if payload.next_hub_id else None
    item.assigned_carrier = payload.carrier
    item.assigned_vehicle_number = payload.vehicle_number
    item.assigned_at = utc_now()
    item.updated_at = utc_now()
    await append_hub_operation_event(
        hub_id=decoded_hub_id,
        operation_type="next_leg_assigned",
        queue_id=queue.id,
        queue_item_id=item.id,
        shipment_id=item.shipment_id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=current_user.id,
        payload={"carrier": payload.carrier, "vehicle_number": payload.vehicle_number},
        db=db,
    )
    await db.commit()
    return {"success": True}


@router.post("/logistics/hubs/{hub_id}/sort-queues/{queue_id}/bulk-scan")
async def bulk_scan_hub_sort_items(
    hub_id: str,
    queue_id: str,
    payload: HubBulkScanRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue = await get_hub_sort_queue_or_404(decode_id_or_404(queue_id), db)
    if queue.hub_id != decoded_hub_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue does not belong to hub")
    await _ensure_sort_action_allowed(queue, db)

    scanned_count = 0
    duplicate_count = 0
    exception_count = 0
    items: list[dict[str, object]] = []
    for shipment_id in payload.shipment_ids:
        try:
            scan_result = await scan_hub_sort_item(
                hub_id=hub_id,
                queue_id=queue_id,
                payload=HubSortScanRequest(shipment_id=shipment_id, scan_code=payload.scan_code, notes=payload.notes),
                current_user=current_user,
                db=db,
            )
            scanned_count += 1
            if scan_result.get("status") == HubSortItemStatus.EXCEPTION.value:
                exception_count += 1
            items.append(scan_result)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_409_CONFLICT or exc.detail != "Duplicate scan":
                raise
            duplicate_count += 1
            decoded_shipment_id = decode_id_or_404(shipment_id)
            existing = (
                await db.execute(
                    select(HubSortQueueItem).where(
                        HubSortQueueItem.queue_id == queue.id,
                        HubSortQueueItem.shipment_id == decoded_shipment_id,
                    )
                )
            ).scalars().first()
            if existing is not None:
                items.append(_serialize_sort_queue_item(existing))
    await append_hub_operation_event(
        hub_id=decoded_hub_id,
        operation_type="bulk_scan_completed",
        queue_id=queue.id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=current_user.id,
        payload={
            "scan_code": payload.scan_code,
            "requested_count": len(payload.shipment_ids),
            "scanned_count": scanned_count,
            "duplicate_count": duplicate_count,
            "exception_count": exception_count,
        },
        db=db,
    )
    await db.commit()
    return {
        "requested_count": len(payload.shipment_ids),
        "scanned_count": scanned_count,
        "duplicate_count": duplicate_count,
        "exception_count": exception_count,
        "items": items,
    }


@router.post("/logistics/hubs/{hub_id}/sort-queues/{queue_id}/bulk-assign")
async def bulk_assign_hub_sort_items(
    hub_id: str,
    queue_id: str,
    payload: HubBulkAssignRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue = await get_hub_sort_queue_or_404(decode_id_or_404(queue_id), db)
    if queue.hub_id != decoded_hub_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue does not belong to hub")
    await _ensure_sort_action_allowed(queue, db)
    decoded_shipment_ids = [decode_id_or_404(shipment_id) for shipment_id in payload.shipment_ids]
    items = (
        await db.execute(
            select(HubSortQueueItem).where(HubSortQueueItem.queue_id == queue.id, HubSortQueueItem.shipment_id.in_(decoded_shipment_ids))
        )
    ).scalars().all()
    found_by_shipment_id = {item.shipment_id: item for item in items}
    if len(found_by_shipment_id) != len(decoded_shipment_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some shipments are missing in queue")

    assigned_count = 0
    idempotent_skip_count = 0
    decoded_next_hub_id = decode_id_or_404(payload.next_hub_id) if payload.next_hub_id else None
    for shipment_id in decoded_shipment_ids:
        item = found_by_shipment_id[shipment_id]
        if item.status == HubSortItemStatus.EXCEPTION:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot assign shipment with unresolved exception")
        same_assignment = (
            item.status in {HubSortItemStatus.ASSIGNED, HubSortItemStatus.MOVED_TO_NEXT_LEG}
            and item.assigned_next_hub_id == decoded_next_hub_id
            and item.assigned_carrier == payload.carrier
            and item.assigned_vehicle_number == payload.vehicle_number
        )
        if same_assignment:
            idempotent_skip_count += 1
            continue
        item.status = HubSortItemStatus.ASSIGNED
        item.assigned_next_hub_id = decoded_next_hub_id
        item.assigned_carrier = payload.carrier
        item.assigned_vehicle_number = payload.vehicle_number
        item.assigned_at = utc_now()
        item.updated_at = utc_now()
        assigned_count += 1
        await append_hub_operation_event(
            hub_id=decoded_hub_id,
            operation_type="next_leg_assigned",
            queue_id=queue.id,
            queue_item_id=item.id,
            shipment_id=item.shipment_id,
            manifest_id=queue.manifest_id,
            actor_type="admin",
            actor_id=current_user.id,
            payload={"carrier": payload.carrier, "vehicle_number": payload.vehicle_number, "bulk_operation": True},
            db=db,
        )
    await append_hub_operation_event(
        hub_id=decoded_hub_id,
        operation_type="bulk_assign_completed",
        queue_id=queue.id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=current_user.id,
        payload={
            "requested_count": len(payload.shipment_ids),
            "assigned_count": assigned_count,
            "idempotent_skip_count": idempotent_skip_count,
        },
        db=db,
    )
    await db.commit()
    return {"requested_count": len(payload.shipment_ids), "assigned_count": assigned_count, "idempotent_skip_count": idempotent_skip_count}


@router.post("/logistics/hubs/{hub_id}/sort-queues/{queue_id}/bulk-move-next-leg")
async def bulk_move_to_next_leg(
    hub_id: str,
    queue_id: str,
    payload: HubBulkMoveNextLegRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue = await get_hub_sort_queue_or_404(decode_id_or_404(queue_id), db)
    if queue.hub_id != decoded_hub_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue does not belong to hub")
    await _ensure_sort_action_allowed(queue, db)
    if not payload.carrier_ready or not payload.vehicle_ready:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Carrier/vehicle readiness validation failed")

    shipment_ids = [decode_id_or_404(shipment_id) for shipment_id in payload.shipment_ids]
    items = (
        await db.execute(
            select(HubSortQueueItem).where(HubSortQueueItem.queue_id == queue.id, HubSortQueueItem.shipment_id.in_(shipment_ids))
        )
    ).scalars().all()
    if len(items) != len(shipment_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some shipments are missing in queue")

    moved = 0
    already_moved = 0
    for item in items:
        if item.status == HubSortItemStatus.MOVED_TO_NEXT_LEG:
            already_moved += 1
            continue
        if item.status != HubSortItemStatus.ASSIGNED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="All shipments must be assigned before bulk move")
        if item.assigned_carrier != payload.carrier or item.assigned_vehicle_number != payload.vehicle_number:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assigned carrier/vehicle mismatch")
        item.status = HubSortItemStatus.MOVED_TO_NEXT_LEG
        item.moved_at = utc_now()
        item.updated_at = utc_now()
        shipment = await db.get(Shipment, item.shipment_id)
        if shipment:
            shipment.current_location = f"Departed {hub_id} via {payload.carrier} / {payload.vehicle_number}"
            shipment.updated_at = utc_now()
        await append_hub_operation_event(
            hub_id=decoded_hub_id,
            operation_type="moved_to_next_leg",
            queue_id=queue.id,
            queue_item_id=item.id,
            shipment_id=item.shipment_id,
            manifest_id=queue.manifest_id,
            actor_type="admin",
            actor_id=current_user.id,
            payload={"carrier": payload.carrier, "vehicle_number": payload.vehicle_number},
            db=db,
        )
        moved += 1
    await append_hub_operation_event(
        hub_id=decoded_hub_id,
        operation_type="bulk_dispatch_completed",
        queue_id=queue.id,
        manifest_id=queue.manifest_id,
        actor_type="admin",
        actor_id=current_user.id,
        payload={
            "requested_count": len(payload.shipment_ids),
            "moved_count": moved,
            "already_moved_count": already_moved,
            "carrier": payload.carrier,
            "vehicle_number": payload.vehicle_number,
        },
        db=db,
    )
    await db.commit()
    return {"moved_count": moved, "already_moved_count": already_moved}


@router.post("/logistics/hubs/{hub_id}/sort-queues/{queue_id}/close")
async def close_hub_queue(
    hub_id: str,
    queue_id: str,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue = await get_hub_sort_queue_or_404(decode_id_or_404(queue_id), db)
    if queue.hub_id != decoded_hub_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue does not belong to hub")
    await close_hub_sort_queue(queue, actor_id=current_user.id, db=db)
    await db.commit()
    return {"status": queue.status.value}


@router.get("/logistics/hubs/{hub_id}/sort-workbench")
async def get_hub_sort_workbench(
    hub_id: str,
    queue_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queue_filter_id = decode_id_or_404(queue_id) if queue_id else None
    queue_query = select(HubSortQueue).where(HubSortQueue.hub_id == decoded_hub_id)
    if queue_filter_id:
        queue_query = queue_query.where(HubSortQueue.id == queue_filter_id)
    queues = (await db.execute(queue_query.order_by(HubSortQueue.created_at.desc()))).scalars().all()
    selected_queue = queues[0] if queues else None
    if queue_filter_id and (selected_queue is None or selected_queue.id != queue_filter_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sort queue not found")

    queue_items: list[HubSortQueueItem] = []
    if selected_queue is not None and selected_queue.id is not None:
        queue_items = (
            await db.execute(select(HubSortQueueItem).where(HubSortQueueItem.queue_id == selected_queue.id).order_by(HubSortQueueItem.updated_at.desc()))
        ).scalars().all()
    inbound_items = [item for item in queue_items if item.status in {HubSortItemStatus.SCANNED, HubSortItemStatus.EXCEPTION}]
    outbound_items = [item for item in queue_items if item.status in {HubSortItemStatus.ASSIGNED, HubSortItemStatus.MOVED_TO_NEXT_LEG}]
    timeline_events = (
        await db.execute(
            select(HubOperationEvent)
            .where(HubOperationEvent.hub_id == decoded_hub_id)
            .order_by(HubOperationEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "hub_id": hub_id,
        "selected_queue_id": encode_id(selected_queue.id or 0) if selected_queue and selected_queue.id else None,
        "queues": [
            {
                "queue_id": encode_id(queue.id or 0),
                "code": queue.code,
                "status": queue.status.value,
                "manifest_id": encode_id(queue.manifest_id) if queue.manifest_id else None,
                "created_at": queue.created_at.isoformat(),
                "closed_at": queue.closed_at.isoformat() if queue.closed_at else None,
            }
            for queue in queues
        ],
        "inbound_items": [_serialize_sort_queue_item(item) for item in inbound_items],
        "outbound_items": [_serialize_sort_queue_item(item) for item in outbound_items],
        "timeline": [
            {
                "event_id": encode_id(event.id or 0),
                "queue_id": encode_id(event.queue_id) if event.queue_id else None,
                "queue_item_id": encode_id(event.queue_item_id) if event.queue_item_id else None,
                "shipment_id": encode_id(event.shipment_id) if event.shipment_id else None,
                "operation_type": event.operation_type,
                "payload": json.loads(event.payload_json or "{}"),
                "created_at": event.created_at.isoformat(),
            }
            for event in timeline_events
        ],
    }


@router.post("/logistics/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    branch = Branch(
        hub_id=decode_id_or_404(payload.hub_id),
        zone_id=decode_id_or_404(payload.zone_id) if payload.zone_id else None,
        name=payload.name,
        code=payload.code,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        contact_phone=payload.contact_phone,
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return {"branch_id": encode_id(branch.id or 0)}


@router.get("/logistics/branches")
async def list_branches(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    branches = (await db.execute(select(Branch).order_by(Branch.created_at.desc()))).scalars().all()
    return {"items": [{"id": encode_id(branch.id or 0), "name": branch.name, "code": branch.code, "city": branch.city} for branch in branches], "total": len(branches)}


@router.post("/logistics/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    agent = DeliveryAgent(
        branch_id=decode_id_or_404(payload.branch_id),
        name=payload.name,
        phone=payload.phone,
        capacity=payload.capacity,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return {"agent_id": encode_id(agent.id or 0)}


@router.get("/logistics/agents")
async def list_agents(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    agents = (await db.execute(select(DeliveryAgent).order_by(DeliveryAgent.created_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(agent.id or 0),
                "branch_id": encode_id(agent.branch_id),
                "name": agent.name,
                "phone": agent.phone,
                "status": agent.status.value,
                "capacity": agent.capacity,
                "current_load": agent.current_load,
            }
            for agent in agents
        ],
        "total": len(agents),
    }


@router.get("/logistics/agents/availability")
async def get_agent_availability(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    agents = (await db.execute(select(DeliveryAgent))).scalars().all()
    status_counts = {status.value: 0 for status in DeliveryAgentStatus}
    for agent in agents:
        status_counts[agent.status.value] += 1
    return {
        "total_agents": len(agents),
        "status_counts": status_counts,
        "available_capacity": sum(max(agent.capacity - agent.current_load, 0) for agent in agents if agent.status == DeliveryAgentStatus.AVAILABLE),
    }


@router.post("/logistics/manifests", status_code=status.HTTP_201_CREATED)
async def create_manifest(
    payload: ManifestCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    manifest = ShipmentManifest(
        code=payload.code,
        origin_hub_id=decode_id_or_404(payload.origin_hub_id) if payload.origin_hub_id else None,
        destination_hub_id=decode_id_or_404(payload.destination_hub_id) if payload.destination_hub_id else None,
        branch_id=decode_id_or_404(payload.branch_id) if payload.branch_id else None,
        shipment_ids_json=json.dumps([decode_id_or_404(shipment_id) for shipment_id in payload.shipment_ids]),
    )
    db.add(manifest)
    await db.commit()
    await db.refresh(manifest)
    return {"manifest_id": encode_id(manifest.id or 0)}


@router.post("/logistics/trips", status_code=status.HTTP_201_CREATED)
async def create_trip(
    payload: TripCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    trip = LineHaulTrip(
        manifest_id=decode_id_or_404(payload.manifest_id),
        vehicle_number=payload.vehicle_number,
        driver_name=payload.driver_name,
        driver_phone=payload.driver_phone,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return {"trip_id": encode_id(trip.id or 0)}


@router.post("/logistics/trips/{trip_id}/dispatch")
async def dispatch_trip(
    trip_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    trip = await get_trip_or_404(decode_id_or_404(trip_id), db)
    await start_line_haul_trip(trip, db)
    await db.commit()
    return {"success": True}


@router.post("/logistics/trips/{trip_id}/arrive")
async def arrive_trip(
    trip_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    trip = await get_trip_or_404(decode_id_or_404(trip_id), db)
    await arrive_line_haul_trip(trip, db)
    await db.commit()
    return {"success": True}


@router.post("/logistics/manifests/{manifest_id}/optimize-route")
async def optimize_manifest(
    manifest_id: str,
    payload: RouteOptimizationRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    manifest = await get_manifest_or_404(decode_id_or_404(manifest_id), db)
    plan = await optimize_manifest_route(
        manifest=manifest,
        db=db,
        average_speed_kph=payload.average_speed_kph,
        service_minutes_per_stop=payload.service_minutes_per_stop,
    )
    await db.commit()
    return _serialize_route_plan(plan)


@router.get("/logistics/manifests/{manifest_id}/route-plan")
async def get_manifest_route_plan(
    manifest_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await get_route_plan(manifest_id=decode_id_or_404(manifest_id), db=db)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route plan not found")
    return _serialize_route_plan(plan)


@router.post("/logistics/trips/{trip_id}/optimize-route")
async def optimize_trip_route(
    trip_id: str,
    payload: RouteOptimizationRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    trip = await get_trip_or_404(decode_id_or_404(trip_id), db)
    manifest = await get_manifest_or_404(trip.manifest_id, db)
    plan = await optimize_manifest_route(
        manifest=manifest,
        trip=trip,
        db=db,
        average_speed_kph=payload.average_speed_kph,
        service_minutes_per_stop=payload.service_minutes_per_stop,
    )
    await db.commit()
    return _serialize_route_plan(plan)


@router.get("/logistics/trips/{trip_id}/route-plan")
async def get_trip_route_plan(
    trip_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await get_route_plan(trip_id=decode_id_or_404(trip_id), db=db)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route plan not found")
    return _serialize_route_plan(plan)


@router.post("/logistics/line-haul-planner/run")
async def run_line_haul_planner(
    payload: LineHaulPlannerRunRequest,
    _: User = Depends(get_current_active_superuser),
):
    result = run_line_haul_optimizer(
        PlannerInput(
            routes=[
                RouteDefinition(
                    route_id=route.route_id,
                    origin_hub=route.origin_hub,
                    destination_hub=route.destination_hub,
                    demand_units=route.demand_units,
                )
                for route in payload.routes
            ],
            vehicles=[
                VehicleCapacity(
                    vehicle_id=vehicle.vehicle_id,
                    hub_code=vehicle.hub_code,
                    capacity_units=vehicle.capacity_units,
                )
                for vehicle in payload.vehicles
            ],
            connectivity=payload.connectivity,
            locked_assignments=[
                LockedAssignment(
                    route_id=assignment.route_id,
                    vehicle_id=assignment.vehicle_id,
                    lock_units=assignment.lock_units,
                    override_units=assignment.override_units,
                )
                for assignment in payload.locked_assignments
            ],
            random_seed=payload.random_seed,
        )
    )
    return {
        "assignments": [
            {
                "route_id": assignment.route_id,
                "vehicle_id": assignment.vehicle_id,
                "assigned_units": assignment.assigned_units,
                "locked": assignment.locked,
                "overridden": assignment.overridden,
            }
            for assignment in result.assignments
        ],
        "unassigned_routes": result.unassigned_routes,
        "metadata": result.metadata,
    }


@router.post("/logistics/trips/{trip_id}/gps", status_code=status.HTTP_201_CREATED)
async def ingest_trip_gps(
    trip_id: str,
    payload: CourierGpsIngestionRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    trip = await get_trip_or_404(decode_id_or_404(trip_id), db)
    ping = await ingest_courier_location_ping(
        trip=trip,
        latitude=payload.latitude,
        longitude=payload.longitude,
        shipment_id=decode_id_or_404(payload.shipment_id) if payload.shipment_id else None,
        agent_id=decode_id_or_404(payload.agent_id) if payload.agent_id else None,
        speed_kph=payload.speed_kph,
        heading=payload.heading,
        accuracy_meters=payload.accuracy_meters,
        source=payload.source,
        label=payload.label,
        recorded_at=payload.recorded_at,
        db=db,
    )
    await db.commit()
    return {
        "ping_id": encode_id(ping.id or 0),
        "trip_id": trip_id,
        "recorded_at": ping.recorded_at.isoformat(),
    }


@router.get("/logistics/trips/{trip_id}/gps")
async def list_trip_gps(
    trip_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_trip_id = decode_id_or_404(trip_id)
    pings = (
        await db.execute(
            select(CourierLocationPing)
            .where(CourierLocationPing.trip_id == decoded_trip_id)
            .order_by(CourierLocationPing.recorded_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "trip_id": trip_id,
        "items": [
            {
                "id": encode_id(ping.id or 0),
                "shipment_id": encode_id(ping.shipment_id) if ping.shipment_id else None,
                "agent_id": encode_id(ping.agent_id) if ping.agent_id else None,
                "latitude": ping.latitude,
                "longitude": ping.longitude,
                "speed_kph": ping.speed_kph,
                "heading": ping.heading,
                "accuracy_meters": ping.accuracy_meters,
                "source": ping.source,
                "label": ping.label,
                "recorded_at": ping.recorded_at.isoformat(),
            }
            for ping in pings
        ],
        "total": len(pings),
    }


@router.post("/vendor/orders/{vendor_order_id}/pickup-jobs", status_code=status.HTTP_201_CREATED)
async def create_pickup_job(
    vendor_order_id: str,
    branch_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    vendor_order = await db.get(VendorOrder, decode_id_or_404(vendor_order_id))
    if vendor_order is None or vendor_order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor order not found")
    shipment = (await db.execute(select(Shipment).where(Shipment.vendor_order_id == vendor_order.id))).scalars().first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    pickup_job = await create_pickup_job_for_vendor_order(vendor_order, shipment, decode_id_or_404(branch_id) if branch_id else None, db)
    await db.commit()
    return {"pickup_job_id": encode_id(pickup_job.id or 0)}


@router.post("/logistics/pickup-jobs/{pickup_job_id}/assign")
async def assign_pickup(
    pickup_job_id: str,
    payload: AssignPickupRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    pickup_job = await get_pickup_job_or_404(decode_id_or_404(pickup_job_id), db)
    agent = await db.get(DeliveryAgent, decode_id_or_404(payload.agent_id))
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    await assign_pickup_job(pickup_job, agent, db)
    await db.commit()
    return {"success": True}


@router.post("/logistics/pickup-jobs/{pickup_job_id}/complete")
async def complete_pickup(
    pickup_job_id: str,
    location: str = Query(default="Origin branch"),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    pickup_job = await get_pickup_job_or_404(decode_id_or_404(pickup_job_id), db)
    await complete_pickup_job(pickup_job, location, db)
    if pickup_job.branch_id:
        shipment = await db.get(Shipment, pickup_job.shipment_id)
        await record_branch_inventory_movement(
            branch_id=pickup_job.branch_id,
            shipment_id=pickup_job.shipment_id,
            variant_id=None,
            movement_type="inbound_pickup",
            quantity=1,
            notes=f"Shipment {shipment.awb if shipment else pickup_job.shipment_id} received from vendor",
            db=db,
        )
    await db.commit()
    return {"success": True}


@router.post("/returns/{return_request_id}/reverse-pickup", status_code=status.HTTP_201_CREATED)
async def create_return_pickup(
    return_request_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    return_request = await db.get(ReturnRequest, decode_id_or_404(return_request_id))
    if return_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    job = await create_reverse_pickup(return_request, db)
    await update_return_request_status(
        return_request=return_request,
        status_value=ReturnStatus.REVERSE_PICKUP_ASSIGNED,
        actor_user_id=None,
        message="Reverse pickup requested",
        payload={"job_id": job.id},
        db=db,
    )
    await db.commit()
    await notify_return_event(
        db=db,
        user_id=return_request.user_id,
        return_request_id=encode_id(return_request.id or 0),
        order_id=encode_id(return_request.order_id),
        event="return.reverse_pickup_assigned",
        title="Reverse pickup assigned",
        body="A reverse pickup has been created for your return.",
        status=return_request.status.value,
    )
    return {"reverse_pickup_job_id": encode_id(job.id or 0)}


@router.post("/logistics/reverse-pickups/{job_id}/assign")
async def assign_return_pickup(
    job_id: str,
    payload: AssignPickupRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(ReversePickupJob, decode_id_or_404(job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reverse pickup job not found")
    agent = await db.get(DeliveryAgent, decode_id_or_404(payload.agent_id))
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    await assign_reverse_pickup(job, agent, db)
    await db.commit()
    return {"success": True}


@router.post("/logistics/reverse-pickups/{job_id}/complete")
async def complete_return_pickup(
    job_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(ReversePickupJob, decode_id_or_404(job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reverse pickup job not found")
    await complete_reverse_pickup(job, db)
    return_request = await db.get(ReturnRequest, job.return_request_id)
    if return_request is not None:
        await update_return_request_status(
            return_request=return_request,
            status_value=ReturnStatus.PICKED_UP,
            actor_user_id=None,
            message="Return package picked up",
            payload={"job_id": job.id},
            db=db,
        )
    await db.commit()
    if return_request is not None:
        await notify_return_event(
            db=db,
            user_id=return_request.user_id,
            return_request_id=encode_id(return_request.id or 0),
            order_id=encode_id(return_request.order_id),
            event="return.picked_up",
            title="Return picked up",
            body="Your return package has been picked up.",
            status=return_request.status.value,
        )
    return {"success": True}


@router.post("/logistics/shipments/{shipment_id}/exceptions", status_code=status.HTTP_201_CREATED)
async def report_delivery_exception(
    shipment_id: str,
    payload: DeliveryExceptionCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    shipment = await db.get(Shipment, decode_id_or_404(shipment_id))
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    exception = await create_delivery_exception(
        shipment=shipment,
        exception_type=payload.exception_type,
        failure_reason=payload.failure_reason,
        notes=payload.notes,
        agent_id=decode_id_or_404(payload.agent_id) if payload.agent_id else None,
        rescheduled_for=payload.rescheduled_for,
        db=db,
    )
    await db.commit()
    order = await db.get(Order, shipment.order_id)
    if order is not None:
        await notify_delivery_exception(
            db=db,
            user_id=order.user_id,
            shipment_id=encode_id(shipment.id or 0),
            order_id=encode_id(order.id or 0),
            event="shipment.failed_delivery",
            title="Delivery attempt failed",
            body=payload.failure_reason or "We could not complete the delivery attempt.",
            status=exception.status.value,
        )
    return {"exception_id": encode_id(exception.id or 0)}


@router.post("/logistics/exceptions/{exception_id}/reschedule")
async def reschedule_exception(
    exception_id: str,
    payload: DeliveryExceptionRescheduleRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    exception = await db.get(DeliveryException, decode_id_or_404(exception_id))
    if exception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery exception not found")
    shipment = await db.get(Shipment, exception.shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    await reschedule_delivery_exception(exception, shipment, payload.rescheduled_for, db)
    await db.commit()
    order = await db.get(Order, shipment.order_id)
    if order is not None:
        await notify_delivery_exception(
            db=db,
            user_id=order.user_id,
            shipment_id=encode_id(shipment.id or 0),
            order_id=encode_id(order.id or 0),
            event="shipment.rescheduled",
            title="Delivery rescheduled",
            body=f"Your delivery has been rescheduled to {payload.rescheduled_for.isoformat()}",
            status=exception.status.value,
        )
    return {"success": True}


@router.post("/logistics/exceptions/{exception_id}/rto")
async def initiate_exception_rto(
    exception_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    exception = await db.get(DeliveryException, decode_id_or_404(exception_id))
    if exception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery exception not found")
    shipment = await db.get(Shipment, exception.shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    await initiate_rto_for_exception(exception, shipment, db)
    await db.commit()
    order = await db.get(Order, shipment.order_id)
    if order is not None:
        await notify_delivery_exception(
            db=db,
            user_id=order.user_id,
            shipment_id=encode_id(shipment.id or 0),
            order_id=encode_id(order.id or 0),
            event="shipment.rto_initiated",
            title="Return to origin initiated",
            body="The shipment is being returned to origin after a failed delivery.",
            status=exception.status.value,
        )
    return {"success": True}


@router.post("/logistics/shipments/{shipment_id}/status")
async def update_shipment_status(
    shipment_id: str,
    payload: ShipmentStatusRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    shipment = await update_shipment_tracking(
        decode_id_or_404(shipment_id),
        payload.status,
        payload.location or "Logistics update",
        payload.remarks or payload.status.value,
        db,
        actor_type="admin",
        actor_id=current_user.id,
        context={"source": "manual_status_api"},
    )
    await db.commit()
    await analytics.capture("system", "shipment_status_updated", {"shipment_id": shipment.id, "status": payload.status.value})
    await _notify_customer_for_shipment_status(
        shipment=shipment,
        db=db,
        title=f"Order {payload.status.value.replace('_', ' ')}",
        body=payload.remarks or f"Shipment is now {payload.status.value.replace('_', ' ')}.",
    )
    return {"success": True}


@router.post("/vendor/shipments/{shipment_id}/label")
async def generate_vendor_shipping_label(
    shipment_id: str,
    force: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor_for_user(current_user, db)
    shipment = await db.get(Shipment, decode_id_or_404(shipment_id))
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    vendor_order = await db.get(VendorOrder, shipment.vendor_order_id) if shipment.vendor_order_id else None
    if vendor_order is None or vendor_order.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    label = await _ensure_shipping_label(shipment=shipment, db=db, force=force)
    return {
        "shipment_id": encode_id(shipment.id or 0),
        "awb": shipment.awb,
        "label_url": label["url"],
        "generated_at": label["generated_at"],
        "label": label["payload"],
    }


@router.get("/vendor/shipments/{shipment_id}/label")
async def get_vendor_shipping_label(
    shipment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await generate_vendor_shipping_label(shipment_id, False, current_user, db)


@router.get("/logistics/shipments/{shipment_id}/label")
async def get_shipping_label_metadata(
    shipment_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    shipment = await db.get(Shipment, decode_id_or_404(shipment_id))
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    label = await _ensure_shipping_label(shipment=shipment, db=db)
    return {
        "shipment_id": encode_id(shipment.id or 0),
        "awb": shipment.awb,
        "carrier": "platform-logistics",
        "label_url": label["url"],
        "label": label["payload"],
    }


@router.post("/logistics/shipments/{shipment_id}/pod", status_code=status.HTTP_201_CREATED)
async def capture_proof_of_delivery(
    shipment_id: str,
    payload: ShipmentProofRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_shipment_id = decode_id_or_404(shipment_id)
    shipment = await db.get(Shipment, decoded_shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    proof = await create_shipment_proof(
        shipment_id=decoded_shipment_id,
        agent_id=decode_id_or_404(payload.agent_id) if payload.agent_id else None,
        proof_type=payload.proof_type,
        otp_code=payload.otp_code,
        photo_url=payload.photo_url,
        signature_url=payload.signature_url,
        notes=payload.notes,
        db=db,
    )
    shipment = await update_shipment_tracking(
        decoded_shipment_id,
        OrderStatus.DELIVERED,
        "Delivered",
        payload.notes or "Proof of delivery captured",
        db,
        actor_type="admin",
        actor_id=current_user.id,
        context={"source": "pod_capture", "proof_id": proof.id},
    )
    await db.commit()
    await _notify_customer_for_shipment_status(
        shipment=shipment,
        db=db,
        title="Order delivered",
        body=payload.notes or "Your order has been delivered.",
    )
    return {"proof_id": encode_id(proof.id or 0)}


@router.get("/logistics/shipments/{shipment_id}/pod")
async def list_shipment_proofs(
    shipment_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    proofs = (
        await db.execute(select(ShipmentProof).where(ShipmentProof.shipment_id == decode_id_or_404(shipment_id)).order_by(ShipmentProof.created_at.desc()))
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(proof.id or 0),
                "agent_id": encode_id(proof.agent_id) if proof.agent_id else None,
                "proof_type": proof.proof_type,
                "otp_code": proof.otp_code,
                "photo_url": proof.photo_url,
                "signature_url": proof.signature_url,
                "notes": proof.notes,
                "created_at": proof.created_at.isoformat(),
            }
            for proof in proofs
        ],
        "total": len(proofs),
    }


@router.post("/logistics/branch-inventory/movements", status_code=status.HTTP_201_CREATED)
async def create_inventory_movement(
    payload: BranchInventoryMovementCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    movement = await record_branch_inventory_movement(
        branch_id=decode_id_or_404(payload.branch_id),
        shipment_id=decode_id_or_404(payload.shipment_id) if payload.shipment_id else None,
        variant_id=decode_id_or_404(payload.variant_id) if payload.variant_id else None,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        notes=payload.notes,
        db=db,
    )
    await db.commit()
    return {"movement_id": encode_id(movement.id or 0)}


@router.get("/logistics/branches/{branch_id}/performance")
async def get_branch_performance(
    branch_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_branch_id = decode_id_or_404(branch_id)
    agents = (await db.execute(select(DeliveryAgent).where(DeliveryAgent.branch_id == decoded_branch_id))).scalars().all()
    pickup_jobs = (await db.execute(select(PickupJob).where(PickupJob.branch_id == decoded_branch_id))).scalars().all()
    reverse_pickups = (await db.execute(select(ReversePickupJob).where(ReversePickupJob.branch_id == decoded_branch_id))).scalars().all()
    movements = (
        await db.execute(select(BranchInventoryMovement).where(BranchInventoryMovement.branch_id == decoded_branch_id))
    ).scalars().all()
    return {
        "branch_id": branch_id,
        "agent_count": len(agents),
        "active_agent_count": len([agent for agent in agents if agent.status == DeliveryAgentStatus.AVAILABLE]),
        "pickup_jobs": len(pickup_jobs),
        "reverse_pickups": len(reverse_pickups),
        "inventory_movements": len(movements),
        "total_moved_units": sum(movement.quantity for movement in movements),
    }


@router.get("/logistics/hubs/{hub_id}/performance")
async def get_hub_performance(
    hub_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    branches = (await db.execute(select(Branch).where(Branch.hub_id == decoded_hub_id))).scalars().all()
    manifests = (
        await db.execute(
            select(ShipmentManifest).where(
                (ShipmentManifest.origin_hub_id == decoded_hub_id) | (ShipmentManifest.destination_hub_id == decoded_hub_id)
            )
        )
    ).scalars().all()
    trips = (
        await db.execute(select(LineHaulTrip).join(ShipmentManifest, ShipmentManifest.id == LineHaulTrip.manifest_id).where(
            (ShipmentManifest.origin_hub_id == decoded_hub_id) | (ShipmentManifest.destination_hub_id == decoded_hub_id)
        ))
    ).scalars().all()
    return {
        "hub_id": hub_id,
        "branch_count": len(branches),
        "manifest_count": len(manifests),
        "trip_count": len(trips),
        "dispatched_manifest_count": len([manifest for manifest in manifests if manifest.status.value == "dispatched"]),
        "received_manifest_count": len([manifest for manifest in manifests if manifest.status.value == "received"]),
    }


@router.get("/logistics/hubs/{hub_id}/timeline")
async def list_hub_timeline(
    hub_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    events = (
        await db.execute(
            select(HubOperationEvent)
            .where(HubOperationEvent.hub_id == decoded_hub_id)
            .order_by(HubOperationEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "hub_id": hub_id,
        "items": [
            {
                "event_id": encode_id(event.id or 0),
                "queue_id": encode_id(event.queue_id) if event.queue_id else None,
                "queue_item_id": encode_id(event.queue_item_id) if event.queue_item_id else None,
                "shipment_id": encode_id(event.shipment_id) if event.shipment_id else None,
                "operation_type": event.operation_type,
                "payload": json.loads(event.payload_json or "{}"),
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "total": len(events),
    }


@router.get("/logistics/hubs/{hub_id}/kpi-dashboard")
async def get_hub_kpi_dashboard(
    hub_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    decoded_hub_id = decode_id_or_404(hub_id)
    queues = (await db.execute(select(HubSortQueue).where(HubSortQueue.hub_id == decoded_hub_id))).scalars().all()
    queue_ids = [queue.id for queue in queues if queue.id is not None]
    items: list[HubSortQueueItem] = []
    if queue_ids:
        items = (
            await db.execute(select(HubSortQueueItem).where(HubSortQueueItem.queue_id.in_(queue_ids)))
        ).scalars().all()
    moved_items = [item for item in items if item.status == HubSortItemStatus.MOVED_TO_NEXT_LEG and item.moved_at]
    exception_items = [item for item in items if item.status == HubSortItemStatus.EXCEPTION]
    dwell_samples_minutes = [
        max((item.moved_at - item.scanned_at).total_seconds(), 0) / 60 for item in moved_items if item.scanned_at and item.moved_at
    ]
    throughput = len(moved_items)
    avg_dwell = round(sum(dwell_samples_minutes) / len(dwell_samples_minutes), 2) if dwell_samples_minutes else 0.0
    mis_sort_rate = round((len(exception_items) / len(items)) * 100, 2) if items else 0.0
    return {
        "hub_id": hub_id,
        "queue_count": len(queues),
        "scanned_shipments": len(items),
        "throughput_shipments": throughput,
        "average_dwell_time_minutes": avg_dwell,
        "mis_sort_rate_percent": mis_sort_rate,
    }
