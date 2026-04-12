'use client';

import { useMemo, useState } from 'react';
import { Download, ShieldAlert, Shuffle, TimerReset, TrendingDown, TrendingUp, Users } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBranchDashboardAlerts, useBranchDashboardDrilldown, useBranchDashboardSnapshot } from '@/hooks/use-observability';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/auth-store';

function toExportFileName() {
  const today = new Date().toISOString().slice(0, 10);
  return `branch-dashboard-${today}.csv`;
}

export default function AdminBranchDashboardPage() {
  const [branchId, setBranchId] = useState('');
  const [zoneId, setZoneId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const user = useAuthStore((state) => state.user);
  const isAdmin = Boolean(user?.is_superuser);

  const filters = useMemo(
    () => ({
      branch_id: branchId || undefined,
      zone_id: zoneId || undefined,
      agent_id: agentId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      timezone,
    }),
    [agentId, branchId, dateFrom, dateTo, timezone, zoneId],
  );

  const { data: snapshot, isLoading: snapshotLoading } = useBranchDashboardSnapshot(filters);
  const { data: drilldown, isLoading: drilldownLoading } = useBranchDashboardDrilldown(filters);
  const { data: alerts } = useBranchDashboardAlerts(filters);

  const handleExport = async () => {
    const response = await apiClient.get('/logistics/branch-dashboard/export', {
      params: filters,
      responseType: 'blob',
    });
    const file = new Blob([response.data], { type: 'text/csv' });
    const href = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = href;
    link.download = toExportFileName();
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(href);
  };

  const branchOptions = snapshot?.branch_codes ? Object.entries(snapshot.branch_codes) : [];
  const managerBranchId = !isAdmin && snapshot?.branch_scope.length ? snapshot.branch_scope[0] : '';
  const activeBranchId = branchId || managerBranchId;

  const runAction = async (kind: 'reassign' | 'prioritize' | 'escalate') => {
    if (!activeBranchId) return;
    if (kind === 'reassign') {
      const rows = drilldown?.productivity ?? [];
      if (rows.length < 2) return;
      const sorted = [...rows].sort((a, b) => b.assigned - a.assigned);
      await apiClient.post('/logistics/branch-dashboard/actions/reassign-load', {
        branch_id: activeBranchId,
        from_agent_id: sorted[0].agent_id,
        to_agent_id: sorted[sorted.length - 1].agent_id,
        limit: 10,
      });
    }
    if (kind === 'prioritize') {
      await apiClient.post('/logistics/branch-dashboard/actions/prioritize-aging', {
        branch_id: activeBranchId,
        assignee_agent_id: agentId || undefined,
        limit: 20,
      });
    }
    if (kind === 'escalate') {
      await apiClient.post('/logistics/branch-dashboard/actions/escalate-issues', {
        branch_id: activeBranchId,
        note: 'Escalated from branch cockpit dashboard',
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Branch Cockpit</h1>
          <p className="mt-1 max-w-3xl text-sm text-[var(--text-secondary)]">
            {isAdmin
              ? 'Network-wide branch execution view with load balancing controls, threshold alerts, and weekly review snapshots.'
              : 'Operational branch execution screen for inventory posture, attempt trends, RTO, aging queues, and on-shift actions.'}
          </p>
        </div>
        <Button onClick={handleExport} variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      <Card className="rounded-[24px]">
        <CardHeader>
          <CardTitle>{isAdmin ? 'Admin filters' : 'Branch manager filters'}</CardTitle>
          <CardDescription>Keep filters aligned across cards, charts, and CSV exports.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          {isAdmin ? (
            <select value={branchId} onChange={(event) => setBranchId(event.target.value)} className="rounded-lg border px-3 py-2 text-sm">
              <option value="">All branches</option>
              {branchOptions.map(([id, code]) => (
                <option key={id} value={id}>{code}</option>
              ))}
            </select>
          ) : (
            <input readOnly value={managerBranchId || 'Scoped branch'} className="rounded-lg border px-3 py-2 text-sm" />
          )}
          <input value={zoneId} onChange={(event) => setZoneId(event.target.value)} placeholder="Zone ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input value={agentId} onChange={(event) => setAgentId(event.target.value)} placeholder="Agent ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
          <input value={timezone} onChange={(event) => setTimezone(event.target.value)} placeholder="Timezone (e.g. UTC)" className="rounded-lg border px-3 py-2 text-sm" />
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ['Inventory posture', snapshot?.snapshot.inventory_posture ?? 'healthy'],
          ['Attempt success', `${snapshot?.snapshot.attempt_success_rate_percent ?? 0}%`],
          ['RTO rate', `${snapshot?.snapshot.rto_rate_percent ?? 0}%`],
          ['Aging queue (6h+)', snapshot?.snapshot.aging_queue_over_6h ?? 0],
        ].map(([label, value]) => (
          <Card key={String(label)} className="rounded-[22px]">
            <CardContent className="pt-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{String(value)}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[24px]">
          <CardHeader>
            <CardTitle>Agent productivity</CardTitle>
            <CardDescription>Assigned vs completed vs failed.</CardDescription>
          </CardHeader>
          <CardContent>
            {drilldownLoading ? <p className="text-sm text-[var(--text-muted)]">Loading…</p> : (
              <ul className="space-y-2">
                {(drilldown?.productivity ?? []).map((row) => (
                  <li key={row.agent_id} className="rounded-lg border p-3 text-sm">
                    <p className="font-medium">{row.agent_name}</p>
                    <p className="text-xs text-[var(--text-muted)]">Assigned {row.assigned} · Completed {row.completed} · Failed {row.failed}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[24px]">
          <CardHeader>
            <CardTitle>Execution trend summary</CardTitle>
            <CardDescription>Delivery outcomes, staffing utilization, and queue aging.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {snapshotLoading ? <p className="text-[var(--text-muted)]">Loading…</p> : (
              <>
                <p>Delivery success rate: <strong>{snapshot?.snapshot.delivery_success_rate_percent ?? 0}%</strong></p>
                <p>Open exceptions: <strong>{snapshot?.snapshot.open_exceptions ?? 0}</strong></p>
                <p>Pending pickups: <strong>{drilldown?.backlog.pending_pickups ?? 0}</strong></p>
                <p>Inventory movement types tracked: <strong>{Object.keys(drilldown?.inventory_flow ?? {}).length}</strong></p>
                <p>Agent utilization: <strong>{snapshot?.snapshot.avg_agent_utilization_percent ?? 0}%</strong></p>
                <p>Aging queue (12h+): <strong>{snapshot?.snapshot.aging_queue_over_12h ?? 0}</strong></p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[24px]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldAlert className="h-4 w-4" />Threshold alerts</CardTitle>
          <CardDescription>Backlog, staffing, failure-rate, and SLA-breach alerts based on current filters.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {(alerts?.alerts ?? []).length === 0 ? <li className="text-[var(--text-muted)]">No active threshold breaches.</li> : (alerts?.alerts ?? []).map((alert) => (
              <li key={alert.code} className="rounded-lg border px-3 py-2">
                <p className="font-medium">{alert.message}</p>
                <p className="text-xs text-[var(--text-muted)]">Code: {alert.code} · Severity: {alert.severity}</p>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card className="rounded-[24px]">
        <CardHeader>
          <CardTitle>Operational actions</CardTitle>
          <CardDescription>Execute load balancing and incident actions directly from the cockpit.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => runAction('reassign')}><Shuffle className="mr-2 h-4 w-4" />Reassign load</Button>
          <Button variant="outline" onClick={() => runAction('prioritize')}><TimerReset className="mr-2 h-4 w-4" />Prioritize aging shipments</Button>
          <Button variant="outline" onClick={() => runAction('escalate')}><ShieldAlert className="mr-2 h-4 w-4" />Escalate issues</Button>
          {isAdmin && <Button variant="outline" onClick={() => setBranchId('')}><Users className="mr-2 h-4 w-4" />Reset to all branches</Button>}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="rounded-[22px]"><CardContent className="pt-4"><p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">Attempt trend</p><p className="mt-1 text-2xl font-semibold"><TrendingUp className="mr-1 inline h-5 w-5" />{snapshot?.snapshot.attempt_success_rate_percent ?? 0}% success</p></CardContent></Card>
        <Card className="rounded-[22px]"><CardContent className="pt-4"><p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">Failure trend</p><p className="mt-1 text-2xl font-semibold"><TrendingDown className="mr-1 inline h-5 w-5" />{snapshot?.snapshot.attempt_failure_rate_percent ?? 0}% failure</p></CardContent></Card>
        <Card className="rounded-[22px]"><CardContent className="pt-4"><p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">On-hand inventory</p><p className="mt-1 text-2xl font-semibold">{snapshot?.snapshot.inventory_on_hand_units ?? 0}</p></CardContent></Card>
      </div>
    </div>
  );
}
