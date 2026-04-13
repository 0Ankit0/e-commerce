from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.iam.api.deps import get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.logistics.models import LineHaulTrip, RouteOptimizationPlan, ShipmentManifest, ShipmentManifestStatus
from src.apps.logistics.planner import LockedAssignment, PlannerInput, RouteDefinition, VehicleCapacity, run_line_haul_optimizer

router = APIRouter(prefix="/logistics/planning", tags=["logistics-planning"])


class PlanningRouteInput(BaseModel):
    route_id: str = Field(min_length=2, max_length=80)
    origin_hub: str = Field(min_length=2, max_length=40)
    destination_hub: str = Field(min_length=2, max_length=40)
    demand_units: int = Field(ge=0)
    demand_weight_kg: float = Field(default=0, ge=0)
    demand_volume_m3: float = Field(default=0, ge=0)
    window_start: datetime | None = None
    window_end: datetime | None = None


class PlanningVehicleInput(BaseModel):
    vehicle_id: str = Field(min_length=2, max_length=80)
    hub_code: str = Field(min_length=2, max_length=40)
    capacity_units: int = Field(ge=0)
    capacity_weight_kg: float = Field(default=0, ge=0)
    capacity_volume_m3: float = Field(default=0, ge=0)
    available_count: int = Field(default=1, ge=0)
    available_from: datetime | None = None
    available_to: datetime | None = None


class PlanningAssignmentInput(BaseModel):
    route_id: str
    vehicle_id: str
    assigned_units: int = Field(ge=0)


class PlanningPlanCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    routes: list[PlanningRouteInput]
    vehicles: list[PlanningVehicleInput]
    connectivity: dict[str, list[str]] = Field(default_factory=dict)


class PlanningPlanUpdateRequest(PlanningPlanCreateRequest):
    assignments: list[PlanningAssignmentInput] = Field(default_factory=list)
    expected_version: int = Field(ge=1)


class PlanningOptimizeRequest(BaseModel):
    expected_version: int = Field(ge=1)
    random_seed: int = Field(default=7, ge=0)
    locked_assignments: list[PlanningAssignmentInput] = Field(default_factory=list)
    manual_overrides: list[PlanningAssignmentInput] = Field(default_factory=list)


class PlanningPublishRequest(BaseModel):
    expected_version: int = Field(ge=1)


class PlanningManifestRequest(BaseModel):
    expected_version: int = Field(ge=1)
    code: str = Field(min_length=3, max_length=64)
    shipment_ids: list[str] = Field(default_factory=list)


class PlanningDispatchAssignRequest(BaseModel):
    expected_version: int = Field(ge=1)
    vehicle_number: str = Field(min_length=2, max_length=50)
    driver_name: str = Field(default="", max_length=120)
    driver_phone: str = Field(default="", max_length=20)


class PlanningExecutionPublishRequest(BaseModel):
    expected_version: int = Field(ge=1)


def _load_payload(plan: RouteOptimizationPlan) -> dict[str, object]:
    payload = json.loads(plan.metrics_json or "{}")
    payload.setdefault("version", 1)
    payload.setdefault("status", "draft")
    payload.setdefault("assignments", [])
    payload.setdefault("optimizer_metadata", {})
    payload.setdefault("conflicts", [])
    payload.setdefault("manifest_id", None)
    payload.setdefault("trip_id", None)
    return payload


def _compute_constraint_errors(routes: list[dict[str, object]], vehicles: list[dict[str, object]], assignments: list[dict[str, object]]) -> list[dict[str, object]]:
    vehicle_lookup = {str(vehicle.get("vehicle_id")): vehicle for vehicle in vehicles}
    route_lookup = {str(route.get("route_id")): route for route in routes}
    errors: list[dict[str, object]] = []

    assigned_by_vehicle: dict[str, dict[str, float]] = defaultdict(lambda: {"units": 0, "weight": 0.0, "volume": 0.0})
    assigned_units_by_route: dict[str, int] = defaultdict(int)

    for assignment in assignments:
        route_id = str(assignment.get("route_id") or "")
        vehicle_id = str(assignment.get("vehicle_id") or "")
        units = int(assignment.get("assigned_units") or 0)
        route = route_lookup.get(route_id)
        vehicle = vehicle_lookup.get(vehicle_id)
        if route is None or vehicle is None:
            continue
        demand_units = int(route.get("demand_units") or 0)
        weight_per_unit = (float(route.get("demand_weight_kg") or 0) / demand_units) if demand_units else 0
        volume_per_unit = (float(route.get("demand_volume_m3") or 0) / demand_units) if demand_units else 0
        assigned_by_vehicle[vehicle_id]["units"] += units
        assigned_by_vehicle[vehicle_id]["weight"] += units * weight_per_unit
        assigned_by_vehicle[vehicle_id]["volume"] += units * volume_per_unit
        assigned_units_by_route[route_id] += units

    for vehicle_id, totals in assigned_by_vehicle.items():
        vehicle = vehicle_lookup[vehicle_id]
        max_units = int(vehicle.get("capacity_units") or 0) * max(int(vehicle.get("available_count") or 0), 0)
        max_weight = float(vehicle.get("capacity_weight_kg") or 0) * max(int(vehicle.get("available_count") or 0), 0)
        max_volume = float(vehicle.get("capacity_volume_m3") or 0) * max(int(vehicle.get("available_count") or 0), 0)
        if totals["units"] > max_units:
            errors.append({"code": "capacity_units_exceeded", "vehicle_id": vehicle_id})
        if max_weight and totals["weight"] > max_weight:
            errors.append({"code": "capacity_weight_exceeded", "vehicle_id": vehicle_id})
        if max_volume and totals["volume"] > max_volume:
            errors.append({"code": "capacity_volume_exceeded", "vehicle_id": vehicle_id})

    for route in routes:
        route_id = str(route.get("route_id") or "")
        if assigned_units_by_route.get(route_id, 0) < int(route.get("demand_units") or 0):
            errors.append({"code": "unscheduled", "route_id": route_id})

    return errors


def _route_ui_states(routes: list[dict[str, object]], assignments: list[dict[str, object]], conflicts: list[dict[str, object]]) -> list[dict[str, str]]:
    assigned_units: dict[str, int] = defaultdict(int)
    for assignment in assignments:
        assigned_units[str(assignment.get("route_id") or "")] += int(assignment.get("assigned_units") or 0)

    failed_routes = {
        str(conflict.get("route_id"))
        for conflict in conflicts
        if conflict.get("route_id") and conflict.get("code") not in {"unscheduled", "optimizer_unassigned"}
    }
    items: list[dict[str, str]] = []
    for route in routes:
        route_id = str(route.get("route_id") or "")
        if route_id in failed_routes:
            state = "constraint-failed"
        elif assigned_units.get(route_id, 0) < int(route.get("demand_units") or 0):
            state = "unscheduled"
        else:
            state = "ready-to-publish"
        items.append({"route_id": route_id, "state": state})
    return items


def _serialize_plan(plan: RouteOptimizationPlan) -> dict[str, object]:
    payload = _load_payload(plan)
    routes = json.loads(plan.stops_json or "[]")
    assignments = payload.get("assignments") or []
    conflicts = payload.get("conflicts") or []
    return {
        "plan_id": encode_id(plan.id or 0),
        "name": payload.get("name") or f"Planning {encode_id(plan.id or 0)}",
        "status": payload.get("status") or "draft",
        "version": int(payload.get("version") or 1),
        "routes": routes,
        "vehicles": payload.get("vehicles") or [],
        "connectivity": payload.get("connectivity") or {},
        "assignments": assignments,
        "optimizer_metadata": payload.get("optimizer_metadata") or {},
        "conflicts": conflicts,
        "ui_states": _route_ui_states(routes, assignments, conflicts),
        "manifest_id": encode_id(payload["manifest_id"]) if payload.get("manifest_id") else None,
        "trip_id": encode_id(payload["trip_id"]) if payload.get("trip_id") else None,
        "updated_at": plan.updated_at.isoformat(),
    }


def _check_version(payload: dict[str, object], expected: int) -> None:
    current = int(payload.get("version") or 1)
    if expected != current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Version mismatch", "expected_version": expected, "current_version": current},
        )


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_planning_plan(
    request: PlanningPlanCreateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = RouteOptimizationPlan(
        strategy="line_haul_planning_v2",
        stops_json=json.dumps([route.model_dump(mode="json") for route in request.routes]),
        metrics_json=json.dumps(
            {
                "name": request.name,
                "status": "draft",
                "version": 1,
                "vehicles": [vehicle.model_dump(mode="json") for vehicle in request.vehicles],
                "connectivity": request.connectivity,
                "assignments": [],
                "conflicts": [],
                "optimizer_metadata": {},
            }
        ),
        updated_at=utc_now(),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _serialize_plan(plan)


@router.get("/plans")
async def list_plans(
    limit: int = Query(default=25, ge=1, le=100),
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plans = (
        await db.execute(
            select(RouteOptimizationPlan)
            .where(RouteOptimizationPlan.strategy == "line_haul_planning_v2")
            .order_by(RouteOptimizationPlan.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {"items": [_serialize_plan(plan) for plan in plans]}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, _: User = Depends(get_current_active_superuser), db: AsyncSession = Depends(get_db)):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    return _serialize_plan(plan)


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    request: PlanningPlanUpdateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    _check_version(payload, request.expected_version)

    routes = [route.model_dump(mode="json") for route in request.routes]
    vehicles = [vehicle.model_dump(mode="json") for vehicle in request.vehicles]
    assignments = [assignment.model_dump(mode="json") for assignment in request.assignments]
    conflicts = _compute_constraint_errors(routes, vehicles, assignments)

    payload.update(
        {
            "name": request.name,
            "vehicles": vehicles,
            "connectivity": request.connectivity,
            "assignments": assignments,
            "conflicts": conflicts,
            "version": int(payload.get("version") or 1) + 1,
        }
    )
    plan.stops_json = json.dumps(routes)
    plan.metrics_json = json.dumps(payload)
    plan.updated_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return _serialize_plan(plan)


@router.post("/plans/{plan_id}/optimize")
async def optimize_plan(
    plan_id: str,
    request: PlanningOptimizeRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    _check_version(payload, request.expected_version)

    routes = json.loads(plan.stops_json or "[]")
    vehicles = payload.get("vehicles") or []
    connectivity = payload.get("connectivity") or {}

    locked = [LockedAssignment(route_id=a.route_id, vehicle_id=a.vehicle_id, lock_units=a.assigned_units) for a in request.locked_assignments]
    locked.extend(
        LockedAssignment(route_id=a.route_id, vehicle_id=a.vehicle_id, lock_units=a.assigned_units, override_units=a.assigned_units)
        for a in request.manual_overrides
    )

    result = run_line_haul_optimizer(
        PlannerInput(
            routes=[RouteDefinition(**{k: route[k] for k in ["route_id", "origin_hub", "destination_hub", "demand_units"]}) for route in routes],
            vehicles=[VehicleCapacity(vehicle_id=v["vehicle_id"], hub_code=v["hub_code"], capacity_units=int(v.get("capacity_units") or 0)) for v in vehicles],
            connectivity=connectivity,
            locked_assignments=locked,
            random_seed=request.random_seed,
        )
    )
    assignments = [a.model_dump(mode="json") for a in result.assignments]
    conflicts = _compute_constraint_errors(routes, vehicles, assignments)
    for unassigned in result.unassigned_routes:
        conflicts.append({"code": "optimizer_unassigned", **unassigned})

    payload["assignments"] = assignments
    payload["optimizer_metadata"] = result.metadata
    payload["conflicts"] = conflicts
    payload["version"] = int(payload.get("version") or 1) + 1
    plan.metrics_json = json.dumps(payload)
    plan.updated_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return _serialize_plan(plan)


@router.post("/plans/{plan_id}/publish")
async def publish_plan(
    plan_id: str,
    request: PlanningPublishRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    _check_version(payload, request.expected_version)

    if payload.get("conflicts"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": "Resolve conflicts before publish", "conflicts": payload.get("conflicts")})

    payload["status"] = "published"
    payload["version"] = int(payload.get("version") or 1) + 1
    payload["published_at"] = utc_now().isoformat()
    plan.metrics_json = json.dumps(payload)
    plan.updated_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return _serialize_plan(plan)


@router.get("/plans/{plan_id}/board")
async def planning_board(plan_id: str, _: User = Depends(get_current_active_superuser), db: AsyncSession = Depends(get_db)):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    routes = json.loads(plan.stops_json or "[]")
    vehicles = payload.get("vehicles") or []

    shipment_pool: dict[str, int] = defaultdict(int)
    for route in routes:
        shipment_pool[str(route.get("destination_hub") or "")] += int(route.get("demand_units") or 0)

    return {
        "plan_id": encode_id(plan.id or 0),
        "route_network": {
            "list": routes,
            "map": [{"from": route.get("origin_hub"), "to": route.get("destination_hub"), "route_id": route.get("route_id")} for route in routes],
        },
        "shipment_pool_by_destination_hub": [{"destination_hub": hub, "demand_units": units} for hub, units in sorted(shipment_pool.items())],
        "vehicle_fleet_capacity_board": [
            {
                "vehicle_id": vehicle.get("vehicle_id"),
                "hub_code": vehicle.get("hub_code"),
                "capacity_units": vehicle.get("capacity_units"),
                "capacity_weight_kg": vehicle.get("capacity_weight_kg"),
                "capacity_volume_m3": vehicle.get("capacity_volume_m3"),
                "available_count": vehicle.get("available_count", 1),
            }
            for vehicle in vehicles
        ],
        "ui_states": _route_ui_states(routes, payload.get("assignments") or [], payload.get("conflicts") or []),
    }


@router.post("/plans/{plan_id}/dispatch/manifest", status_code=status.HTTP_201_CREATED)
async def create_manifest_from_plan(
    plan_id: str,
    request: PlanningManifestRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    _check_version(payload, request.expected_version)
    if payload.get("status") != "published":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan must be published before manifest creation")

    routes = json.loads(plan.stops_json or "[]")
    origin = next((r.get("origin_hub") for r in routes if r.get("origin_hub")), None)
    destination = next((r.get("destination_hub") for r in routes if r.get("destination_hub")), None)

    manifest = ShipmentManifest(
        code=request.code,
        shipment_ids_json=json.dumps([decode_id_or_404(sid) for sid in request.shipment_ids]),
        origin_hub_id=None,
        destination_hub_id=None,
    )
    db.add(manifest)
    await db.flush()
    payload["manifest_id"] = manifest.id
    payload["dispatch_origin_hub_code"] = origin
    payload["dispatch_destination_hub_code"] = destination
    payload["version"] = int(payload.get("version") or 1) + 1
    plan.metrics_json = json.dumps(payload)
    plan.updated_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return {"manifest_id": encode_id(manifest.id or 0), "plan": _serialize_plan(plan)}


@router.post("/plans/{plan_id}/dispatch/assign")
async def assign_dispatch_vehicle(
    plan_id: str,
    request: PlanningDispatchAssignRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    _check_version(payload, request.expected_version)
    manifest_id = payload.get("manifest_id")
    if not manifest_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Create manifest before assigning vehicle")

    trip = LineHaulTrip(
        manifest_id=int(manifest_id),
        vehicle_number=request.vehicle_number,
        driver_name=request.driver_name,
        driver_phone=request.driver_phone,
    )
    db.add(trip)
    await db.flush()

    payload["trip_id"] = trip.id
    payload["version"] = int(payload.get("version") or 1) + 1
    plan.metrics_json = json.dumps(payload)
    plan.updated_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return {"trip_id": encode_id(trip.id or 0), "plan": _serialize_plan(plan)}


@router.post("/plans/{plan_id}/dispatch/publish")
async def publish_dispatch_execution(
    plan_id: str,
    request: PlanningExecutionPublishRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(RouteOptimizationPlan, decode_id_or_404(plan_id))
    if plan is None or plan.strategy != "line_haul_planning_v2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning plan not found")
    payload = _load_payload(plan)
    _check_version(payload, request.expected_version)
    manifest_id = payload.get("manifest_id")
    if not manifest_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manifest is required before dispatch publish")

    manifest = await db.get(ShipmentManifest, int(manifest_id))
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    manifest.status = ShipmentManifestStatus.DISPATCHED
    manifest.updated_at = utc_now()

    payload["status"] = "published_to_execution"
    payload["version"] = int(payload.get("version") or 1) + 1
    plan.metrics_json = json.dumps(payload)
    plan.updated_at = utc_now()
    await db.commit()
    await db.refresh(plan)
    return {"manifest_id": encode_id(manifest.id or 0), "manifest_status": manifest.status.value, "plan": _serialize_plan(plan)}
