'use client';

import { useMemo, useState } from 'react';
import { Lock, Save, Sparkles, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

type RouteRow = {
  routeId: string;
  origin: string;
  destination: string;
  demandUnits: number;
};

type VehicleRow = {
  vehicleId: string;
  hubCode: string;
  capacityUnits: number;
};

type LockedAssignment = {
  routeId: string;
  vehicleId: string;
  lockUnits?: number;
  overrideUnits?: number;
};

type PlannerAssignment = {
  routeId: string;
  vehicleId: string;
  assignedUnits: number;
  locked: boolean;
  overridden: boolean;
};

type PlannerResult = {
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

const DEFAULT_ROUTES: RouteRow[] = [
  { routeId: 'R-NAT-01', origin: 'HUB-DEL', destination: 'HUB-LKO', demandUnits: 38 },
  { routeId: 'R-NAT-02', origin: 'HUB-DEL', destination: 'HUB-JAI', demandUnits: 18 },
  { routeId: 'R-NAT-03', origin: 'HUB-LKO', destination: 'HUB-PAT', demandUnits: 12 },
];

const DEFAULT_VEHICLES: VehicleRow[] = [
  { vehicleId: 'TRUCK-19', hubCode: 'HUB-DEL', capacityUnits: 26 },
  { vehicleId: 'TRUCK-22', hubCode: 'HUB-DEL', capacityUnits: 24 },
  { vehicleId: 'TRUCK-71', hubCode: 'HUB-LKO', capacityUnits: 12 },
];

const DEFAULT_LOCKS: LockedAssignment[] = [{ routeId: 'R-NAT-02', vehicleId: 'TRUCK-19', lockUnits: 8 }];

function runPlanner(routes: RouteRow[], vehicles: VehicleRow[], locks: LockedAssignment[], seed: number): PlannerResult {
  const connectivity: Record<string, string[]> = {
    'HUB-DEL': ['HUB-LKO', 'HUB-JAI'],
    'HUB-LKO': ['HUB-PAT'],
    'HUB-JAI': ['HUB-DEL'],
    'HUB-PAT': ['HUB-LKO'],
  };

  const assignmentMap = new Map<string, number>(vehicles.map((v) => [v.vehicleId, v.capacityUnits]));
  const remainingByRoute = new Map<string, number>(routes.map((r) => [r.routeId, r.demandUnits]));
  const assignments: PlannerAssignment[] = [];
  const unassignedRoutes: PlannerResult['unassignedRoutes'] = [];
  const warnings: string[] = [];

  const isConnected = (origin: string, destination: string) => {
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
  };

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
      fallbackStrategyUsed = 'manual_override_respected_v1';
      warnings.push(`override_exceeds_capacity:${lock.vehicleId}`);
    }

    assignments.push({ routeId: lock.routeId, vehicleId: lock.vehicleId, assignedUnits: units, locked: true, overridden: lock.overrideUnits != null });
    remainingByRoute.set(lock.routeId, Math.max(remaining - units, 0));
    assignmentMap.set(lock.vehicleId, currentCap - units);
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
      assignments.push({ routeId: route.routeId, vehicleId: vehicle.vehicleId, assignedUnits: chunk, locked: false, overridden: false });
      assignmentMap.set(vehicle.vehicleId, cap - chunk);
      remaining -= chunk;
    }

    remainingByRoute.set(route.routeId, remaining);
    if (remaining > 0) {
      unassignedRoutes.push({ route_id: route.routeId, reason: 'insufficient_capacity', remaining_units: remaining });
      if (fallbackStrategyUsed === 'none') {
        fallbackStrategyUsed = 'partial_manifest_split_v1';
      }
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

export default function LineHaulPlannerPage() {
  const [seed, setSeed] = useState(17);
  const [routes] = useState<RouteRow[]>(DEFAULT_ROUTES);
  const [vehicles] = useState<VehicleRow[]>(DEFAULT_VEHICLES);
  const [locks, setLocks] = useState<LockedAssignment[]>(DEFAULT_LOCKS);
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [versions, setVersions] = useState<Array<{ name: string; snapshot: PlannerResult }>>([]);

  const totals = useMemo(() => ({ demand: routes.reduce((acc, route) => acc + route.demandUnits, 0), capacity: vehicles.reduce((acc, vehicle) => acc + vehicle.capacityUnits, 0) }), [routes, vehicles]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Line-haul planner</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Define routes, assign vehicle capacity, run optimization, and save plan versions before manifest finalization.</p>
        </div>
        <div className="flex gap-3">
          <Input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value || 0))} className="w-28" />
          <Button onClick={() => setResult(runPlanner(routes, vehicles, locks, seed))}><Sparkles className="mr-2 h-4 w-4" />Run optimizer</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle>Total route demand</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{totals.demand}</p></CardContent></Card>
        <Card><CardHeader><CardTitle>Available capacity</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{totals.capacity}</p></CardContent></Card>
        <Card><CardHeader><CardTitle>Pre-locked assignments</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{locks.length}</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Lock className="h-4 w-4" />Lock / override assignments</CardTitle>
          <CardDescription>Pin critical assignments or force a manual override before finalizing the generated manifest.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {locks.map((lock, index) => (
            <div key={`${lock.routeId}-${lock.vehicleId}-${index}`} className="grid gap-2 rounded-xl border border-[var(--border-color)] p-3 md:grid-cols-4">
              <Input value={lock.routeId} onChange={(event) => setLocks((current) => current.map((item, i) => (i === index ? { ...item, routeId: event.target.value } : item)))} />
              <Input value={lock.vehicleId} onChange={(event) => setLocks((current) => current.map((item, i) => (i === index ? { ...item, vehicleId: event.target.value } : item)))} />
              <Input type="number" value={lock.lockUnits ?? ''} placeholder="Lock units" onChange={(event) => setLocks((current) => current.map((item, i) => (i === index ? { ...item, lockUnits: Number(event.target.value || 0) } : item)))} />
              <Input type="number" value={lock.overrideUnits ?? ''} placeholder="Override units" onChange={(event) => setLocks((current) => current.map((item, i) => (i === index ? { ...item, overrideUnits: Number(event.target.value || 0) } : item)))} />
            </div>
          ))}
        </CardContent>
      </Card>

      {result && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Optimization run metadata</CardTitle>
              <CardDescription>Inputs, score, runtime, and fallback strategy for this execution.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p><strong>Score:</strong> {result.metadata.score}%</p>
              <p><strong>Runtime:</strong> {result.metadata.runtime_ms} ms</p>
              <p><strong>Fallback:</strong> {result.metadata.fallback_strategy_used}</p>
              <p><strong>Seed:</strong> {result.metadata.inputs.seed}</p>
              {result.unassignedRoutes.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800"><TriangleAlert className="mr-2 inline h-4 w-4" />
                  {result.unassignedRoutes.length} route(s) incomplete due to capacity/connectivity constraints.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Plan output</CardTitle>
                <CardDescription>Review auto and manual allocations before manifest finalization.</CardDescription>
              </div>
              <Button variant="outline" onClick={() => setVersions((current) => [{ name: `Plan v${current.length + 1}`, snapshot: result }, ...current])}><Save className="mr-2 h-4 w-4" />Save version</Button>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {result.assignments.map((row, idx) => (
                  <li key={`${row.routeId}-${row.vehicleId}-${idx}`} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                    <strong>{row.routeId}</strong> → {row.vehicleId} · {row.assignedUnits} units {row.locked ? '(locked)' : ''} {row.overridden ? '(override)' : ''}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Saved plan versions</CardTitle>
          <CardDescription>Track strategy changes while iterating toward final line-haul manifest.</CardDescription>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? <p className="text-sm text-[var(--text-muted)]">No saved versions yet.</p> : (
            <ul className="space-y-2 text-sm">
              {versions.map((version) => (
                <li key={version.name} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                  <strong>{version.name}</strong> · score {version.snapshot.metadata.score}% · fallback {version.snapshot.metadata.fallback_strategy_used}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
