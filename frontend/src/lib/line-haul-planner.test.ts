import { describe, expect, it } from 'vitest';
import { runPlanner, type RouteRow, type VehicleRow } from './line-haul-planner';

describe('line haul planner', () => {
  it('enforces vehicle capacity constraints even when override asks for more units', () => {
    const routes: RouteRow[] = [{ routeId: 'R1', origin: 'HUB-DEL', destination: 'HUB-LKO', demandUnits: 30 }];
    const vehicles: VehicleRow[] = [{ vehicleId: 'V1', hubCode: 'HUB-DEL', capacityUnits: 10 }];

    const result = runPlanner(routes, vehicles, [{ routeId: 'R1', vehicleId: 'V1', overrideUnits: 50 }], 11);

    const byVehicle = result.assignments.reduce<Record<string, number>>((acc, current) => {
      acc[current.vehicleId] = (acc[current.vehicleId] ?? 0) + current.assignedUnits;
      return acc;
    }, {});

    expect(byVehicle.V1).toBe(10);
    expect(result.unassignedRoutes).toEqual([{ route_id: 'R1', reason: 'insufficient_capacity', remaining_units: 20 }]);
    expect(result.metadata.warnings).toContain('override_exceeds_capacity:V1');
  });

  it('produces deterministic optimization output for same fixed seed', () => {
    const routes: RouteRow[] = [
      { routeId: 'R1', origin: 'HUB-DEL', destination: 'HUB-LKO', demandUnits: 8 },
      { routeId: 'R2', origin: 'HUB-DEL', destination: 'HUB-JAI', demandUnits: 6 },
    ];
    const vehicles: VehicleRow[] = [
      { vehicleId: 'V1', hubCode: 'HUB-DEL', capacityUnits: 7 },
      { vehicleId: 'V2', hubCode: 'HUB-DEL', capacityUnits: 9 },
    ];

    const first = runPlanner(routes, vehicles, [], 42);
    const second = runPlanner(routes, vehicles, [], 42);

    expect(second).toEqual(first);
  });
});
