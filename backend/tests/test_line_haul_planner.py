import pytest

from src.apps.logistics.planner import (
    LockedAssignment,
    PlannerInput,
    RouteDefinition,
    VehicleCapacity,
    run_line_haul_optimizer,
)


@pytest.mark.unit
def test_planner_reports_infeasible_capacity_with_partial_fallback():
    result = run_line_haul_optimizer(
        PlannerInput(
            routes=[RouteDefinition(route_id="R1", origin_hub="H1", destination_hub="H2", demand_units=30)],
            vehicles=[VehicleCapacity(vehicle_id="V1", hub_code="H1", capacity_units=12)],
            connectivity={"H1": ["H2"], "H2": ["H1"]},
            locked_assignments=[],
            random_seed=11,
        )
    )

    assert result.metadata["partial_failure"] is True
    assert result.metadata["fallback_strategy_used"] == "partial_manifest_split_v1"
    assert result.unassigned_routes == [{"route_id": "R1", "reason": "insufficient_capacity", "remaining_units": 18}]


@pytest.mark.unit
def test_planner_marks_disconnected_hubs_as_unassigned():
    result = run_line_haul_optimizer(
        PlannerInput(
            routes=[RouteDefinition(route_id="R2", origin_hub="A", destination_hub="Z", demand_units=8)],
            vehicles=[VehicleCapacity(vehicle_id="V2", hub_code="A", capacity_units=20)],
            connectivity={"A": ["B"], "B": ["A"]},
            locked_assignments=[],
            random_seed=5,
        )
    )

    assert result.unassigned_routes == [{"route_id": "R2", "reason": "disconnected_hubs", "remaining_units": 8}]
    assert result.metadata["fallback_strategy_used"] == "disconnected_hub_skip_v1"


@pytest.mark.unit
def test_planner_is_deterministic_for_fixed_seed_with_overrides():
    planner_input = PlannerInput(
        routes=[
            RouteDefinition(route_id="R10", origin_hub="HUB-1", destination_hub="HUB-2", demand_units=20),
            RouteDefinition(route_id="R11", origin_hub="HUB-1", destination_hub="HUB-3", demand_units=10),
        ],
        vehicles=[
            VehicleCapacity(vehicle_id="V10", hub_code="HUB-1", capacity_units=15),
            VehicleCapacity(vehicle_id="V11", hub_code="HUB-1", capacity_units=20),
        ],
        connectivity={"HUB-1": ["HUB-2", "HUB-3"], "HUB-2": ["HUB-1"], "HUB-3": ["HUB-1"]},
        locked_assignments=[
            LockedAssignment(route_id="R10", vehicle_id="V10", lock_units=5),
            LockedAssignment(route_id="R11", vehicle_id="V10", override_units=12),
        ],
        random_seed=99,
    )

    first = run_line_haul_optimizer(planner_input)
    second = run_line_haul_optimizer(planner_input)

    assert [(a.route_id, a.vehicle_id, a.assigned_units, a.locked, a.overridden) for a in first.assignments] == [
        (a.route_id, a.vehicle_id, a.assigned_units, a.locked, a.overridden) for a in second.assignments
    ]
    assert first.unassigned_routes == second.unassigned_routes
    assert first.metadata["fallback_strategy_used"] == "manual_override_respected_v1"
    assert "override_exceeds_capacity:V10" in first.metadata["warnings"]
