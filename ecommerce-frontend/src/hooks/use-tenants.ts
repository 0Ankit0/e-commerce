'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/auth-store';
import type { Tenant, TenantMembership } from '@/types';

interface TenantsResponse {
  results: Tenant[];
  count: number;
  next: string | null;
  previous: string | null;
}

export function useTenants() {
  return useQuery({
    queryKey: ['tenants'],
    queryFn: async () => {
      const response = await apiClient.get<TenantsResponse>('/tenants/');
      return response.data;
    },
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: ['tenants', id],
    queryFn: async () => {
      const response = await apiClient.get<Tenant>(`/tenants/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { name: string; type: 'organization' | 'individual' }) => {
      const response = await apiClient.post<Tenant>('/tenants/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

export function useUpdateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Tenant> }) => {
      const response = await apiClient.patch<Tenant>(`/tenants/${id}/`, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.id] });
    },
  });
}

export function useTenantMemberships(tenantId: string) {
  return useQuery({
    queryKey: ['tenants', tenantId, 'memberships'],
    queryFn: async () => {
      const response = await apiClient.get<{ results: TenantMembership[] }>(
        `/tenants/${tenantId}/memberships/`
      );
      return response.data.results;
    },
    enabled: !!tenantId,
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tenantId,
      email,
      role,
    }: {
      tenantId: string;
      email: string;
      role: string;
    }) => {
      const response = await apiClient.post(`/tenants/${tenantId}/invite/`, { email, role });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'memberships'] });
    },
  });
}

export function useSwitchTenant() {
  const { setTenant } = useAuthStore();

  return useMutation({
    mutationFn: async (tenant: Tenant) => {
      setTenant(tenant);
      return tenant;
    },
  });
}
