from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.logistics.models import (
    Branch,
    DeliveryAgent,
    DeliveryAgentStatus,
    DeliveryZone,
    Hub,
    HubType,
    LineHaulTrip,
    PickupJob,
    ReversePickupJob,
    ShipmentProof,
    ShipmentManifest,
    ShippingOption,
)
from src.apps.logistics.services import (
    arrive_line_haul_trip,
    assign_pickup_job,
    assign_reverse_pickup,
    complete_pickup_job,
    complete_reverse_pickup,
    create_shipment_proof,
    create_pickup_job_for_vendor_order,
    create_reverse_pickup,
    get_manifest_or_404,
    get_pickup_job_or_404,
    get_trip_or_404,
    quote_shipping,
    start_line_haul_trip,
    update_shipment_tracking,
)
from src.apps.orders.models import OrderStatus, ReturnRequest, Shipment, ShipmentTracking, VendorOrder, VendorOrderStatus
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
    await db.commit()
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
    await db.commit()
    return {"success": True}


@router.post("/logistics/shipments/{shipment_id}/status")
async def update_shipment_status(
    shipment_id: str,
    payload: ShipmentStatusRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    shipment = await update_shipment_tracking(
        decode_id_or_404(shipment_id),
        payload.status,
        payload.location or "Logistics update",
        payload.remarks or payload.status.value,
        db,
    )
    await db.commit()
    await analytics.capture("system", "shipment_status_updated", {"shipment_id": shipment.id, "status": payload.status.value})
    return {"success": True}


@router.post("/logistics/shipments/{shipment_id}/pod", status_code=status.HTTP_201_CREATED)
async def capture_proof_of_delivery(
    shipment_id: str,
    payload: ShipmentProofRequest,
    _: User = Depends(get_current_active_superuser),
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
    shipment.status = OrderStatus.DELIVERED
    shipment.current_location = "Delivered"
    db.add(
        ShipmentTracking(
            shipment_id=shipment.id,
            status=OrderStatus.DELIVERED,
            location="Customer address",
            remarks=payload.notes or "Proof of delivery captured",
        )
    )
    await db.commit()
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
