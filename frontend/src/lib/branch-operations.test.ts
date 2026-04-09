import { describe, expect, it } from 'vitest';
import {
  canPerformSupervisorAction,
  computeBranchKpis,
  deactivateAgentWithGuardrails,
  transferShipmentBranch,
} from './branch-operations';
import type { BranchOperationsSnapshot } from '@/types/branch-operations';

const snapshot: BranchOperationsSnapshot = {
  agents: [
    { id: 'a1', branchId: 'b1', name: 'Agent A', active: true, shift: 'morning' },
    { id: 'a2', branchId: 'b1', name: 'Agent B', active: true, shift: 'afternoon' },
  ],
  shipments: [
    { id: 'e1', shipmentId: 'S1', branchId: 'b1', agentId: 'a1', status: 'delivered', timestamp: '2026-04-08T01:45:00Z' },
    { id: 'e2', shipmentId: 'S2', branchId: 'b1', agentId: 'a1', status: 'failed', timestamp: '2026-04-08T05:30:00Z' },
    { id: 'e3', shipmentId: 'S3', branchId: 'b1', agentId: 'a2', status: 'failed', timestamp: '2026-04-08T08:00:00Z' },
  ],
  agentHistory: [],
  exceptions: [
    {
      id: 'x1',
      shipmentId: 'S2',
      branchId: 'b1',
      createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
      status: 'open',
      reason: 'Address unavailable',
    },
  ],
};

describe('branch operations KPI and permissions', () => {
  it('computes KPI totals and trends with timezone cutoff applied', () => {
    const result = computeBranchKpis('b1', snapshot, {
      timezone: 'Asia/Kathmandu',
      cutoffHourLocal: 6,
      asOfDate: '2026-04-08',
    });

    expect(result.kpi.totalShipments).toBe(3);
    expect(result.kpi.failedDeliveries).toBe(2);
    expect(result.kpi.failureRate).toBeCloseTo(66.67, 2);
    expect(result.kpi.avgDeliveriesPerActiveAgent).toBe(0.5);
    expect(result.kpi.slaBreaches).toBe(1);
    expect(result.failedDeliveryTrend.reduce((total, point) => total + point.failed, 0)).toBe(2);
  });

  it('enforces supervisor permissions by role and branch ownership', () => {
    expect(canPerformSupervisorAction('admin', null, 'b1')).toBe(true);
    expect(canPerformSupervisorAction('branch_supervisor', 'b1', 'b1')).toBe(true);
    expect(canPerformSupervisorAction('branch_supervisor', 'b2', 'b1')).toBe(false);
    expect(canPerformSupervisorAction('viewer', 'b1', 'b1')).toBe(false);
  });

  it('blocks agent deactivation when assignments are active without reassignment', () => {
    const guardrail = deactivateAgentWithGuardrails(snapshot.agents[0], [
      { ...snapshot.shipments[0], status: 'assigned' },
    ]);
    expect(guardrail.ok).toBe(false);
    expect(guardrail.reassignmentsRequired).toBe(1);
  });

  it('records a branch transfer event for mid-delivery handoff', () => {
    const transferred = transferShipmentBranch(snapshot.shipments[0], 'b2', 'Capacity overflow');
    expect(transferred.branchId).toBe('b2');
    expect(transferred.status).toBe('branch_transfer');
    expect(transferred.notes).toBe('Capacity overflow');
  });
});
