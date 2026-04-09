export type BranchSupervisorRole = 'admin' | 'branch_supervisor' | 'viewer';

export interface BranchAgent {
  id: string;
  branchId: string;
  name: string;
  active: boolean;
  shift: 'morning' | 'afternoon' | 'evening';
}

export interface ShipmentHistoryEvent {
  id: string;
  shipmentId: string;
  branchId: string;
  agentId?: string;
  status: 'assigned' | 'in_transit' | 'delivered' | 'failed' | 'exception' | 'reassigned' | 'branch_transfer';
  timestamp: string;
  notes?: string;
}

export interface AgentActivity {
  id: string;
  agentId: string;
  branchId: string;
  eventType: 'assignment' | 'delivery' | 'failure' | 'exception' | 'deactivation';
  timestamp: string;
  shipmentId?: string;
}

export interface BranchException {
  id: string;
  shipmentId: string;
  branchId: string;
  agentId?: string;
  createdAt: string;
  triagedAt?: string;
  status: 'open' | 'triaged' | 'resolved';
  reason: string;
}

export interface BranchOperationsSnapshot {
  shipments: ShipmentHistoryEvent[];
  agentHistory: AgentActivity[];
  exceptions: BranchException[];
  agents: BranchAgent[];
}

export interface BranchKpi {
  totalShipments: number;
  deliveredShipments: number;
  failedDeliveries: number;
  failureRate: number;
  avgDeliveriesPerActiveAgent: number;
  openExceptions: number;
  slaBreaches: number;
}

export interface BranchKpiResult {
  branchId: string;
  asOfDate: string;
  kpi: BranchKpi;
  failedDeliveryTrend: Array<{ date: string; failed: number }>;
  alerts: string[];
}

export interface ReportingBoundary {
  timezone: string;
  cutoffHourLocal: number;
  asOfDate?: string;
}
