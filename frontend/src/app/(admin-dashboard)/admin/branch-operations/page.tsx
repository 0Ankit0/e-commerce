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
              <Button key={branch.id} variant={branch.id === selectedBranchId ? 'default' : 'outline'} onClick={() => setSelectedBranchId(branch.id)}>
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
                <Button key={status} variant={shipmentFilter === status ? 'default' : 'outline'} size="sm" onClick={() => setShipmentFilter(status)}>
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
            <CardTitle>Agent history & supervisor actions</CardTitle>
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
    </div>
  );
}
