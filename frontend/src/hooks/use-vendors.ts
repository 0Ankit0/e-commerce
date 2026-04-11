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
