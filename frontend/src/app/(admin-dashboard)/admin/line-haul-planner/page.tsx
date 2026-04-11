'use client';

import { useMemo, useState } from 'react';
import { CheckCircle2, Lock, Save, Sparkles, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  DEFAULT_LOCKS,
  DEFAULT_ROUTES,
  DEFAULT_VEHICLES,
  type LockedAssignment,
  type PlannerResult,
  type RouteRow,
  type VehicleRow,
} from '@/lib/line-haul-planner';
import {
  useApplyLineHaulDraft,
  useLineHaulPlanDrafts,
  useRunLineHaulOptimization,
  useSaveLineHaulDraft,
  useValidateLineHaulAssignments,
} from '@/hooks/use-route-planning';

export default function LineHaulPlannerPage() {
  const [seed, setSeed] = useState(17);
  const [routes] = useState<RouteRow[]>(DEFAULT_ROUTES);
  const [vehicles] = useState<VehicleRow[]>(DEFAULT_VEHICLES);
  const [locks, setLocks] = useState<LockedAssignment[]>(DEFAULT_LOCKS);
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string>('');
  const [manualVehicleId, setManualVehicleId] = useState<string>('');
  const [manualUnits, setManualUnits] = useState<number>(0);

  const draftsQuery = useLineHaulPlanDrafts();
  const runMutation = useRunLineHaulOptimization();
  const saveDraftMutation = useSaveLineHaulDraft();
  const applyDraftMutation = useApplyLineHaulDraft();
  const validateMutation = useValidateLineHaulAssignments();

  const assignments = useMemo(() => {
    const autoAssignments = (result?.assignments ?? []).map((row) => ({
      route_id: row.routeId,
      vehicle_id: row.vehicleId,
      assigned_units: row.assignedUnits,
    }));
    if (selectedRouteId && manualVehicleId && manualUnits > 0) {
      return [...autoAssignments, { route_id: selectedRouteId, vehicle_id: manualVehicleId, assigned_units: manualUnits }];
    }
    return autoAssignments;
  }, [manualUnits, manualVehicleId, result?.assignments, selectedRouteId]);

  const totals = useMemo(
    () => ({
      demand: routes.reduce((acc, route) => acc + route.demandUnits, 0),
      capacity: vehicles.reduce((acc, vehicle) => acc + vehicle.capacityUnits, 0),
    }),
    [routes, vehicles]
  );

  const conflictErrors = (validateMutation.data?.errors as Array<{ code: string; message: string }> | undefined) ?? [];

  const onRun = async () => {
    const payload = {
      routes: routes.map((route) => ({
        route_id: route.routeId,
        origin_hub: route.origin,
        destination_hub: route.destination,
        demand_units: route.demandUnits,
      })),
      vehicles: vehicles.map((vehicle) => ({
        vehicle_id: vehicle.vehicleId,
        hub_code: vehicle.hubCode,
        capacity_units: vehicle.capacityUnits,
      })),
      connectivity: {
        KTM: ['PKR', 'BWA', 'DHR'],
        PKR: ['KTM', 'DHR'],
        BWA: ['KTM'],
        DHR: ['KTM', 'PKR'],
      },
      locked_assignments: locks.map((lock) => ({
        route_id: lock.routeId,
        vehicle_id: lock.vehicleId,
        lock_units: lock.lockUnits,
        override_units: lock.overrideUnits,
      })),
      random_seed: seed,
    };
    const runResponse = await runMutation.mutateAsync(payload);
    setResult({
      assignments: runResponse.assignments.map((row: any) => ({
        routeId: row.route_id,
        vehicleId: row.vehicle_id,
        assignedUnits: row.assigned_units,
        locked: row.locked,
        overridden: row.overridden,
        rebalanced: false,
      })),
      unassignedRoutes: runResponse.unassigned_routes,
      metadata: runResponse.metadata,
    });

    await validateMutation.mutateAsync({
      name: 'inline-validation',
      routes: payload.routes,
      vehicles: payload.vehicles,
      locked_assignments: payload.locked_assignments,
      assignments: runResponse.assignments.map((row: any) => ({
        route_id: row.route_id,
        vehicle_id: row.vehicle_id,
        assigned_units: row.assigned_units,
      })),
      optimizer_metadata: runResponse.metadata,
      connectivity: payload.connectivity,
    });
  };

  const onSaveDraft = async () => {
    if (!result) return;
    await saveDraftMutation.mutateAsync({
      name: `Line-haul draft ${new Date().toLocaleString()}`,
      routes: routes.map((route) => ({ route_id: route.routeId, origin_hub: route.origin, destination_hub: route.destination, demand_units: route.demandUnits })),
      vehicles: vehicles.map((vehicle) => ({ vehicle_id: vehicle.vehicleId, hub_code: vehicle.hubCode, capacity_units: vehicle.capacityUnits })),
      locked_assignments: locks.map((lock) => ({ route_id: lock.routeId, vehicle_id: lock.vehicleId, lock_units: lock.lockUnits, override_units: lock.overrideUnits })),
      assignments,
      optimizer_metadata: result.metadata,
      connectivity: { KTM: ['PKR', 'BWA', 'DHR'], PKR: ['KTM', 'DHR'], BWA: ['KTM'], DHR: ['KTM', 'PKR'] },
    });
  };

  const savedDrafts = (draftsQuery.data as Array<{ draft_id: string; name: string; status: string; validation?: { errors?: Array<{ message: string }> } }> | undefined) ?? [];

  return (
    <main className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Admin logistics</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Line-haul planner</h1>
        </div>
        <div className="flex gap-3">
          <Input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value || 0))} className="w-28" />
          <Button onClick={onRun}>
            <Sparkles className="mr-2 h-4 w-4" />Run optimizer
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle>Total route demand</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{totals.demand}</p></CardContent></Card>
        <Card><CardHeader><CardTitle>Available capacity</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{totals.capacity}</p></CardContent></Card>
        <Card><CardHeader><CardTitle>Capacity utilization</CardTitle></CardHeader><CardContent><p className="text-sm">{validateMutation.data?.summary?.utilization?.map((row: any) => `${row.vehicle_id}: ${row.utilization_percent}%`).join(' · ') || 'Run validation'}</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Route selection + manual vehicle assignment</CardTitle><CardDescription>Pick a route, choose vehicle, and simulate manual assignment rows before saving.</CardDescription></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <Input placeholder="Route ID" value={selectedRouteId} onChange={(e) => setSelectedRouteId(e.target.value)} />
          <Input placeholder="Vehicle ID" value={manualVehicleId} onChange={(e) => setManualVehicleId(e.target.value)} />
          <Input type="number" placeholder="Units" value={manualUnits || ''} onChange={(e) => setManualUnits(Number(e.target.value || 0))} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Lock className="h-4 w-4" />Lock / override assignments</CardTitle>
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
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div><CardTitle>Plan output + conflict indicators</CardTitle></div>
            <Button variant="outline" onClick={onSaveDraft}><Save className="mr-2 h-4 w-4" />Save draft</Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {conflictErrors.length > 0 && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-700">
                <TriangleAlert className="mr-2 inline h-4 w-4" />
                {conflictErrors.map((error, idx) => <p key={`${error.code}-${idx}`}>{error.message}</p>)}
              </div>
            )}
            <ul className="space-y-2 text-sm">
              {result.assignments.map((row, idx) => <li key={`${row.routeId}-${row.vehicleId}-${idx}`} className="rounded-lg border border-[var(--border-color)] px-3 py-2"><strong>{row.routeId}</strong> → {row.vehicleId} · {row.assignedUnits} units</li>)}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Drafts / apply</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {savedDrafts.map((draft) => (
            <div key={draft.draft_id} className="flex items-center justify-between rounded-lg border border-[var(--border-color)] p-3 text-sm">
              <div>
                <p className="font-medium">{draft.name}</p>
                <p className="text-[var(--text-muted)]">{draft.status} {draft.validation?.errors?.length ? `· ${draft.validation.errors.length} conflict(s)` : '· clean'}</p>
              </div>
              <Button size="sm" disabled={draft.status === 'finalized'} onClick={() => applyDraftMutation.mutate(draft.draft_id)}>
                <CheckCircle2 className="mr-2 h-4 w-4" />Apply
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </main>
  );
}
