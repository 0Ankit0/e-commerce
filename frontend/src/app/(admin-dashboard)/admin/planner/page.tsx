'use client';

import { useMemo, useState } from 'react';
import { AlertTriangle, Copy, Lock, Rocket, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DEFAULT_ROUTES, DEFAULT_VEHICLES } from '@/lib/line-haul-planner';
import {
  useClonePlannerDraft,
  useCreatePlannerDraft,
  useFinalizePlannerDraft,
  useLockPlannerDraft,
  usePlannerBacklogPool,
  useOptimizePlannerDraft,
  usePlannerDrafts,
  usePlannerFleetCapacity,
  usePlannerRouteCanvas,
  usePublishPlannerDraft,
  usePublishQueue,
  useUpdatePlannerDraft,
} from '@/hooks/use-system';

const CONNECTIVITY = {
  KTM: ['PKR', 'BWA', 'DHR'],
  PKR: ['KTM', 'DHR'],
  BWA: ['KTM'],
  DHR: ['KTM', 'PKR'],
};

export default function AdminPlannerPage() {
  const [seed, setSeed] = useState(17);
  const drafts = usePlannerDrafts();
  const createDraft = useCreatePlannerDraft();
  const optimizeDraft = useOptimizePlannerDraft();
  const updateDraft = useUpdatePlannerDraft();
  const publishDraft = usePublishPlannerDraft();
  const cloneDraft = useClonePlannerDraft();
  const lockDraft = useLockPlannerDraft();
  const finalizeDraft = useFinalizePlannerDraft();
  const backlogPool = usePlannerBacklogPool();
  const routeCanvas = usePlannerRouteCanvas();
  const fleetCapacity = usePlannerFleetCapacity();
  const publishQueue = usePublishQueue();

  const latestDraft = (drafts.data?.[0] as any) ?? null;
  const assignments = useMemo(
    () => ((latestDraft?.assignments as Array<{ route_id: string; vehicle_id: string; assigned_units: number }> | undefined) ?? []),
    [latestDraft?.assignments],
  );
  const routes = useMemo(
    () =>
      (latestDraft?.routes as Array<{ route_id: string; demand_units: number; destination_hub: string }> | undefined) ??
      DEFAULT_ROUTES.map((route) => ({
        route_id: route.routeId,
        demand_units: route.demandUnits,
        destination_hub: route.destination,
      })),
    [latestDraft?.routes],
  );
  const vehicles = useMemo(
    () =>
      (latestDraft?.vehicles as Array<{ vehicle_id: string; capacity_units: number }> | undefined) ??
      DEFAULT_VEHICLES.map((vehicle) => ({
        vehicle_id: vehicle.vehicleId,
        capacity_units: vehicle.capacityUnits,
      })),
    [latestDraft?.vehicles],
  );

  const unscheduled = useMemo(() => {
    const assignedByRoute = new Map<string, number>();
    assignments.forEach((item) => assignedByRoute.set(item.route_id, (assignedByRoute.get(item.route_id) ?? 0) + item.assigned_units));
    return routes
      .map((route) => ({ ...route, unassigned_units: Math.max(route.demand_units - (assignedByRoute.get(route.route_id) ?? 0), 0) }))
      .filter((route) => route.unassigned_units > 0);
  }, [assignments, routes]);

  const vehicleLoad = useMemo(() => {
    const loads = new Map<string, number>();
    assignments.forEach((item) => loads.set(item.vehicle_id, (loads.get(item.vehicle_id) ?? 0) + item.assigned_units));
    return vehicles.map((vehicle) => {
      const assigned = loads.get(vehicle.vehicle_id) ?? 0;
      const percent = vehicle.capacity_units ? Math.min(100, Math.round((assigned / vehicle.capacity_units) * 100)) : 0;
      return { ...vehicle, assigned, percent };
    });
  }, [assignments, vehicles]);

  const onCreate = async () => {
    await createDraft.mutateAsync({
      name: `Planner ${new Date().toISOString()}`,
      routes: DEFAULT_ROUTES.map((route) => ({ route_id: route.routeId, origin_hub: route.origin, destination_hub: route.destination, demand_units: route.demandUnits })),
      vehicles: DEFAULT_VEHICLES.map((vehicle) => ({ vehicle_id: vehicle.vehicleId, hub_code: vehicle.hubCode, capacity_units: vehicle.capacityUnits })),
      connectivity: CONNECTIVITY,
      locked_assignments: [],
      assignments: [],
      optimizer_metadata: {},
      status: 'draft',
    });
  };

  const onOptimize = async () => {
    if (!latestDraft) return;
    await optimizeDraft.mutateAsync({ draftId: latestDraft.draft_id, expectedVersion: latestDraft.version, randomSeed: seed });
  };

  const onResolve = async () => {
    if (!latestDraft) return;
    const conflictCount = conflicts.length;
    const accepted = conflictCount
      ? window.confirm(`This draft has ${conflictCount} conflicts. Save your manual override anyway?`)
      : true;
    if (!accepted) return;
    await updateDraft.mutateAsync({
      draftId: latestDraft.draft_id,
      payload: {
        name: latestDraft.name,
        status: 'draft',
        expected_version: latestDraft.version,
        routes: latestDraft.routes,
        vehicles: latestDraft.vehicles,
        connectivity: latestDraft.connectivity,
        locked_assignments: latestDraft.locked_assignments,
        assignments: assignments.filter((row) => row.assigned_units > 0),
        optimizer_metadata: latestDraft.optimizer_metadata,
      },
    });
  };

  const onPublish = async (freeze = false) => {
    if (!latestDraft) return;
    const confirmed = window.confirm(
      freeze ? 'Freeze this plan and block further edits?' : 'Publish this plan and auto-generate executable manifests?',
    );
    if (!confirmed) return;
    await publishDraft.mutateAsync({ draftId: latestDraft.draft_id, expectedVersion: latestDraft.version, freeze });
  };

  const conflicts = ((latestDraft?.validation?.errors as Array<{ code: string; message: string }> | undefined) ?? []);

  return (
    <main className="space-y-6 p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Admin logistics</p>
          <h1 className="text-3xl font-semibold">Planner workspace</h1>
        </div>
        <div className="flex gap-2">
          <Input type="number" className="w-28" value={seed} onChange={(event) => setSeed(Number(event.target.value || 0))} />
          <Button onClick={onCreate}>Create draft</Button>
          <Button variant="outline" onClick={onOptimize} disabled={!latestDraft}><Sparkles className="mr-2 h-4 w-4" />Optimize</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Shipment backlog / pool</CardTitle></CardHeader>
          <CardContent className="text-sm">
            {((backlogPool.data?.items as Array<any> | undefined) ?? []).length
              ? (backlogPool.data?.items as Array<any>).map((item) => (
                  <p key={item.route_id}>{item.destination_hub} ({item.cutoff_window}): {item.backlog_units} units</p>
                ))
              : unscheduled.length
                ? unscheduled.map((route) => <p key={route.route_id}>{route.route_id}: {route.unassigned_units} units</p>)
                : 'No unscheduled shipments'}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Conflict warnings</CardTitle></CardHeader>
          <CardContent className="text-sm">
            {conflicts.length ? conflicts.map((conflict, index) => <p key={`${conflict.code}-${index}`}><AlertTriangle className="mr-1 inline h-3 w-3" />{conflict.code}: {conflict.message}</p>) : 'No conflicts'}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Publish queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {((publishQueue.data as Array<any> | undefined) ?? []).length
              ? (publishQueue.data as Array<any>).slice(0, 3).map((item) => <p key={item.draft_id}>{item.name} · {item.status}</p>)
              : <p>No drafts queued for publish</p>}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Route canvas (planned vs unplanned)</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="font-medium">Planned</p>
          {((routeCanvas.data?.planned as Array<any> | undefined) ?? []).length
            ? (routeCanvas.data?.planned as Array<any>).map((row) => <p key={row.route_id}>{row.route_id}</p>)
            : assignments.length
              ? assignments.map((row, idx) => <p key={`${row.route_id}-${row.vehicle_id}-${idx}`}>{row.route_id} → {row.vehicle_id} ({row.assigned_units} units)</p>)
              : 'No planned routes'}
          <p className="mt-3 font-medium">Unplanned</p>
          {((routeCanvas.data?.unplanned as Array<any> | undefined) ?? []).length
            ? (routeCanvas.data?.unplanned as Array<any>).map((row) => <p key={row.route_id}>{row.route_id}</p>)
            : 'No unplanned routes'}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Fleet capacity board</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {((((fleetCapacity.data?.items as Array<any> | undefined) ?? vehicleLoad) as Array<any>)).map((vehicle) => (
            <div key={vehicle.vehicle_id}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{vehicle.vehicle_id} ({vehicle.weight_kg ?? '-'}kg/{vehicle.volume_m3 ?? '-'}m³)</span>
                <span>{vehicle.assigned_units ?? vehicle.assigned}/{vehicle.capacity_units}</span>
              </div>
              <div className="h-2 rounded bg-slate-200"><div className="h-2 rounded bg-indigo-500" style={{ width: `${vehicle.percent ?? 0}%` }} /></div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Draft lifecycle controls</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Status: {latestDraft?.status ?? 'n/a'} · Version: {latestDraft?.version ?? 0}</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={onResolve} disabled={!latestDraft}>Resolve conflicts</Button>
            <Button size="sm" variant="outline" onClick={() => latestDraft && cloneDraft.mutate({ draftId: latestDraft.draft_id })} disabled={!latestDraft}><Copy className="mr-2 h-4 w-4" />Clone what-if</Button>
            <Button size="sm" variant="outline" onClick={() => latestDraft && lockDraft.mutate({ draftId: latestDraft.draft_id, expectedVersion: latestDraft.version })} disabled={!latestDraft}><Lock className="mr-2 h-4 w-4" />Lock</Button>
            <Button size="sm" variant="outline" onClick={() => latestDraft && finalizeDraft.mutate({ draftId: latestDraft.draft_id, expectedVersion: latestDraft.version })} disabled={!latestDraft}>Finalize</Button>
            <Button size="sm" onClick={() => onPublish(false)} disabled={!latestDraft || conflicts.length > 0}><Rocket className="mr-2 h-4 w-4" />Publish</Button>
            <Button size="sm" variant="secondary" onClick={() => onPublish(true)} disabled={!latestDraft}>Freeze</Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
