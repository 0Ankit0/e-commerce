export interface CapabilitySummary {
  modules: Record<string, boolean>;
  active_providers: Record<string, string | null>;
  fallback_providers: Record<string, string[]>;
}

export interface ProviderStatus {
  channel: string;
  provider: string;
  active: boolean;
  enabled: boolean;
  configured: boolean;
  fallback: boolean;
}

export interface ProviderStatusResponse {
  providers: ProviderStatus[];
}

export interface PushProviderConfig {
  enabled: boolean;
  vapid_public_key?: string;
  project_id?: string;
  web_vapid_key?: string;
  api_key?: string;
  app_id?: string;
  messaging_sender_id?: string;
  auth_domain?: string;
  storage_bucket?: string;
  measurement_id?: string;
  web_app_id?: string;
}

export interface PushConfigResponse {
  provider: string | null;
  providers: {
    webpush: PushProviderConfig;
    fcm: PushProviderConfig;
    onesignal: PushProviderConfig;
  };
}

export interface MapProviderConfig {
  enabled: boolean;
  label: string;
  api_key?: string;
  map_id?: string;
}

export interface MapConfigResponse {
  enabled: boolean;
  provider: 'osm' | 'google' | null;
  default_center: {
    latitude: number;
    longitude: number;
    zoom: number;
  };
  providers: {
    osm: MapProviderConfig;
    google: MapProviderConfig;
  };
}

export interface ChannelQuotaPolicy {
  id: number;
  channel: string;
  scope: 'global' | 'tenant' | 'user' | 'tenant_user';
  tenant_id: number | null;
  user_id: number | null;
  limit_count: number;
  window_seconds: number;
  timezone: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChannelQuotaUsage {
  id: number;
  policy_id: number;
  window_start: string;
  window_end: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChannelQuotaAudit {
  id: number;
  policy_id: number;
  actor_user_id: number | null;
  action: string;
  reason: string;
  before_json: Record<string, unknown>;
  after_json: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface ChannelQuotaDashboardTotals {
  policies: number;
  active_policies: number;
  usage_rows: number;
  at_risk: number;
}

export interface ChannelQuotaDashboardItem {
  policy_id: number;
  scope: 'global' | 'tenant' | 'user' | 'tenant_user';
  tenant_id: number | null;
  user_id: number | null;
  enabled: boolean;
  limit_count: number;
  window_seconds: number;
  usage_count: number;
  utilization: number;
  window_end: string | null;
  seconds_until_reset: number | null;
}

export interface ChannelQuotaDashboardResponse {
  channel: string;
  totals: ChannelQuotaDashboardTotals;
  items: ChannelQuotaDashboardItem[];
}

export type EmailLifecycleStatus = 'queued' | 'sent' | 'delivered' | 'bounced' | 'failed' | 'complained';

export interface EmailDeliveryMessage {
  id: number;
  subject: string;
  template_name: string;
  status: EmailLifecycleStatus;
  provider: string | null;
  provider_message_id: string | null;
  attempt_count: number;
  max_attempts: number;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  queued_at: string;
  sent_at: string | null;
  delivered_at: string | null;
}

export interface EmailDeliveryDeadLetter {
  id: number;
  message_id: number;
  reason: string;
  created_at: string;
}

export interface DeliveryFailureReason {
  reason: string;
  count: number;
}

export interface EmailDeliveryAnalytics {
  total: number;
  status_counts: Partial<Record<EmailLifecycleStatus, number>>;
  delivery_rate: number;
  bounce_rate: number;
  failure_rate: number;
  failure_reasons: DeliveryFailureReason[];
}

export interface NotificationChannelPerformance {
  day: string;
  channel: string;
  total: number;
  delivered: number;
  failed: number;
  delivery_rate: number;
  failure_rate: number;
  avg_latency_ms: number;
}

export interface NotificationTemplatePerformance {
  day: string;
  template: string;
  channel: string;
  total: number;
  delivered: number;
  failed: number;
  delivery_rate: number;
  failure_rate: number;
}

export interface NotificationPerformanceResponse<T> {
  items: T[];
  total: number;
}


export interface SmsQuotaConfig {
  id: number;
  provider: string;
  per_user_daily_limit: number | null;
  per_ip_window_limit: number | null;
  ip_window_seconds: number;
  global_provider_daily_limit: number | null;
  privileged_override_enabled: boolean;
  updated_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface SmsQuotaViolationEvent {
  id: number;
  config_id: number | null;
  scope: string;
  provider: string | null;
  user_id: number | null;
  ip_address: string | null;
  limit_count: number;
  attempted_count: number;
  window_start: string;
  window_end: string;
  override_applied: boolean;
  reason: string;
  created_at: string;
}

export interface SmsQuotaDashboardResponse {
  provider: string;
  totals: {
    counters: number;
    violations: number;
    override_violations: number;
  };
  usage_by_scope: Record<string, number>;
  active_counters: ChannelQuotaUsage[];
}
