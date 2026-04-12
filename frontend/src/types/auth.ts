// IAM / Auth module types

export interface User {
  id: string;
  username: string;
  email: string;
  created_at?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_confirmed: boolean;
  otp_enabled: boolean;
  otp_verified: boolean;
  first_name?: string;
  last_name?: string;
  phone?: string;
  image_url?: string;
  bio?: string;
  roles: string[];
}

export interface AuthTokens {
  access: string;
  refresh: string;
  token_type: string;
}

export interface LoginSuccessResponse extends AuthTokens {
  otp_recommended?: boolean;
  otp_recommendation_message?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface SignupData {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
  first_name?: string;
  last_name?: string;
}

export interface UserUpdate {
  email?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ResetPasswordRequestData {
  email: string;
}

export interface ResetPasswordConfirmData {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface OTPLoginResponse {
  requires_otp: true;
  temp_token: string;
  message: string;
}

export interface VerifyOTPData {
  otp_code: string;
  temp_token: string;
}

export interface OTPSetupResponse {
  otp_base32: string;
  otp_auth_url: string;
  qr_code: string;
}

export interface AdminOTPStatusItem {
  user_id: string;
  username: string;
  email: string;
  otp_enabled: boolean;
  otp_verified: boolean;
  last_verified_state: 'verified' | 'pending_verification' | 'not_enabled';
  last_otp_event_code: string | null;
  last_otp_event_at: string | null;
}

export interface AdminOTPStatusResponse {
  items: AdminOTPStatusItem[];
  total: number;
}

export interface PrivilegedActionChallengeDetail {
  code: 'OTP_CHALLENGE_REQUIRED';
  message: string;
  action: string;
  reason: 'step_up_required' | 'step_up_expired' | 'step_up_invalid' | string;
  otp: {
    required_freshness_seconds: number;
    grace_window_seconds: number;
    mode: 'audit' | 'enforce' | string;
  };
  rechallenge?: {
    required: boolean;
    reason: string;
    retryable: boolean;
  };
}

export interface StepUpVerificationResponse {
  step_up_token: string;
  expires_at: string;
  required_freshness_seconds: number;
  grace_window_seconds: number;
  action: string;
}
