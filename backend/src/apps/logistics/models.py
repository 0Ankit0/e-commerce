from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class HubType(str, Enum):
    NATIONAL = "national"
    REGIONAL = "regional"
    LOCAL = "local"


class DeliveryAgentStatus(str, Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    OFFLINE = "offline"
    ON_LEAVE = "on_leave"


class ShipmentManifestStatus(str, Enum):
    DRAFT = "draft"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    RECONCILED = "reconciled"


class LineHaulTripStatus(str, Enum):
    PLANNED = "planned"
    LOADED = "loaded"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    CANCELLED = "cancelled"


class PickupJobStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    RECEIVED_AT_HUB = "received_at_hub"
    FAILED = "failed"


class ReversePickupStatus(str, Enum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    RECEIVED = "received"
    RETURNED_TO_VENDOR = "returned_to_vendor"
    CANCELLED = "cancelled"


class DeliveryExceptionStatus(str, Enum):
    OPEN = "open"
    RESCHEDULED = "rescheduled"
    RTO_INITIATED = "rto_initiated"
    RESOLVED = "resolved"


class ShippingOption(SQLModel, table=True):
    __tablename__ = "shipping_options"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    zone_id: Optional[int] = Field(default=None, foreign_key="delivery_zones.id", index=True)
    name: str = Field(max_length=120)
    code: str = Field(max_length=50, unique=True, index=True)
    rate: float = Field(default=0, ge=0)
    cod_enabled: bool = Field(default=True)
    estimated_days: int = Field(default=3, ge=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class DeliveryZone(SQLModel, table=True):
    __tablename__ = "delivery_zones"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    code: str = Field(max_length=50, unique=True, index=True)
    state: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=120)
    pincodes_json: str = Field(default="[]")
    cod_enabled: bool = Field(default=True)
    is_active: bool = Field(default=True)
    shipping_rate: float = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)


class Hub(SQLModel, table=True):
    __tablename__ = "logistics_hubs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    code: str = Field(max_length=50, unique=True, index=True)
    address: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=120)
    state: str = Field(default="", max_length=120)
    hub_type: HubType = Field(default=HubType.LOCAL)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class Branch(SQLModel, table=True):
    __tablename__ = "logistics_branches"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    hub_id: int = Field(foreign_key="logistics_hubs.id", index=True)
    zone_id: Optional[int] = Field(default=None, foreign_key="delivery_zones.id", index=True)
    name: str = Field(max_length=120)
    code: str = Field(max_length=50, unique=True, index=True)
    address: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=120)
    state: str = Field(default="", max_length=120)
    contact_phone: str = Field(default="", max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class DeliveryAgent(SQLModel, table=True):
    __tablename__ = "delivery_agents"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    branch_id: int = Field(foreign_key="logistics_branches.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    name: str = Field(max_length=120)
    phone: str = Field(default="", max_length=20)
    status: DeliveryAgentStatus = Field(default=DeliveryAgentStatus.AVAILABLE)
    capacity: int = Field(default=20, ge=0)
    current_load: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)


class ShipmentManifest(SQLModel, table=True):
    __tablename__ = "shipment_manifests"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=64, unique=True, index=True)
    origin_hub_id: Optional[int] = Field(default=None, foreign_key="logistics_hubs.id", index=True)
    destination_hub_id: Optional[int] = Field(default=None, foreign_key="logistics_hubs.id", index=True)
    branch_id: Optional[int] = Field(default=None, foreign_key="logistics_branches.id", index=True)
    shipment_ids_json: str = Field(default="[]")
    status: ShipmentManifestStatus = Field(default=ShipmentManifestStatus.DRAFT)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class LineHaulTrip(SQLModel, table=True):
    __tablename__ = "line_haul_trips"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    manifest_id: int = Field(foreign_key="shipment_manifests.id", index=True)
    vehicle_number: str = Field(default="", max_length=50)
    driver_name: str = Field(default="", max_length=120)
    driver_phone: str = Field(default="", max_length=20)
    status: LineHaulTripStatus = Field(default=LineHaulTripStatus.PLANNED)
    departed_at: Optional[datetime] = Field(default=None)
    arrived_at: Optional[datetime] = Field(default=None)
    last_latitude: Optional[float] = Field(default=None)
    last_longitude: Optional[float] = Field(default=None)
    last_gps_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class PickupJob(SQLModel, table=True):
    __tablename__ = "pickup_jobs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_order_id: int = Field(foreign_key="vendor_orders.id", index=True)
    shipment_id: int = Field(foreign_key="shipments.id", index=True)
    branch_id: Optional[int] = Field(default=None, foreign_key="logistics_branches.id", index=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="delivery_agents.id", index=True)
    status: PickupJobStatus = Field(default=PickupJobStatus.PENDING)
    scheduled_for: Optional[datetime] = Field(default=None)
    picked_up_at: Optional[datetime] = Field(default=None)
    failure_reason: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class ReversePickupJob(SQLModel, table=True):
    __tablename__ = "reverse_pickup_jobs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    return_request_id: int = Field(foreign_key="return_requests.id", index=True)
    shipment_id: Optional[int] = Field(default=None, foreign_key="shipments.id", index=True)
    branch_id: Optional[int] = Field(default=None, foreign_key="logistics_branches.id", index=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="delivery_agents.id", index=True)
    status: ReversePickupStatus = Field(default=ReversePickupStatus.REQUESTED)
    scheduled_for: Optional[datetime] = Field(default=None)
    picked_up_at: Optional[datetime] = Field(default=None)
    received_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class BranchInventory(SQLModel, table=True):
    __tablename__ = "branch_inventory"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    branch_id: int = Field(foreign_key="logistics_branches.id", index=True)
    shipment_id: Optional[int] = Field(default=None, foreign_key="shipments.id", index=True)
    variant_id: Optional[int] = Field(default=None, foreign_key="product_variants.id", index=True)
    quantity: int = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=utc_now)


class ShipmentProof(SQLModel, table=True):
    __tablename__ = "shipment_proofs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    shipment_id: int = Field(foreign_key="shipments.id", index=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="delivery_agents.id", index=True)
    proof_type: str = Field(default="otp", max_length=30)
    otp_code: str = Field(default="", max_length=20)
    photo_url: str = Field(default="", max_length=500)
    signature_url: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class DeliveryException(SQLModel, table=True):
    __tablename__ = "delivery_exceptions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    shipment_id: int = Field(foreign_key="shipments.id", index=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="delivery_agents.id", index=True)
    exception_type: str = Field(max_length=80, index=True)
    failure_reason: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=500)
    rescheduled_for: Optional[datetime] = Field(default=None)
    rto_initiated_at: Optional[datetime] = Field(default=None)
    status: DeliveryExceptionStatus = Field(default=DeliveryExceptionStatus.OPEN)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BranchInventoryMovement(SQLModel, table=True):
    __tablename__ = "branch_inventory_movements"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    branch_id: int = Field(foreign_key="logistics_branches.id", index=True)
    shipment_id: Optional[int] = Field(default=None, foreign_key="shipments.id", index=True)
    variant_id: Optional[int] = Field(default=None, foreign_key="product_variants.id", index=True)
    movement_type: str = Field(max_length=40, index=True)
    quantity: int = Field(default=0)
    notes: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class RouteOptimizationPlan(SQLModel, table=True):
    __tablename__ = "route_optimization_plans"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    manifest_id: Optional[int] = Field(default=None, foreign_key="shipment_manifests.id", index=True)
    trip_id: Optional[int] = Field(default=None, foreign_key="line_haul_trips.id", index=True)
    strategy: str = Field(default="nearest_neighbor_2opt_v1", max_length=80)
    total_distance_km: float = Field(default=0, ge=0)
    estimated_duration_minutes: int = Field(default=0, ge=0)
    routed_stop_count: int = Field(default=0, ge=0)
    unroutable_stop_count: int = Field(default=0, ge=0)
    score: float = Field(default=0, ge=0)
    stops_json: str = Field(default="[]")
    metrics_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CourierLocationPing(SQLModel, table=True):
    __tablename__ = "courier_location_pings"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: Optional[int] = Field(default=None, foreign_key="line_haul_trips.id", index=True)
    shipment_id: Optional[int] = Field(default=None, foreign_key="shipments.id", index=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="delivery_agents.id", index=True)
    latitude: float
    longitude: float
    speed_kph: Optional[float] = Field(default=None)
    heading: Optional[float] = Field(default=None)
    accuracy_meters: Optional[float] = Field(default=None)
    source: str = Field(default="device", max_length=40)
    label: str = Field(default="", max_length=120)
    recorded_at: datetime = Field(default_factory=utc_now, index=True)
    created_at: datetime = Field(default_factory=utc_now)
