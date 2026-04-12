'use client';

import { useMemo, useState } from 'react';
import { RefreshCcw } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useCurrentUser } from '@/hooks/use-users';
import { useHubOperationalReports } from '@/hooks/use-observability';

type WorkbenchQueue = {
  queue_id: string;
  code: string;
  status: string;
  manifest_id: string | null;
  created_at: string;
  closed_at: string | null;
};

type WorkbenchItem = {
  queue_item_id: string;
  shipment_id: string;
  status: string;
  scan_count: number;
  assigned_next_hub_id: string | null;
  assigned_carrier: string;
  assigned_vehicle_number: string;
  exception_code: string | null;
  updated_at: string;
};

type WorkbenchEvent = {
  event_id: string;
  operation_type: string;
  shipment_id: string | null;
  created_at: string;
};

type HubWorkbenchResponse = {
  selected_queue_id: string | null;
  queues: WorkbenchQueue[];
  inbound_items: WorkbenchItem[];
  hold_exception_items?: WorkbenchItem[];
  sorting_lanes?: Array<{ lane: string; items: WorkbenchItem[] }>;
  outbound_items: WorkbenchItem[];
  timeline: WorkbenchEvent[];
};

export default function HubOperationsPage() {
  const [hubId, setHubId] = useState('');
  const [queueId, setQueueId] = useState('');
  const [shipmentIdsCsv, setShipmentIdsCsv] = useState('');
  const [carrier, setCarrier] = useState('LinehaulX');
  const [vehicleNumber, setVehicleNumber] = useState('VEH-01');
  const [workbench, setWorkbench] = useState<HubWorkbenchResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState('Load a hub to start inbound/outbound sort operations.');
  const [loading, setLoading] = useState(false);
  const { data: currentUser } = useCurrentUser();
  const canRunBulkActions = Boolean(currentUser?.is_superuser || currentUser?.roles?.includes('hub_supervisor'));
  const { data: operationalReports } = useHubOperationalReports(hubId || null);

  const shipmentIds = useMemo(
    () => shipmentIdsCsv.split(',').map((entry) => entry.trim()).filter(Boolean),
    [shipmentIdsCsv],
  );

  const activeQueueId = queueId || workbench?.selected_queue_id || '';

  const refreshWorkbench = async (nextQueueId?: string) => {
    if (!hubId.trim()) {
      setStatusMessage('Hub ID is required.');
      return;
    }
    setLoading(true);
    try {
      const response = await apiClient.get<HubWorkbenchResponse>(`/logistics/hubs/${hubId.trim()}/sort-workbench`, {
        params: nextQueueId ? { queue_id: nextQueueId } : undefined,
      });
      setWorkbench(response.data);
      setQueueId(nextQueueId || response.data.selected_queue_id || '');
      setStatusMessage('Sort workbench refreshed.');
    } catch {
      setStatusMessage('Failed to load sort workbench.');
    } finally {
      setLoading(false);
    }
  };

  const runBulkAction = async (path: 'bulk-scan' | 'bulk-assign' | 'bulk-move-next-leg' | 'bulk-actions') => {
    if (!hubId.trim() || !activeQueueId) {
      setStatusMessage('Hub ID and queue ID are required.');
      return;
    }
    if (shipmentIds.length === 0) {
      setStatusMessage('Enter at least one shipment ID.');
      return;
    }
    if ((path === 'bulk-assign' || path === 'bulk-move-next-leg' || path === 'bulk-actions') && !canRunBulkActions) {
      setStatusMessage('You need hub supervisor/admin role for bulk operational actions.');
      return;
    }
    setLoading(true);
    try {
      if (path === 'bulk-scan') {
        const response = await apiClient.post(`/logistics/hubs/${hubId.trim()}/sort-queues/${activeQueueId}/bulk-scan`, {
          shipment_ids: shipmentIds,
          scan_code: 'inbound_scan',
        });
        setStatusMessage(`Bulk scan done: ${response.data.scanned_count} scanned, ${response.data.duplicate_count} duplicate.`);
      }
      if (path === 'bulk-assign') {
        const response = await apiClient.post(`/logistics/hubs/${hubId.trim()}/sort-queues/${activeQueueId}/bulk-assign`, {
          shipment_ids: shipmentIds,
          carrier,
          vehicle_number: vehicleNumber,
        });
        setStatusMessage(`Bulk assign done: ${response.data.assigned_count} assigned, ${response.data.idempotent_skip_count} skipped.`);
      }
      if (path === 'bulk-move-next-leg') {
        const response = await apiClient.post(`/logistics/hubs/${hubId.trim()}/sort-queues/${activeQueueId}/bulk-move-next-leg`, {
          shipment_ids: shipmentIds,
          carrier,
          vehicle_number: vehicleNumber,
          carrier_ready: true,
          vehicle_ready: true,
        });
        setStatusMessage(`Bulk dispatch done: ${response.data.moved_count} moved, ${response.data.already_moved_count} already moved.`);
      }
      if (path === 'bulk-actions') {
        const response = await apiClient.post(`/logistics/hubs/${hubId.trim()}/sort-queues/${activeQueueId}/bulk-actions`, {
          shipment_ids: shipmentIds,
          action: 'hold',
          exception_code: 'manual_hold',
          notes: 'Held from admin hub console',
        });
        setStatusMessage(`Bulk hold done for ${response.data.updated_count} shipments.`);
      }
      await refreshWorkbench(activeQueueId);
    } catch {
      setStatusMessage('Bulk action failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Hub inbound/outbound sort workbench</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Operate inbound queue, lanes, missorts, and dispatch groups in real time.</p>
        </div>
        <Button variant="outline" onClick={() => refreshWorkbench(activeQueueId)} disabled={loading}>
          <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workbench context</CardTitle>
          <CardDescription>Provide hub/queue context and shipment IDs for bulk operations.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <Input placeholder="Hub ID" value={hubId} onChange={(event) => setHubId(event.target.value)} />
          <Input placeholder="Queue ID (optional)" value={queueId} onChange={(event) => setQueueId(event.target.value)} />
          <Input placeholder="Carrier" value={carrier} onChange={(event) => setCarrier(event.target.value)} />
          <Input placeholder="Vehicle number" value={vehicleNumber} onChange={(event) => setVehicleNumber(event.target.value)} />
          <div className="md:col-span-2 lg:col-span-4">
            <Input
              placeholder="Shipment IDs (comma-separated)"
              value={shipmentIdsCsv}
              onChange={(event) => setShipmentIdsCsv(event.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2 md:col-span-2 lg:col-span-4">
            <Button onClick={() => runBulkAction('bulk-scan')} disabled={loading}>Bulk scan</Button>
            <Button variant="outline" onClick={() => runBulkAction('bulk-assign')} disabled={loading}>Bulk sort/assign</Button>
            <Button variant="secondary" onClick={() => runBulkAction('bulk-move-next-leg')} disabled={loading}>Bulk dispatch</Button>
            <Button variant="destructive" onClick={() => runBulkAction('bulk-actions')} disabled={loading}>Bulk hold</Button>
          </div>
          <p className="text-sm text-[var(--text-secondary)] md:col-span-2 lg:col-span-4">{statusMessage}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Queues</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {workbench?.queues.map((queue) => (
              <button
                key={queue.queue_id}
                className="w-full rounded-lg border border-[var(--border-color)] px-3 py-2 text-left"
                onClick={() => refreshWorkbench(queue.queue_id)}
              >
                <p className="font-medium">{queue.code}</p>
                <p className="text-xs text-[var(--text-muted)]">{queue.status}</p>
              </button>
            )) ?? <p className="text-[var(--text-muted)]">No queues loaded.</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Inbound</CardTitle>
            <CardDescription>Inbound queue and blocked parcels.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {workbench?.inbound_items.map((item) => (
              <div key={item.queue_item_id} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                <p className="font-medium">{item.shipment_id}</p>
                <p>{item.status}</p>
                {item.exception_code && <p className="text-xs text-amber-600">{item.exception_code}</p>}
              </div>
            )) ?? <p className="text-[var(--text-muted)]">No inbound items.</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active lanes + timeline</CardTitle>
            <CardDescription>Lane/bin assignments, dispatch groups, and latest events.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {(workbench?.sorting_lanes ?? []).slice(0, 3).map((lane) => (
              <div key={lane.lane as string} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                <p className="font-medium">{lane.lane as string}</p>
                <p className="text-xs text-[var(--text-muted)]">{(lane.items as WorkbenchItem[]).length} parcels</p>
              </div>
            ))}
            {(workbench?.outbound_items ?? []).slice(0, 3).map((item) => (
              <div key={item.queue_item_id} className="rounded-lg border border-[var(--border-color)] px-3 py-2">
                <p className="font-medium">{item.shipment_id}</p>
                <p>{item.status}</p>
                <p className="text-xs text-[var(--text-muted)]">{item.assigned_carrier} / {item.assigned_vehicle_number}</p>
              </div>
            ))}
            <div className="border-t border-[var(--border-color)] pt-2">
              {(workbench?.timeline ?? []).slice(0, 6).map((event) => (
                <p key={event.event_id} className="text-xs text-[var(--text-secondary)]">{event.operation_type} · {event.shipment_id ?? 'n/a'}</p>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-4">
        <Card><CardHeader><CardTitle>Dwell time</CardTitle></CardHeader><CardContent>{operationalReports?.dwell_time_minutes ?? 0} min</CardContent></Card>
        <Card><CardHeader><CardTitle>Lane throughput</CardTitle></CardHeader><CardContent>{JSON.stringify(operationalReports?.lane_throughput ?? {})}</CardContent></Card>
        <Card><CardHeader><CardTitle>SLA breaches</CardTitle></CardHeader><CardContent>{operationalReports?.sla_breach_shipments ?? 0}</CardContent></Card>
        <Card><CardHeader><CardTitle>Top exception</CardTitle></CardHeader><CardContent>{operationalReports?.top_exception_category ?? 'n/a'}</CardContent></Card>
      </div>
    </div>
  );
}
