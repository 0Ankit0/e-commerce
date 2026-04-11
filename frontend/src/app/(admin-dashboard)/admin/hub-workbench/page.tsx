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
  outbound_items: WorkbenchItem[];
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

  const sortedItems = useMemo(
    () => (workbench?.outbound_items ?? []).filter((item) => item.status === 'assigned'),
    [workbench?.outbound_items],
  );
  const outboundItems = useMemo(
    () => (workbench?.outbound_items ?? []).filter((item) => item.status === 'moved_to_next_leg'),
    [workbench?.outbound_items],
  );

  const load = async () => {
    if (!hubId.trim()) return;
    const [workbenchResponse, kpiResponse] = await Promise.all([
      apiClient.get<HubWorkbenchResponse>(`/logistics/hubs/${hubId.trim()}/sort-workbench`, {
        params: queueId ? { queue_id: queueId } : undefined,
      }),
      apiClient.get<HubKpiResponse>(`/logistics/hubs/${hubId.trim()}/kpi-dashboard`),
    ]);
    setWorkbench(workbenchResponse.data);
    setQueueId(queueId || workbenchResponse.data.selected_queue_id || '');
    setKpi(kpiResponse.data);
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

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Inbound queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(workbench?.inbound_items ?? []).map((item) => <p key={item.queue_item_id}>{item.shipment_id} · {item.status}</p>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Sorted queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {sortedItems.map((item) => <p key={item.queue_item_id}>{item.shipment_id} · {item.assigned_carrier}</p>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Outbound queue</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {outboundItems.map((item) => <p key={item.queue_item_id}>{item.shipment_id} · {item.assigned_vehicle_number}</p>)}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
