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
