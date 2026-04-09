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
  runPlanner,
} from '@/lib/line-haul-planner';

type PlanVersion = {
  id: string;
  name: string;
  status: 'draft' | 'finalized';
  createdAt: string;
  snapshot: PlannerResult;
};

export default function LineHaulPlannerPage() {
  const [seed, setSeed] = useState(17);
  const [routes] = useState<RouteRow[]>(DEFAULT_ROUTES);
  const [vehicles] = useState<VehicleRow[]>(DEFAULT_VEHICLES);
  const [locks, setLocks] = useState<LockedAssignment[]>(DEFAULT_LOCKS);
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [runs, setRuns] = useState<PlannerResult[]>([]);
  const [versions, setVersions] = useState<PlanVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const totals = useMemo(
    () => ({
      demand: routes.reduce((acc, route) => acc + route.demandUnits, 0),
      capacity: vehicles.reduce((acc, vehicle) => acc + vehicle.capacityUnits, 0),
    }),
    [routes, vehicles],
  );

  const selectedVersion = versions.find((version) => version.id === selectedVersionId) ?? null;

  const onRun = () => {
    const output = runPlanner(routes, vehicles, locks, seed);
    setResult(output);
    setRuns((current) => [output, ...current].slice(0, 8));
  };

  const onSaveDraft = () => {
    if (!result) return;
    const id = `plan-${Date.now()}`;
    const draft: PlanVersion = {
      id,
      name: `Plan v${versions.length + 1}`,
      status: 'draft',
      createdAt: new Date().toISOString(),
      snapshot: result,
    };
    setVersions((current) => [draft, ...current]);
    setSelectedVersionId(id);
  };

  const onFinalize = () => {
    if (!selectedVersionId) return;
    setVersions((current) =>
      current.map((version) =>
        version.id === selectedVersionId
          ? {
              ...version,
              status: 'finalized',
            }
          : version,
      ),
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Line-haul planner</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Explicit route and fleet planning workspace with optimization runs, draft versions, and finalization controls.
          </p>
        </div>
        <div className="flex gap-3">
          <Input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value || 0))} className="w-28" />
          <Button onClick={onRun}>
            <Sparkles className="mr-2 h-4 w-4" />Run optimizer
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Total route demand</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{totals.demand}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Available capacity</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{totals.capacity}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Pre-locked assignments</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{locks.length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Routes</CardTitle>
            <CardDescription>Plannable lane matrix with origin, destination, and demand units.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto text-sm">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-[var(--text-muted)]">
                    <th>Route</th>
                    <th>Origin</th>
                    <th>Destination</th>
                    <th>Demand</th>
                  </tr>
                </thead>
                <tbody>
                  {routes.map((route) => (
                    <tr key={route.routeId} className="border-t border-[var(--border-color)]">
                      <td className="py-2 font-medium">{route.routeId}</td>
                      <td>{route.origin}</td>
                      <td>{route.destination}</td>
                      <td>{route.demandUnits}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vehicles and capacities</CardTitle>
            <CardDescription>Fleet inventory available for assignment in this optimization window.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto text-sm">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-[var(--text-muted)]">
                    <th>Vehicle</th>
                    <th>Hub</th>
                    <th>Capacity</th>
                  </tr>
                </thead>
                <tbody>
                  {vehicles.map((vehicle) => (
                    <tr key={vehicle.vehicleId} className="border-t border-[var(--border-color)]">
                      <td className="py-2 font-medium">{vehicle.vehicleId}</td>
                      <td>{vehicle.hubCode}</td>
                      <td>{vehicle.capacityUnits}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-4 w-4" />Lock / override assignments
          </CardTitle>
          <CardDescription>Pin critical assignments or force a manual override before finalizing the generated manifest.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {locks.map((lock, index) => (
            <div key={`${lock.routeId}-${lock.vehicleId}-${index}`} className="grid gap-2 rounded-xl border border-[var(--border-color)] p-3 md:grid-cols-4">
              <Input
                value={lock.routeId}
                onChange={(event) => setLocks((current) => current.map((item, i) => (i === index ? { ...item, routeId: event.target.value } : item)))}
              />
              <Input
                value={lock.vehicleId}
                onChange={(event) =>
                  setLocks((current) => current.map((item, i) => (i === index ? { ...item, vehicleId: event.target.value } : item)))
                }
              />
              <Input
                type="number"
                value={lock.lockUnits ?? ''}
                placeholder="Lock units"
                onChange={(event) =>
                  setLocks((current) => current.map((item, i) => (i === index ? { ...item, lockUnits: Number(event.target.value || 0) } : item)))
                }
              />
              <Input
                type="number"
                value={lock.overrideUnits ?? ''}
                placeholder="Override units"
                onChange={(event) =>
                  setLocks((current) => current.map((item, i) => (i === index ? { ...item, overrideUnits: Number(event.target.value || 0) } : item)))
                }
              />
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
              <p>
                <strong>Score:</strong> {result.metadata.score}%
              </p>
              <p>
                <strong>Runtime:</strong> {result.metadata.runtime_ms} ms
              </p>
              <p>
                <strong>Fallback:</strong> {result.metadata.fallback_strategy_used}
              </p>
              <p>
                <strong>Seed:</strong> {result.metadata.inputs.seed}
              </p>
              {result.metadata.warnings.length > 0 && <p><strong>Warnings:</strong> {result.metadata.warnings.join(', ')}</p>}
              {result.unassignedRoutes.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
                  <TriangleAlert className="mr-2 inline h-4 w-4" />
                  {result.unassignedRoutes.length} route(s) still incomplete. Planner fallback preserved feasible allocations and marked remainder for manual follow-up.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Plan output</CardTitle>
                <CardDescription>Review auto, locked, and rebalanced allocations before manifest finalization.</CardDescription>
              </div>
              <Button variant="outline" onClick={onSaveDraft}>
                <Save className="mr-2 h-4 w-4" />Save draft
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2 text-sm">
                {result.assignments.map((row, idx) => (
                  <li key={`${row.routeId}-${row.vehicleId}-${idx}`} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                    <strong>{row.routeId}</strong> → {row.vehicleId} · {row.assignedUnits} units {row.locked ? '(locked)' : ''}{' '}
                    {row.overridden ? '(override)' : ''} {row.rebalanced ? '(rebalanced)' : ''}
                  </li>
                ))}
              </ul>

              <div>
                <p className="mb-2 text-sm font-medium text-[var(--text-secondary)]">Recent optimization runs</p>
                <ul className="space-y-2 text-sm">
                  {runs.map((run, index) => (
                    <li key={`${run.metadata.inputs.seed}-${index}`} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                      Run {runs.length - index} · seed {run.metadata.inputs.seed} · score {run.metadata.score}% · fallback {run.metadata.fallback_strategy_used}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Drafts, versions, and finalization</CardTitle>
          <CardDescription>Promote validated drafts to finalized manifest plans for line-haul dispatch.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {versions.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No saved draft versions yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {versions.map((version) => (
                <li
                  key={version.id}
                  className={`rounded-lg border px-3 py-2 ${selectedVersionId === version.id ? 'border-[var(--focus-color)]' : 'border-[var(--border-color)]'}`}
                >
                  <button type="button" className="w-full text-left" onClick={() => setSelectedVersionId(version.id)}>
                    <strong>{version.name}</strong> · {version.status} · score {version.snapshot.metadata.score}% · {new Date(version.createdAt).toLocaleString()}
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex flex-wrap gap-2">
            <Button disabled={!selectedVersion || selectedVersion.status === 'finalized'} onClick={onFinalize}>
              <CheckCircle2 className="mr-2 h-4 w-4" />Finalize selected version
            </Button>
            {selectedVersion?.status === 'finalized' && <p className="self-center text-sm text-emerald-700">Selected plan is finalized for dispatch.</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
