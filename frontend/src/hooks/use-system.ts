'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { apiClient } from '@/lib/api-client';
import type {
  CapabilitySummary,
  MapConfigResponse,
  ChannelQuotaAudit,
  ChannelQuotaPolicy,
  ChannelQuotaUsage,
  EmailDeliveryAnalytics,
  EmailDeliveryDeadLetter,
  EmailDeliveryMessage,
  ProviderStatusResponse,
  PushConfigResponse,
} from '@/types';

export function useSystemCapabilities() {
  return useQuery({
    queryKey: ['system-capabilities'],
    queryFn: async () => {
      const response = await apiClient.get<CapabilitySummary>('/system/capabilities/');
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function useSystemProviders() {
  return useQuery({
    queryKey: ['system-providers'],
    queryFn: async () => {
      const response = await apiClient.get<ProviderStatusResponse>('/system/providers/');
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function usePushConfig() {
  return useQuery({
    queryKey: ['push-config'],
    queryFn: async () => {
      try {
        const response = await apiClient.get<PushConfigResponse>('/notifications/push/config/');
        return response.data;
      } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 503) {
          return {
            provider: null,
            providers: {
              webpush: { enabled: false },
              fcm: { enabled: false },
              onesignal: { enabled: false },
            },
          } satisfies PushConfigResponse;
        }
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function useMapConfig() {
  return useQuery({
    queryKey: ['maps-config'],
    queryFn: async () => {
      const response = await apiClient.get<MapConfigResponse>('/system/maps/config/');
      return response.data;
    },
    staleTime: 60_000,
  });
}


export function useChannelQuotaPolicies() {
  return useQuery({
    queryKey: ['channel-quota-policies'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: ChannelQuotaPolicy[] }>('/system/admin/communications/quotas/policies/');
      return response.data.items;
    },
  });
}

export function useChannelQuotaUsage() {
  return useQuery({
    queryKey: ['channel-quota-usage'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: ChannelQuotaUsage[] }>('/system/admin/communications/quotas/usage/');
      return response.data.items;
    },
  });
}

export function useChannelQuotaAudit() {
  return useQuery({
    queryKey: ['channel-quota-audit'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: ChannelQuotaAudit[] }>('/system/admin/communications/quotas/audit/');
      return response.data.items;
    },
  });
}

export function useCreateChannelQuotaPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<ChannelQuotaPolicy>) => {
      const response = await apiClient.post<ChannelQuotaPolicy>('/system/admin/communications/quotas/policies/', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-quota-policies'] });
    },
  });
}

export function useOverrideChannelQuotaPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ policyId, limit_count, enabled, reason }: { policyId: number; limit_count?: number; enabled?: boolean; reason?: string }) => {
      const response = await apiClient.patch<ChannelQuotaPolicy>(`/system/admin/communications/quotas/policies/${policyId}/override/`, {
        limit_count,
        enabled,
        reason: reason ?? '',
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-quota-policies'] });
      queryClient.invalidateQueries({ queryKey: ['channel-quota-audit'] });
    },
  });
}

export function useEmailDeliveryAnalytics() {
  return useQuery({
    queryKey: ['email-delivery-analytics'],
    queryFn: async () => {
      const response = await apiClient.get<EmailDeliveryAnalytics>('/system/admin/communications/delivery/analytics/');
      return response.data;
    },
  });
}

export function useEmailDeliveryMessages() {
  return useQuery({
    queryKey: ['email-delivery-messages'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: EmailDeliveryMessage[] }>('/system/admin/communications/delivery/messages/');
      return response.data.items;
    },
  });
}

export function useEmailDeliveryDeadLetters() {
  return useQuery({
    queryKey: ['email-delivery-dead-letters'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: EmailDeliveryDeadLetter[] }>('/system/admin/communications/delivery/dead-letters/');
      return response.data.items;
    },
  });
}
