from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import dataclass


@dataclass(slots=True)
class RouteDefinition:
    route_id: str
    origin_hub: str
    destination_hub: str
    demand_units: int


@dataclass(slots=True)
class VehicleCapacity:
    vehicle_id: str
    hub_code: str
    capacity_units: int


@dataclass(slots=True)
class LockedAssignment:
    route_id: str
    vehicle_id: str
    lock_units: int | None = None
    override_units: int | None = None


@dataclass(slots=True)
class PlannerInput:
    routes: list[RouteDefinition]
    vehicles: list[VehicleCapacity]
    connectivity: dict[str, list[str]]
    locked_assignments: list[LockedAssignment]
    random_seed: int = 7


@dataclass(slots=True)
class PlannerAssignment:
    route_id: str
    vehicle_id: str
    assigned_units: int
    locked: bool = False
    overridden: bool = False
    reason: str = "capacity_fit"


@dataclass(slots=True)
class PlannerRunResult:
    assignments: list[PlannerAssignment]
    unassigned_routes: list[dict[str, object]]
    metadata: dict[str, object]


def _is_connected(origin: str, destination: str, graph: dict[str, list[str]]) -> bool:
    if origin == destination:
        return True
    visited = {origin}
    queue: deque[str] = deque([origin])
    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, []):
            if neighbor == destination:
                return True
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


def run_line_haul_optimizer(payload: PlannerInput) -> PlannerRunResult:
    started_at = time.perf_counter()
    rng = random.Random(payload.random_seed)

    route_by_id = {route.route_id: route for route in payload.routes}
    vehicle_by_id = {vehicle.vehicle_id: vehicle for vehicle in payload.vehicles}
    remaining_capacity = {vehicle.vehicle_id: max(vehicle.capacity_units, 0) for vehicle in payload.vehicles}
    remaining_demand = {route.route_id: max(route.demand_units, 0) for route in payload.routes}

    assignments: list[PlannerAssignment] = []
    unassigned_routes: list[dict[str, object]] = []
    fallback_strategy = "none"
    warnings: list[str] = []

    for route in payload.routes:
        if not _is_connected(route.origin_hub, route.destination_hub, payload.connectivity):
            unassigned_routes.append(
                {
                    "route_id": route.route_id,
                    "reason": "disconnected_hubs",
                    "remaining_units": remaining_demand[route.route_id],
                }
            )
            remaining_demand[route.route_id] = 0
            fallback_strategy = "disconnected_hub_skip_v1"

    for lock in payload.locked_assignments:
        route = route_by_id.get(lock.route_id)
        vehicle = vehicle_by_id.get(lock.vehicle_id)
        if route is None or vehicle is None:
            warnings.append(f"unknown_lock_reference:{lock.route_id}:{lock.vehicle_id}")
            continue
        if remaining_demand[route.route_id] <= 0:
            continue

        requested_units = lock.override_units if lock.override_units is not None else lock.lock_units
        if requested_units is None:
            requested_units = remaining_demand[route.route_id]

        units = max(requested_units, 0)
        if lock.override_units is None:
            units = min(units, remaining_capacity[vehicle.vehicle_id], remaining_demand[route.route_id])
        else:
            if units > remaining_capacity[vehicle.vehicle_id]:
                fallback_strategy = "manual_override_respected_v1"
                warnings.append(f"override_exceeds_capacity:{lock.vehicle_id}")

        if units <= 0:
            continue

        assignments.append(
            PlannerAssignment(
                route_id=route.route_id,
                vehicle_id=vehicle.vehicle_id,
                assigned_units=units,
                locked=True,
                overridden=lock.override_units is not None,
                reason="manual_override" if lock.override_units is not None else "locked_assignment",
            )
        )
        remaining_demand[route.route_id] = max(remaining_demand[route.route_id] - units, 0)
        remaining_capacity[vehicle.vehicle_id] -= units

    candidate_vehicles = payload.vehicles[:]
    rng.shuffle(candidate_vehicles)
    candidate_vehicles.sort(key=lambda vehicle: remaining_capacity.get(vehicle.vehicle_id, 0), reverse=True)

    for route in payload.routes:
        demand_left = remaining_demand[route.route_id]
        if demand_left <= 0:
            continue

        route_candidates = [
            vehicle
            for vehicle in candidate_vehicles
            if vehicle.hub_code == route.origin_hub and remaining_capacity[vehicle.vehicle_id] > 0
        ]
        for vehicle in route_candidates:
            if demand_left <= 0:
                break
            chunk = min(demand_left, remaining_capacity[vehicle.vehicle_id])
            if chunk <= 0:
                continue
            assignments.append(
                PlannerAssignment(
                    route_id=route.route_id,
                    vehicle_id=vehicle.vehicle_id,
                    assigned_units=chunk,
                    reason="capacity_fit",
                )
            )
            demand_left -= chunk
            remaining_capacity[vehicle.vehicle_id] -= chunk

        remaining_demand[route.route_id] = demand_left
        if demand_left > 0:
            unassigned_routes.append(
                {
                    "route_id": route.route_id,
                    "reason": "insufficient_capacity",
                    "remaining_units": demand_left,
                }
            )
            if fallback_strategy == "none":
                fallback_strategy = "partial_manifest_split_v1"

    total_demand = sum(max(route.demand_units, 0) for route in payload.routes)
    assigned_total = sum(assignment.assigned_units for assignment in assignments)
    score = round((assigned_total / total_demand) * 100, 2) if total_demand else 100.0
    runtime_ms = round((time.perf_counter() - started_at) * 1000, 2)

    return PlannerRunResult(
        assignments=assignments,
        unassigned_routes=unassigned_routes,
        metadata={
            "inputs": {
                "route_count": len(payload.routes),
                "vehicle_count": len(payload.vehicles),
                "locked_assignment_count": len(payload.locked_assignments),
                "seed": payload.random_seed,
                "total_demand_units": total_demand,
                "total_capacity_units": sum(max(vehicle.capacity_units, 0) for vehicle in payload.vehicles),
            },
            "score": score,
            "runtime_ms": runtime_ms,
            "fallback_strategy_used": fallback_strategy,
            "partial_failure": len(unassigned_routes) > 0,
            "warnings": warnings,
        },
    )
