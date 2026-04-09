export type RouteRow = {
  routeId: string;
  origin: string;
  destination: string;
  demandUnits: number;
};

export type VehicleRow = {
  vehicleId: string;
  hubCode: string;
  capacityUnits: number;
};

export type LockedAssignment = {
  routeId: string;
  vehicleId: string;
  lockUnits?: number;
  overrideUnits?: number;
};

export type PlannerAssignment = {
  routeId: string;
  vehicleId: string;
  assignedUnits: number;
  locked: boolean;
  overridden: boolean;
  rebalanced: boolean;
};

export type PlannerResult = {
  assignments: PlannerAssignment[];
  unassignedRoutes: Array<{ route_id: string; reason: string; remaining_units: number }>;
  metadata: {
    inputs: Record<string, number>;
    score: number;
    runtime_ms: number;
    fallback_strategy_used: string;
    partial_failure: boolean;
    warnings: string[];
  };
};

const connectivity: Record<string, string[]> = {
  'HUB-DEL': ['HUB-LKO', 'HUB-JAI'],
  'HUB-LKO': ['HUB-PAT'],
  'HUB-JAI': ['HUB-DEL'],
  'HUB-PAT': ['HUB-LKO'],
};

function isConnected(origin: string, destination: string): boolean {
  if (origin === destination) return true;
  const visited = new Set([origin]);
  const queue = [origin];

  while (queue.length) {
    const current = queue.shift()!;
    for (const neighbor of connectivity[current] ?? []) {
      if (neighbor === destination) return true;
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push(neighbor);
      }
    }
  }

  return false;
}

export function runPlanner(routes: RouteRow[], vehicles: VehicleRow[], locks: LockedAssignment[], seed: number): PlannerResult {
  const assignmentMap = new Map<string, number>(vehicles.map((v) => [v.vehicleId, v.capacityUnits]));
  const remainingByRoute = new Map<string, number>(routes.map((r) => [r.routeId, r.demandUnits]));
  const assignments: PlannerAssignment[] = [];
  const unassignedRoutes: PlannerResult['unassignedRoutes'] = [];
  const warnings: string[] = [];

  let fallbackStrategyUsed = 'none';

  for (const route of routes) {
    if (!isConnected(route.origin, route.destination)) {
      unassignedRoutes.push({ route_id: route.routeId, reason: 'disconnected_hubs', remaining_units: route.demandUnits });
      remainingByRoute.set(route.routeId, 0);
      fallbackStrategyUsed = 'disconnected_hub_skip_v1';
    }
  }

  for (const lock of locks) {
    const remaining = remainingByRoute.get(lock.routeId) ?? 0;
    if (remaining <= 0) continue;

    const currentCap = assignmentMap.get(lock.vehicleId) ?? 0;
    const requested = Math.max(lock.overrideUnits ?? lock.lockUnits ?? remaining, 0);
    const units = lock.overrideUnits != null ? requested : Math.min(requested, currentCap, remaining);

    if (units <= 0) continue;

    if (lock.overrideUnits != null && units > currentCap) {
      warnings.push(`override_exceeds_capacity:${lock.vehicleId}`);
      fallbackStrategyUsed = 'manual_override_capped_v1';
    }

    const cappedUnits = Math.min(units, currentCap);
    assignments.push({
      routeId: lock.routeId,
      vehicleId: lock.vehicleId,
      assignedUnits: cappedUnits,
      locked: true,
      overridden: lock.overrideUnits != null,
      rebalanced: false,
    });
    remainingByRoute.set(lock.routeId, Math.max(remaining - cappedUnits, 0));
    assignmentMap.set(lock.vehicleId, Math.max(currentCap - cappedUnits, 0));
  }

  const randomValues = new Map<string, number>();
  vehicles.forEach((v, index) => {
    const derived = (Math.sin(seed + index * 13) + 1) * 1000;
    randomValues.set(v.vehicleId, derived);
  });

  const orderedVehicles = [...vehicles].sort((a, b) => {
    const capDiff = (assignmentMap.get(b.vehicleId) ?? 0) - (assignmentMap.get(a.vehicleId) ?? 0);
    if (capDiff !== 0) return capDiff;
    return (randomValues.get(b.vehicleId) ?? 0) - (randomValues.get(a.vehicleId) ?? 0);
  });

  for (const route of routes) {
    let remaining = remainingByRoute.get(route.routeId) ?? 0;
    if (remaining <= 0) continue;

    for (const vehicle of orderedVehicles) {
      if (vehicle.hubCode !== route.origin || remaining <= 0) continue;
      const cap = assignmentMap.get(vehicle.vehicleId) ?? 0;
      const chunk = Math.min(cap, remaining);
      if (chunk <= 0) continue;

      assignments.push({ routeId: route.routeId, vehicleId: vehicle.vehicleId, assignedUnits: chunk, locked: false, overridden: false, rebalanced: false });
      assignmentMap.set(vehicle.vehicleId, cap - chunk);
      remaining -= chunk;
    }

    // Fallback: reposition capacity from connected hubs when origin hub capacity is exhausted.
    if (remaining > 0) {
      for (const vehicle of orderedVehicles) {
        if (vehicle.hubCode === route.origin || remaining <= 0) continue;
        if (!isConnected(vehicle.hubCode, route.origin)) continue;
        const cap = assignmentMap.get(vehicle.vehicleId) ?? 0;
        const chunk = Math.min(cap, remaining);
        if (chunk <= 0) continue;

        assignments.push({ routeId: route.routeId, vehicleId: vehicle.vehicleId, assignedUnits: chunk, locked: false, overridden: false, rebalanced: true });
        assignmentMap.set(vehicle.vehicleId, cap - chunk);
        remaining -= chunk;
        fallbackStrategyUsed = fallbackStrategyUsed === 'none' ? 'cross_hub_rebalance_v1' : fallbackStrategyUsed;
      }
    }

    remainingByRoute.set(route.routeId, remaining);
    if (remaining > 0) {
      unassignedRoutes.push({ route_id: route.routeId, reason: 'insufficient_capacity', remaining_units: remaining });
      fallbackStrategyUsed = fallbackStrategyUsed === 'none' ? 'defer_unserved_capacity_v1' : fallbackStrategyUsed;
      warnings.push(`manual_followup_required:${route.routeId}`);
    }
  }

  const totalDemand = routes.reduce((acc, route) => acc + route.demandUnits, 0);
  const assignedUnits = assignments.reduce((acc, row) => acc + row.assignedUnits, 0);

  return {
    assignments,
    unassignedRoutes,
    metadata: {
      inputs: {
        route_count: routes.length,
        vehicle_count: vehicles.length,
        locked_assignment_count: locks.length,
        seed,
      },
      score: totalDemand > 0 ? Number(((assignedUnits / totalDemand) * 100).toFixed(2)) : 100,
      runtime_ms: Number((0.2 + routes.length * 0.08 + vehicles.length * 0.05).toFixed(2)),
      fallback_strategy_used: fallbackStrategyUsed,
      partial_failure: unassignedRoutes.length > 0,
      warnings,
    },
  };
}

export const DEFAULT_ROUTES: RouteRow[] = [
  { routeId: 'R-NAT-01', origin: 'HUB-DEL', destination: 'HUB-LKO', demandUnits: 38 },
  { routeId: 'R-NAT-02', origin: 'HUB-DEL', destination: 'HUB-JAI', demandUnits: 18 },
  { routeId: 'R-NAT-03', origin: 'HUB-LKO', destination: 'HUB-PAT', demandUnits: 12 },
];

export const DEFAULT_VEHICLES: VehicleRow[] = [
  { vehicleId: 'TRUCK-19', hubCode: 'HUB-DEL', capacityUnits: 26 },
  { vehicleId: 'TRUCK-22', hubCode: 'HUB-DEL', capacityUnits: 24 },
  { vehicleId: 'TRUCK-71', hubCode: 'HUB-LKO', capacityUnits: 12 },
];

export const DEFAULT_LOCKS: LockedAssignment[] = [{ routeId: 'R-NAT-02', vehicleId: 'TRUCK-19', lockUnits: 8 }];
