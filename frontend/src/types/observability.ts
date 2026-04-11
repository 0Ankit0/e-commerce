export interface ObservabilityLogEntry {
  id: string;
  timestamp: string;
  level: string;
  logger_name: string;
  source: string;
  message: string;
  event_code: string;
  request_id: string;
  method: string;
  path: string;
  status_code?: number | null;
  duration_ms?: number | null;
  user_id?: string | null;
  ip_address: string;
  user_agent: string;
  metadata: Record<string, unknown>;
}

export interface ObservabilityLogSummary {
  total_logs_24h: number;
  info_logs_24h: number;
  warning_logs_24h: number;
  error_logs_24h: number;
  open_incidents: number;
  acknowledged_incidents: number;
  critical_incidents: number;
}

export interface SecurityIncident {
  id: string;
  signal_type: string;
  severity: string;
  status: string;
  title: string;
  summary: string;
  fingerprint: string;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  actor_user_id?: string | null;
  subject_user_id?: string | null;
  ip_address: string;
  related_log_id?: string | null;
  metadata: Record<string, unknown>;
  review_notes: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
}

export interface SecurityIncidentStatusUpdate {
  status: 'acknowledged' | 'resolved';
  review_notes?: string;
}

export interface BranchKpiSnapshot {
  inventory_movements: number;
  total_moved_units: number;
  agent_count: number;
  active_agent_count: number;
  pickup_jobs: number;
  completed_pickups: number;
  reverse_pickups: number;
  reverse_completed: number;
  open_exceptions: number;
  failed_deliveries: number;
  delivery_success_rate_percent: number;
  delivery_attempts: number;
  backlog_shipments: number;
}

export interface BranchDashboardSnapshotResponse {
  snapshot: BranchKpiSnapshot;
  branch_scope: string[];
  date_from?: string | null;
  date_to?: string | null;
  agent_id?: string | null;
  branch_codes: Record<string, string>;
}

export interface BranchDashboardDrilldownResponse {
  productivity: Array<{
    agent_id: string;
    agent_name: string;
    assigned: number;
    completed: number;
    failed: number;
  }>;
  delivery_outcomes: {
    success: number;
    failed: number;
  };
  backlog: {
    pending_pickups: number;
    open_exceptions: number;
  };
  inventory_flow: Record<string, number>;
}
