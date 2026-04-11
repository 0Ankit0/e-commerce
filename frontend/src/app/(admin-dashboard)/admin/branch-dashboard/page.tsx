'use client';

import { useMemo, useState } from 'react';
import { Download } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBranchDashboardDrilldown, useBranchDashboardSnapshot } from '@/hooks/use-observability';
import { apiClient } from '@/lib/api-client';

function toExportFileName() {
  const today = new Date().toISOString().slice(0, 10);
  return `branch-dashboard-${today}.csv`;
}

export default function AdminBranchDashboardPage() {
  const [branchId, setBranchId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const filters = useMemo(
    () => ({
      branch_id: branchId || undefined,
      agent_id: agentId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
    [agentId, branchId, dateFrom, dateTo],
  );

  const { data: snapshot, isLoading: snapshotLoading } = useBranchDashboardSnapshot(filters);
  const { data: drilldown, isLoading: drilldownLoading } = useBranchDashboardDrilldown(filters);

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Branch KPI Dashboard</h1>
          <p className="mt-1 max-w-3xl text-sm text-[var(--text-secondary)]">
            Branch-level inventory, productivity, delivery outcomes, and backlog with drilldowns and CSV export.
          </p>
        </div>
        <Button onClick={handleExport} variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      <Card className="rounded-[24px]">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Keep filters aligned across cards, charts, and CSV exports.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <select value={branchId} onChange={(event) => setBranchId(event.target.value)} className="rounded-lg border px-3 py-2 text-sm">
            <option value="">All branches</option>
            {branchOptions.map(([id, code]) => (
              <option key={id} value={id}>{code}</option>
            ))}
          </select>
          <input value={agentId} onChange={(event) => setAgentId(event.target.value)} placeholder="Agent ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ['Inventory units moved', snapshot?.snapshot.total_moved_units ?? 0],
          ['Agent productivity (completed)', snapshot?.snapshot.completed_pickups ?? 0],
          ['Delivery failures', snapshot?.snapshot.failed_deliveries ?? 0],
          ['Backlog', snapshot?.snapshot.backlog_shipments ?? 0],
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
            <CardTitle>Trend summary</CardTitle>
            <CardDescription>Delivery outcomes and backlog shape.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {snapshotLoading ? <p className="text-[var(--text-muted)]">Loading…</p> : (
              <>
                <p>Delivery success rate: <strong>{snapshot?.snapshot.delivery_success_rate_percent ?? 0}%</strong></p>
                <p>Open exceptions: <strong>{snapshot?.snapshot.open_exceptions ?? 0}</strong></p>
                <p>Pending pickups: <strong>{drilldown?.backlog.pending_pickups ?? 0}</strong></p>
                <p>Inventory movement types tracked: <strong>{Object.keys(drilldown?.inventory_flow ?? {}).length}</strong></p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
