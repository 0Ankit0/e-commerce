'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import type { AdminOTPStatusResponse } from '@/types';

export function useAdminOTPStatus(enabled = true) {
  return useQuery({
    queryKey: ['admin-otp-status'],
    queryFn: async () => {
      const response = await apiClient.get<AdminOTPStatusResponse>('/auth/admin/security/admin-otp-status');
      return response.data;
    },
    enabled,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
