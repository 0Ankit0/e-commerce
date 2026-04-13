'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface VendorQueueItem {
  vendor: {
    id: string;
    business_name: string;
    display_name: string;
    kyc_status: string;
    created_at: string;
  };
  checks: {
    missing_documents: string[];
    bank_verified: boolean;
  };
  sla_breach: boolean;
  age_hours: number;
}

export interface VendorAnalyticsResponse {
  vendor: {
    id: string;
    business_name: string;
    display_name: string;
    status: string;
    kyc_status: string;
    product_count: number;
    rating: number;
    created_at: string;
  };
  analytics: {
    orders: number;
    net_revenue: number;
    product_count: number;
    rating: number;
  };
}

export interface VendorTimelineItem {
  id: string;
  event_type: string;
  message: string;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface VendorPayout {
  id: string;
  vendor_id: string;
  amount: number;
  commission_amount: number;
  status: string;
  reference: string;
  period_start: string | null;
  period_end: string | null;
  payout_batch_id: string | null;
  created_at: string;
  paid_at: string | null;
}

export interface VendorPayoutRequest {
  id: string;
  vendor_id: string;
  requested_by_user_id: string;
  amount: number;
  currency: string;
  notes: string;
  status: string;
  created_at: string;
  reviewed_at: string | null;
}

export function useAdminKycQueue(filter: 'new' | 'pending' | 'sla_breach' = 'pending') {
  return useQuery({
    queryKey: ['admin-kyc-queue', filter],
    queryFn: async () => {
      const response = await apiClient.get<{ items: VendorQueueItem[]; total: number }>('/admin/vendors/kyc/queue', {
        params: { filter },
      });
      return response.data;
    },
  });
}

export function useAdminVendorTimeline(vendorId?: string) {
  return useQuery({
    queryKey: ['admin-vendor-timeline', vendorId],
    queryFn: async () => {
      const response = await apiClient.get<{ items: Array<{ event_type: string; message: string; created_at: string }> }>(
        `/admin/vendors/${vendorId}/timeline`,
      );
      return response.data.items;
    },
    enabled: Boolean(vendorId),
  });
}

export function useAdminKycDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { vendorId: string; action: 'approve' | 'reject' | 'request-resubmission'; reasonCode: string; reason: string }) => {
      const response = await apiClient.post(`/admin/vendors/${payload.vendorId}/kyc/decision/${payload.action}`, {
        reason_code: payload.reasonCode,
        reason: payload.reason,
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin-kyc-queue'] });
    },
  });
}

export function useVendorKycHistory() {
  return useQuery({
    queryKey: ['vendor-kyc-history'],
    queryFn: async () => {
      const response = await apiClient.get<{
        kyc_status: string;
        steps: Record<string, string>;
        checks: { missing_documents: string[]; bank_verified: boolean; bank_submitted: boolean };
        items: Array<{ event_type: string; message: string; created_at: string; payload: Record<string, unknown> }>;
      }>('/vendor/kyc/history');
      return response.data;
    },
  });
}

export function useVendorAnalytics() {
  return useQuery({
    queryKey: ['vendor-analytics'],
    queryFn: async () => {
      const response = await apiClient.get<VendorAnalyticsResponse>('/vendor/analytics');
      return response.data;
    },
    staleTime: 15_000,
  });
}

export function useVendorTimeline() {
  return useQuery({
    queryKey: ['vendor-timeline'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: VendorTimelineItem[]; total: number }>('/vendor/timeline');
      return response.data;
    },
    staleTime: 15_000,
  });
}

export function useVendorPayouts() {
  return useQuery({
    queryKey: ['vendor-payouts'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: VendorPayout[]; total: number }>('/vendor/payouts');
      return response.data;
    },
    staleTime: 15_000,
  });
}

export function useVendorPayoutRequests() {
  return useQuery({
    queryKey: ['vendor-payout-requests'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: VendorPayoutRequest[]; total: number }>('/vendor/payout-requests');
      return response.data;
    },
    staleTime: 15_000,
  });
}

export function useCreateVendorPayoutRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { amount: number; notes: string }) => {
      const response = await apiClient.post('/vendor/payout-requests', payload);
      return response.data as { payout_request: VendorPayoutRequest };
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vendor-payout-requests'] }),
        queryClient.invalidateQueries({ queryKey: ['vendor-payouts'] }),
        queryClient.invalidateQueries({ queryKey: ['vendor-timeline'] }),
        queryClient.invalidateQueries({ queryKey: ['vendor-analytics'] }),
      ]);
    },
  });
}

export function useSubmitKycPacket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, string>) => {
      const response = await apiClient.put('/vendor/kyc/packet', payload);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['vendor-kyc-history'] });
    },
  });
}
