'use client';

import { useMemo, useState } from 'react';
import { AlertTriangle, ArrowRightLeft, ShieldCheck, UserRoundCog, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { BranchAgent, BranchException, BranchOperationsSnapshot, ShipmentHistoryEvent } from '@/types/branch-operations';
import {
  canPerformSupervisorAction,
  computeBranchKpis,
  deactivateAgentWithGuardrails,
  getAgentPerformance,
  getBranchInventorySummary,
  getInventoryMovementTrend,
  getSlaBreachTrend,
  rebalanceShift,
  transferShipmentBranch,
  triageException,
} from '@/lib/branch-operations';

const BRANCHES = [
  { id: 'branch-ktm', name: 'Kathmandu Central' },
  { id: 'branch-bkt', name: 'Bhaktapur East' },
];

const INITIAL_SNAPSHOT: BranchOperationsSnapshot = {
  agents: [
    { id: 'agent-a1', branchId: 'branch-ktm', name: 'Rider One', active: true, shift: 'morning' },
    { id: 'agent-a2', branchId: 'branch-ktm', name: 'Rider Two', active: true, shift: 'afternoon' },
    { id: 'agent-b1', branchId: 'branch-bkt', name: 'Rider Three', active: true, shift: 'morning' },
  ],
  shipments: [
    { id: 'evt-1', shipmentId: 'SHP-1001', branchId: 'branch-ktm', agentId: 'agent-a1', status: 'assigned', timestamp: '2026-04-08T03:15:00Z' },
    { id: 'evt-2', shipmentId: 'SHP-1002', branchId: 'branch-ktm', agentId: 'agent-a2', status: 'delivered', timestamp: '2026-04-08T07:10:00Z' },
    { id: 'evt-3', shipmentId: 'SHP-1003', branchId: 'branch-ktm', agentId: 'agent-a1', status: 'failed', timestamp: '2026-04-08T09:25:00Z' },
    { id: 'evt-4', shipmentId: 'SHP-2001', branchId: 'branch-bkt', agentId: 'agent-b1', status: 'delivered', timestamp: '2026-04-08T10:15:00Z' },
  ],
  agentHistory: [
    { id: 'ah-1', agentId: 'agent-a1', branchId: 'branch-ktm', eventType: 'assignment', shipmentId: 'SHP-1001', timestamp: '2026-04-08T03:15:00Z' },
    { id: 'ah-2', agentId: 'agent-a2', branchId: 'branch-ktm', eventType: 'delivery', shipmentId: 'SHP-1002', timestamp: '2026-04-08T07:10:00Z' },
    { id: 'ah-3', agentId: 'agent-a1', branchId: 'branch-ktm', eventType: 'failure', shipmentId: 'SHP-1003', timestamp: '2026-04-08T09:25:00Z' },
  ],
  exceptions: [
    {
      id: 'ex-1',
      shipmentId: 'SHP-1003',
      branchId: 'branch-ktm',
      agentId: 'agent-a1',
      createdAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      status: 'open',
      reason: 'Customer unavailable',
    },
    {
      id: 'ex-2',
      shipmentId: 'SHP-2002',
      branchId: 'branch-bkt',
      agentId: 'agent-b1',
      createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      status: 'open',
      reason: 'Building access delayed',
    },
  ],
  inventory: [
    { id: 'inv-1', branchId: 'branch-ktm', sku: 'SKU-HEADPHONE', name: 'Wireless Headphone', onHand: 14, reserved: 5, reorderPoint: 8 },
    { id: 'inv-2', branchId: 'branch-ktm', sku: 'SKU-ADAPTER', name: 'USB-C Adapter', onHand: 5, reserved: 4, reorderPoint: 6 },
    { id: 'inv-3', branchId: 'branch-bkt', sku: 'SKU-MOUSE', name: 'Ergo Mouse', onHand: 18, reserved: 3, reorderPoint: 5 },
  ],
  inventoryMovements: [
    { id: 'mv-1', branchId: 'branch-ktm', sku: 'SKU-HEADPHONE', quantity: 10, direction: 'in', timestamp: '2026-04-07T03:00:00Z', reason: 'Hub replenishment' },
    { id: 'mv-2', branchId: 'branch-ktm', sku: 'SKU-HEADPHONE', quantity: 7, direction: 'out', timestamp: '2026-04-07T12:00:00Z', reason: 'Shipment allocation' },
    { id: 'mv-3', branchId: 'branch-ktm', sku: 'SKU-ADAPTER', quantity: 12, direction: 'in', timestamp: '2026-04-08T02:30:00Z', reason: 'Vendor inbound' },
    { id: 'mv-4', branchId: 'branch-ktm', sku: 'SKU-ADAPTER', quantity: 9, direction: 'out', timestamp: '2026-04-08T08:30:00Z', reason: 'Shipment allocation' },
    { id: 'mv-5', branchId: 'branch-bkt', sku: 'SKU-MOUSE', quantity: 5, direction: 'out', timestamp: '2026-04-08T09:10:00Z', reason: 'Shipment allocation' },
  ],
};

export default function BranchOperationsPage() {
  const [snapshot, setSnapshot] = useState<BranchOperationsSnapshot>(INITIAL_SNAPSHOT);
  const [selectedBranchId, setSelectedBranchId] = useState(BRANCHES[0].id);
  const [shipmentFilter, setShipmentFilter] = useState<'all' | ShipmentHistoryEvent['status']>('all');
  const [agentFilter, setAgentFilter] = useState<'all' | string>('all');

  const userRole: 'admin' | 'branch_supervisor' | 'viewer' = 'admin';
  const userBranchId = 'branch-ktm';

  const kpi = useMemo(
    () =>
      computeBranchKpis(selectedBranchId, snapshot, {
        timezone: 'Asia/Kathmandu',
        cutoffHourLocal: 6,
        asOfDate: '2026-04-08',
      }),
    [selectedBranchId, snapshot],
  );

  const filteredShipments = snapshot.shipments.filter(
    (shipment) =>
      shipment.branchId === selectedBranchId &&
      (shipmentFilter === 'all' || shipment.status === shipmentFilter) &&
      (agentFilter === 'all' || shipment.agentId === agentFilter),
  );

  const selectedBranchAgents = snapshot.agents.filter((agent) => agent.branchId === selectedBranchId);
  const selectedBranchHistory = snapshot.agentHistory.filter((event) => event.branchId === selectedBranchId);
  const selectedBranchExceptions = snapshot.exceptions.filter((exception) => exception.branchId === selectedBranchId);
  const inventorySummary = getBranchInventorySummary(selectedBranchId, snapshot.inventory ?? []);
  const agentPerformance = getAgentPerformance(selectedBranchId, snapshot.agents, snapshot.shipments);
  const inventoryTrend = getInventoryMovementTrend(selectedBranchId, snapshot.inventoryMovements ?? [], {
    timezone: 'Asia/Kathmandu',
    cutoffHourLocal: 6,
    asOfDate: '2026-04-08',
  });
  const slaTrend = getSlaBreachTrend(selectedBranchId, snapshot.exceptions, {
    timezone: 'Asia/Kathmandu',
    cutoffHourLocal: 6,
    asOfDate: '2026-04-08',
  });

  const canManage = canPerformSupervisorAction(userRole, userBranchId, selectedBranchId);

  const handleReassign = (shipmentId: string, targetAgentId: string) => {
    if (!canManage) return;
    setSnapshot((prev) => ({
      ...prev,
      shipments: prev.shipments.map((event) =>
        event.shipmentId === shipmentId
          ? { ...event, status: 'reassigned', agentId: targetAgentId, timestamp: new Date().toISOString() }
          : event,
      ),
    }));
  };

  const handleShiftBalance = () => {
    if (!canManage) return;
    const movedAgentIds = rebalanceShift(selectedBranchAgents, selectedBranchHistory, 'morning', 1);
    if (movedAgentIds.length === 0) return;
    setSnapshot((prev) => ({
      ...prev,
      agents: prev.agents.map((agent) => (movedAgentIds.includes(agent.id) ? { ...agent, shift: 'morning' } : agent)),
    }));
  };

  const handleTriage = (exception: BranchException) => {
    if (!canManage) return;
    setSnapshot((prev) => ({
      ...prev,
      exceptions: prev.exceptions.map((item) => (item.id === exception.id ? triageException(item) : item)),
    }));
  };

  const handleDeactivateAgent = (agent: BranchAgent) => {
    if (!canManage) return;
    const guardrail = deactivateAgentWithGuardrails(agent, snapshot.shipments, selectedBranchAgents.find((a) => a.id !== agent.id)?.id);
    if (!guardrail.ok) return;
    setSnapshot((prev) => ({ ...prev, agents: prev.agents.map((item) => (item.id === agent.id ? { ...item, active: false } : item)) }));
  };

  const handleTransferShipment = (shipment: ShipmentHistoryEvent) => {
    if (!canManage) return;
    const targetBranch = BRANCHES.find((branch) => branch.id !== selectedBranchId);
    if (!targetBranch) return;
    setSnapshot((prev) => ({
      ...prev,
      shipments: prev.shipments.map((event) =>
        event.id === shipment.id ? transferShipmentBranch(event, targetBranch.id, 'Transferred mid-delivery for capacity balancing') : event,
      ),
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Control Plane</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Branch Operations</h1>
          <p className="mt-1 max-w-3xl text-sm text-[var(--text-secondary)]">
            Monitor branch inventory state, agent productivity, failed delivery trends, SLA alerts, and act on delivery exceptions.
          </p>
        </div>
      </div>

      <Card className="rounded-[24px]">
        <CardContent className="pt-5">
          <div className="flex flex-wrap gap-2">
            {BRANCHES.map((branch) => (
                <Button key={branch.id} variant={branch.id === selectedBranchId ? 'primary' : 'outline'} onClick={() => setSelectedBranchId(branch.id)}>
                {branch.name}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[{ label: 'Shipments', value: kpi.kpi.totalShipments }, { label: 'Failed deliveries', value: kpi.kpi.failedDeliveries }, { label: 'Open exceptions', value: kpi.kpi.openExceptions }, { label: 'SLA breaches', value: kpi.kpi.slaBreaches }].map((item) => (
          <Card key={item.label} className="rounded-[22px]">
            <CardContent className="pt-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{item.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Inventory SKUs', value: inventorySummary.skuCount },
          { label: 'Low-stock SKUs', value: inventorySummary.lowStockCount },
          { label: 'On-hand units', value: inventorySummary.totalOnHand },
          { label: 'Reserved units', value: inventorySummary.totalReserved },
        ].map((item) => (
          <Card key={item.label} className="rounded-[22px]">
            <CardContent className="pt-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{item.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {kpi.alerts.length > 0 && (
        <Card className="rounded-[24px] border-amber-200 bg-amber-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-900"><AlertTriangle className="h-4 w-4" />SLA Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm text-amber-900">
              {kpi.alerts.map((alert) => <li key={alert}>• {alert}</li>)}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[24px]">
          <CardHeader>
            <CardTitle>Shipment drill-down</CardTitle>
            <CardDescription>Filter branch shipments by status and assigned agent.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {(['all', 'assigned', 'delivered', 'failed', 'branch_transfer', 'reassigned'] as const).map((status) => (
                <Button key={status} variant={shipmentFilter === status ? 'primary' : 'outline'} size="sm" onClick={() => setShipmentFilter(status)}>
                  {status}
                </Button>
              ))}
              <select
                value={agentFilter}
                onChange={(event) => setAgentFilter(event.target.value)}
                className="rounded-lg border border-[var(--border-color)] px-3 py-1 text-sm"
              >
                <option value="all">All agents</option>
                {selectedBranchAgents.map((agent) => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
              </select>
            </div>
            <ul className="space-y-2">
              {filteredShipments.map((shipment) => (
                <li key={shipment.id} className="rounded-xl border border-[var(--border-color)] p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold">{shipment.shipmentId}</p>
                    <span className="rounded-full bg-[var(--surface-subtle)] px-2 py-0.5 text-xs">{shipment.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">Agent: {shipment.agentId ?? 'Unassigned'} · {new Date(shipment.timestamp).toLocaleString()}</p>
                  {canManage && shipment.status !== 'delivered' && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => handleReassign(shipment.shipmentId, selectedBranchAgents[0]?.id ?? '')}>
                        <UserRoundCog className="mr-1.5 h-3.5 w-3.5" /> Reassign
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleTransferShipment(shipment)}>
                        <ArrowRightLeft className="mr-1.5 h-3.5 w-3.5" /> Transfer branch
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card className="rounded-[24px]">
          <CardHeader>
            <CardTitle>Agent controls & exception triage</CardTitle>
            <CardDescription>Shift balancing, deactivation guardrails, and exception triage.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={handleShiftBalance} disabled={!canManage}>
                <Users className="mr-1.5 h-3.5 w-3.5" /> Shift balance
              </Button>
            </div>
            <ul className="space-y-2">
              {selectedBranchAgents.map((agent) => (
                <li key={agent.id} className="flex items-center justify-between rounded-xl border border-[var(--border-color)] p-3 text-sm">
                  <div>
                    <p className="font-semibold">{agent.name}</p>
                    <p className="text-xs text-[var(--text-muted)]">Shift: {agent.shift} · {agent.active ? 'Active' : 'Inactive'}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => handleDeactivateAgent(agent)} disabled={!canManage || !agent.active}>Deactivate</Button>
                </li>
              ))}
            </ul>
            <div className="space-y-2">
              {selectedBranchExceptions.map((exception) => (
                <div key={exception.id} className="rounded-xl border border-[var(--border-color)] p-3 text-sm">
                  <p className="font-semibold">{exception.shipmentId}</p>
                  <p className="text-xs text-[var(--text-muted)]">{exception.reason} · {exception.status}</p>
                  <Button size="sm" variant="outline" className="mt-2" disabled={!canManage || exception.status !== 'open'} onClick={() => handleTriage(exception)}>
                    <ShieldCheck className="mr-1.5 h-3.5 w-3.5" /> Triage exception
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="rounded-[24px] xl:col-span-2">
          <CardHeader>
            <CardTitle>Agent performance leaderboard</CardTitle>
            <CardDescription>Per-branch delivery output and success rate by agent.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-color)] text-xs uppercase tracking-[0.12em] text-[var(--text-muted)]">
                    <th className="px-2 py-2">Agent</th>
                    <th className="px-2 py-2">Shift</th>
                    <th className="px-2 py-2">Delivered</th>
                    <th className="px-2 py-2">Failed</th>
                    <th className="px-2 py-2">Open assignments</th>
                    <th className="px-2 py-2">Success</th>
                  </tr>
                </thead>
                <tbody>
                  {agentPerformance.map((agent) => (
                    <tr key={agent.agentId} className="border-b border-[var(--border-color)]">
                      <td className="px-2 py-2 font-medium">{agent.name}</td>
                      <td className="px-2 py-2">{agent.shift}</td>
                      <td className="px-2 py-2">{agent.delivered}</td>
                      <td className="px-2 py-2">{agent.failed}</td>
                      <td className="px-2 py-2">{agent.openAssignments}</td>
                      <td className="px-2 py-2">{agent.successRate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[24px]">
          <CardHeader>
            <CardTitle>Branch report snapshot</CardTitle>
            <CardDescription>Daily trend drill-downs for inventory flow and SLA breaches.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">Inventory movement trend</p>
              <ul className="mt-2 space-y-1">
                {inventoryTrend.map((point) => (
                  <li key={point.date} className="flex items-center justify-between rounded-lg border border-[var(--border-color)] px-2 py-1.5">
                    <span>{point.date}</span>
                    <span>IN {point.inbound} / OUT {point.outbound}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">SLA breach trend</p>
              <ul className="mt-2 space-y-1">
                {slaTrend.length === 0 ? (
                  <li className="rounded-lg border border-[var(--border-color)] px-2 py-1.5 text-[var(--text-muted)]">No breaches in the selected operational window.</li>
                ) : (
                  slaTrend.map((point) => (
                    <li key={point.date} className="flex items-center justify-between rounded-lg border border-[var(--border-color)] px-2 py-1.5">
                      <span>{point.date}</span>
                      <span>{point.breaches} breach(es)</span>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
