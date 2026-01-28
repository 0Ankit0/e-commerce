export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar?: string;
  otp_enabled?: boolean;
  otp_verified?: boolean;
}

export interface UserProfile {
  id: string;
  user: User;
  first_name: string;
  last_name: string;
  avatar?: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  type: 'organization' | 'individual';
}

export interface TenantMembership {
  id: string;
  user_id: string;
  tenant: Tenant;
  role: 'owner' | 'admin' | 'member';
  invitation_accepted: boolean;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupData {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface Notification {
  id: string;
  type: string;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface Subscription {
  id: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  trial_start?: string;
  trial_end?: string;
}

export interface PaymentMethod {
  id: string;
  type: string;
  card?: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  };
}
