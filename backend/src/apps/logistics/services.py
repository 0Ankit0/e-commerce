from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.logistics.models import (
    Branch,
    DeliveryAgent,
    DeliveryAgentStatus,
    DeliveryZone,
    Hub,
    LineHaulTrip,
    LineHaulTripStatus,
    PickupJob,
    PickupJobStatus,
    ReversePickupJob,
    ReversePickupStatus,
    ShipmentProof,
    ShipmentManifest,
    ShipmentManifestStatus,
    ShippingOption,
)
from src.apps.orders.models import OrderStatus, ReturnRequest, Shipment, ShipmentTracking, VendorOrder, VendorOrderStatus


async def get_zone_by_pincode(pincode: str, db: AsyncSession) -> DeliveryZone | None:
    zones = (await db.execute(select(DeliveryZone).where(DeliveryZone.is_active == True))).scalars().all()  # noqa: E712
    for zone in zones:
        if pincode in json.loads(zone.pincodes_json or "[]"):
            return zone
    return None


async def quote_shipping(pincode: str, cod: bool, db: AsyncSession) -> dict[str, object]:
    zone = await get_zone_by_pincode(pincode, db)
    if zone is None:
        return {
            "serviceable": True,
            "zone_code": "DEFAULT",
            "shipping_rate": 0.0,
            "cod_enabled": True,
            "shipping_option": None,
        }
    option = (
        await db.execute(
            select(ShippingOption).where(
                ShippingOption.zone_id == zone.id,
                ShippingOption.is_active == True,  # noqa: E712
            ).order_by(ShippingOption.rate.asc())
        )
    ).scalars().first()
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


async def update_shipment_tracking(
    shipment_id: int,
    status_value: OrderStatus,
    location: str,
    remarks: str,
    db: AsyncSession,
) -> Shipment:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    shipment.status = status_value
    shipment.current_location = location
    shipment.updated_at = datetime.utcnow()
    db.add(
        ShipmentTracking(
            shipment_id=shipment.id,
            status=status_value,
            location=location,
            remarks=remarks,
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
    pickup_job.picked_up_at = datetime.utcnow()
    vendor_order = await db.get(VendorOrder, pickup_job.vendor_order_id)
    if vendor_order:
        vendor_order.status = VendorOrderStatus.SHIPPED
        vendor_order.updated_at = datetime.utcnow()
    await update_shipment_tracking(pickup_job.shipment_id, OrderStatus.SHIPPED, location, "Package picked up from vendor", db)


async def start_line_haul_trip(trip: LineHaulTrip, db: AsyncSession) -> None:
    manifest = await db.get(ShipmentManifest, trip.manifest_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    manifest.status = ShipmentManifestStatus.DISPATCHED
    manifest.updated_at = datetime.utcnow()
    trip.status = LineHaulTripStatus.IN_TRANSIT
    trip.departed_at = datetime.utcnow()
    for shipment_id in json.loads(manifest.shipment_ids_json or "[]"):
        await update_shipment_tracking(shipment_id, OrderStatus.SHIPPED, "Line haul", "Manifest dispatched", db)


async def arrive_line_haul_trip(trip: LineHaulTrip, db: AsyncSession) -> None:
    manifest = await db.get(ShipmentManifest, trip.manifest_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    manifest.status = ShipmentManifestStatus.RECEIVED
    manifest.updated_at = datetime.utcnow()
    trip.status = LineHaulTripStatus.ARRIVED
    trip.arrived_at = datetime.utcnow()
    destination_hub = await db.get(Hub, manifest.destination_hub_id) if manifest.destination_hub_id else None
    location = destination_hub.name if destination_hub else "Destination hub"
    for shipment_id in json.loads(manifest.shipment_ids_json or "[]"):
        await update_shipment_tracking(shipment_id, OrderStatus.OUT_FOR_DELIVERY, location, "Shipment received at destination hub", db)


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
    job.picked_up_at = datetime.utcnow()


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
