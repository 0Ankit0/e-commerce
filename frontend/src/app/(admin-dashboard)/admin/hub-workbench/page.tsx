'use client';

import { useMemo, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

type WorkbenchItem = {
  queue_item_id: string;
  shipment_id: string;
  status: string;
  assigned_carrier: string;
  assigned_vehicle_number: string;
};

type HubWorkbenchResponse = {
  selected_queue_id: string | null;
  inbound_items: WorkbenchItem[];
  hold_exception_items: WorkbenchItem[];
  sorting_lanes: { lane: string; items: WorkbenchItem[] }[];
  outbound_items: WorkbenchItem[];
  outbound_readiness_board: {
    ready_to_dispatch_count: number;
    dispatched_count: number;
    hold_count: number;
  };
  sla_timers: {
    average_dwell_minutes: number;
    average_sort_latency_minutes: number;
    cutoff_miss_shipments: number;
  };
  alerts: { type: string; severity: string; count: number }[];
};

type HubKpiResponse = {
  throughput_shipments: number;
  average_dwell_time_minutes: number;
  sla_breach_shipments: number;
};

export default function AdminHubWorkbenchPage() {
  const [hubId, setHubId] = useState('');
  const [queueId, setQueueId] = useState('');
  const [workbench, setWorkbench] = useState<HubWorkbenchResponse | null>(null);
  const [kpi, setKpi] = useState<HubKpiResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const outboundItems = useMemo(
    () => (workbench?.outbound_items ?? []).filter((item) => item.status === 'moved_to_next_leg'),
    [workbench?.outbound_items],
  );

  const load = async () => {
    if (!hubId.trim()) return;
    setLoading(true);
    const [workbenchResponse, kpiResponse] = await Promise.all([
      apiClient.get<HubWorkbenchResponse>(`/logistics/hubs/${hubId.trim()}/sort-workbench`, {
        params: queueId ? { queue_id: queueId } : undefined,
      }),
      apiClient.get<HubKpiResponse>(`/logistics/hubs/${hubId.trim()}/kpi-dashboard`),
    ]);
    setWorkbench(workbenchResponse.data);
    setQueueId(queueId || workbenchResponse.data.selected_queue_id || '');
    setKpi(kpiResponse.data);
    setLoading(false);
  };

  const requeueMisSort = async (shipmentId: string) => {
    if (!hubId.trim() || !queueId.trim()) return;
    await apiClient.post(`/logistics/hubs/${hubId.trim()}/sort-queues/${queueId.trim()}/exception-queue`, {
      shipment_id: shipmentId,
      exception_code: 'mis_sort_corrected',
      notes: 'Requeued from hold queue by sorter',
      requeue_for_sorting: true,
    });
    await load();
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Hub operations</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Hub workbench</h1>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Context</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Input placeholder="Hub ID" value={hubId} onChange={(event) => setHubId(event.target.value)} />
          <Input placeholder="Queue ID (optional)" value={queueId} onChange={(event) => setQueueId(event.target.value)} />
          <Button onClick={load}>Load queues</Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle>Throughput</CardTitle></CardHeader><CardContent>{kpi?.throughput_shipments ?? 0}</CardContent></Card>
        <Card><CardHeader><CardTitle>Avg dwell (min)</CardTitle></CardHeader><CardContent>{kpi?.average_dwell_time_minutes ?? 0}</CardContent></Card>
        <Card><CardHeader><CardTitle>SLA breaches</CardTitle></CardHeader><CardContent>{kpi?.sla_breach_shipments ?? 0}</CardContent></Card>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle>Sort latency (min)</CardTitle></CardHeader><CardContent>{workbench?.sla_timers.average_sort_latency_minutes ?? 0}</CardContent></Card>
        <Card><CardHeader><CardTitle>Cutoff misses</CardTitle></CardHeader><CardContent>{workbench?.sla_timers.cutoff_miss_shipments ?? 0}</CardContent></Card>
        <Card><CardHeader><CardTitle>Alerts</CardTitle></CardHeader><CardContent>{workbench?.alerts.map((a) => `${a.type}:${a.count}`).join(', ') || 'None'}</CardContent></Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <Card>
          <CardHeader><CardTitle>Inbound queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(workbench?.inbound_items ?? []).map((item) => <p key={item.queue_item_id}>{item.shipment_id} · {item.status}</p>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Sorting lanes</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(workbench?.sorting_lanes ?? []).map((lane) => <p key={lane.lane}>{lane.lane} · {lane.items.length}</p>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Mis-sort / hold queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(workbench?.hold_exception_items ?? []).map((item) => (
              <div className="flex items-center justify-between gap-2" key={item.queue_item_id}>
                <span>{item.shipment_id} · {item.status}</span>
                <Button size="sm" variant="secondary" onClick={() => requeueMisSort(item.shipment_id)}>Requeue</Button>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Outbound readiness</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>Ready: {workbench?.outbound_readiness_board.ready_to_dispatch_count ?? 0}</p>
            <p>Dispatched: {workbench?.outbound_readiness_board.dispatched_count ?? 0}</p>
            <p>Hold: {workbench?.outbound_readiness_board.hold_count ?? 0}</p>
            {outboundItems.slice(0, 4).map((item) => <p key={item.queue_item_id}>{item.shipment_id} · {item.assigned_vehicle_number}</p>)}
          </CardContent>
        </Card>
      </div>
      {loading ? <p className="text-sm text-[var(--text-muted)]">Loading live queue state...</p> : null}
    </div>
  );
}
