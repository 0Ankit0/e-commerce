import type {
  AgentActivity,
  BranchAgent,
  BranchException,
  BranchKpiResult,
  BranchOperationsSnapshot,
  BranchSupervisorRole,
  ReportingBoundary,
  ShipmentHistoryEvent,
} from '@/types/branch-operations';

function toDateKeyInTimezone(date: Date, timezone: string): string {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return formatter.format(date);
}

function getHourInTimezone(date: Date, timezone: string): number {
  const formatter = new Intl.DateTimeFormat('en-US', { timeZone: timezone, hour: '2-digit', hour12: false });
  return Number(formatter.format(date));
}

function dayBefore(dateKey: string): string {
  const [year, month, day] = dateKey.split('-').map(Number);
  const utcDate = new Date(Date.UTC(year, month - 1, day));
  utcDate.setUTCDate(utcDate.getUTCDate() - 1);
  return `${utcDate.getUTCFullYear()}-${String(utcDate.getUTCMonth() + 1).padStart(2, '0')}-${String(utcDate.getUTCDate()).padStart(2, '0')}`;
}

function resolveOperationalDate(timestamp: string, boundary: ReportingBoundary): string {
  const date = new Date(timestamp);
  const dateKey = toDateKeyInTimezone(date, boundary.timezone);
  const hour = getHourInTimezone(date, boundary.timezone);
  return hour < boundary.cutoffHourLocal ? dayBefore(dateKey) : dateKey;
}

export function computeBranchKpis(
  branchId: string,
  snapshot: BranchOperationsSnapshot,
  boundary: ReportingBoundary,
): BranchKpiResult {
  const branchShipments = snapshot.shipments.filter((shipment) => shipment.branchId === branchId);
  const asOfDate = boundary.asOfDate ?? toDateKeyInTimezone(new Date(), boundary.timezone);

  const inWindow = branchShipments.filter((event) => resolveOperationalDate(event.timestamp, boundary) <= asOfDate);
  const delivered = inWindow.filter((event) => event.status === 'delivered').length;
  const failed = inWindow.filter((event) => event.status === 'failed').length;

  const activeAgents = snapshot.agents.filter((agent) => agent.branchId === branchId && agent.active).length;
  const openExceptions = snapshot.exceptions.filter((exception) => exception.branchId === branchId && exception.status === 'open').length;
  const slaBreaches = snapshot.exceptions.filter(
    (exception) => exception.branchId === branchId && exception.status === 'open' && hoursSince(exception.createdAt) > 4,
  ).length;

  const total = inWindow.length;
  const failureRate = total > 0 ? Number(((failed / total) * 100).toFixed(2)) : 0;
  const avgDeliveriesPerActiveAgent = activeAgents > 0 ? Number((delivered / activeAgents).toFixed(2)) : 0;

  const failedByDay = new Map<string, number>();
  for (const shipment of inWindow) {
    if (shipment.status !== 'failed') continue;
    const dayKey = resolveOperationalDate(shipment.timestamp, boundary);
    failedByDay.set(dayKey, (failedByDay.get(dayKey) ?? 0) + 1);
  }

  const failedDeliveryTrend = [...failedByDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, failedCount]) => ({ date, failed: failedCount }));

  const alerts: string[] = [];
  if (failureRate >= 15) alerts.push('Failure rate exceeded 15% threshold.');
  if (slaBreaches > 0) alerts.push(`${slaBreaches} unresolved exception(s) breached SLA.`);
  if (activeAgents === 0) alerts.push('No active agents available in this branch.');

  return {
    branchId,
    asOfDate,
    kpi: {
      totalShipments: total,
      deliveredShipments: delivered,
      failedDeliveries: failed,
      failureRate,
      avgDeliveriesPerActiveAgent,
      openExceptions,
      slaBreaches,
    },
    failedDeliveryTrend,
    alerts,
  };
}

function hoursSince(timestamp: string): number {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  return (now - then) / (1000 * 60 * 60);
}

export function canPerformSupervisorAction(role: BranchSupervisorRole, userBranchId: string | null, targetBranchId: string): boolean {
  if (role === 'admin') return true;
  if (role === 'branch_supervisor' && userBranchId === targetBranchId) return true;
  return false;
}

export function deactivateAgentWithGuardrails(agent: BranchAgent, activeAssignments: ShipmentHistoryEvent[], reassignmentAgentId?: string) {
  if (!agent.active) {
    return { ok: true, warnings: ['Agent is already inactive.'], reassignmentsRequired: 0 };
  }

  const assignmentsToMove = activeAssignments.filter(
    (assignment) => assignment.agentId === agent.id && (assignment.status === 'assigned' || assignment.status === 'in_transit'),
  );

  if (assignmentsToMove.length > 0 && !reassignmentAgentId) {
    return {
      ok: false,
      warnings: ['Agent has active assignments and cannot be deactivated without reassignment.'],
      reassignmentsRequired: assignmentsToMove.length,
    };
  }

  return {
    ok: true,
    warnings: assignmentsToMove.length > 0 ? [`${assignmentsToMove.length} assignment(s) should be reassigned.`] : [],
    reassignmentsRequired: assignmentsToMove.length,
  };
}

export function transferShipmentBranch(event: ShipmentHistoryEvent, targetBranchId: string, reason: string): ShipmentHistoryEvent {
  return {
    ...event,
    branchId: targetBranchId,
    status: 'branch_transfer',
    notes: reason,
    timestamp: new Date().toISOString(),
  };
}

export function rebalanceShift(
  agents: BranchAgent[],
  history: AgentActivity[],
  targetShift: BranchAgent['shift'],
  moveCount: number,
): string[] {
  const overloadedAgents = agents
    .filter((agent) => agent.active && agent.shift !== targetShift)
    .sort((a, b) => {
      const aLoad = history.filter((event) => event.agentId === a.id && event.eventType === 'assignment').length;
      const bLoad = history.filter((event) => event.agentId === b.id && event.eventType === 'assignment').length;
      return bLoad - aLoad;
    })
    .slice(0, moveCount);

  return overloadedAgents.map((agent) => agent.id);
}

export function triageException(exception: BranchException): BranchException {
  if (exception.status !== 'open') return exception;
  return {
    ...exception,
    status: 'triaged',
    triagedAt: new Date().toISOString(),
  };
}
