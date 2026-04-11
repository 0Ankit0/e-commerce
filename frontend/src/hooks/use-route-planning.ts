'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface PlannerRouteInput {
  route_id: string;
  origin_hub: string;
  destination_hub: string;
  demand_units: number;
}

export interface PlannerVehicleInput {
  vehicle_id: string;
  hub_code: string;
  capacity_units: number;
}

export interface PlannerLockInput {
  route_id: string;
  vehicle_id: string;
  lock_units?: number;
  override_units?: number;
}

export interface PlannerAssignmentInput {
  route_id: string;
  vehicle_id: string;
  assigned_units: number;
}

export interface PlannerDraftPayload {
  name: string;
  status?: 'draft' | 'finalized';
  routes: PlannerRouteInput[];
  vehicles: PlannerVehicleInput[];
  connectivity?: Record<string, string[]>;
  locked_assignments?: PlannerLockInput[];
  assignments: PlannerAssignmentInput[];
  optimizer_metadata?: Record<string, unknown>;
}

export function useLineHaulPlanDrafts(enabled = true) {
  return useQuery({
    queryKey: ['line-haul-drafts'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: Array<Record<string, unknown>> }>('/logistics/line-haul-planner/drafts');
      return response.data.items;
    },
    enabled,
  });
}

export function useRunLineHaulOptimization() {
  return useMutation({
    mutationFn: async (payload: Omit<PlannerDraftPayload, 'name' | 'assignments' | 'status' | 'optimizer_metadata'> & { random_seed: number }) => {
      const response = await apiClient.post('/logistics/line-haul-planner/run', payload);
      return response.data;
    },
  });
}

export function useValidateLineHaulAssignments() {
  return useMutation({
    mutationFn: async (payload: PlannerDraftPayload) => {
      const response = await apiClient.post('/logistics/line-haul-planner/assignments/validate', {
        ...payload,
        status: payload.status ?? 'draft',
      });
      return response.data;
    },
  });
}

export function useSaveLineHaulDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PlannerDraftPayload) => {
      const response = await apiClient.post('/logistics/line-haul-planner/drafts', {
        ...payload,
        status: payload.status ?? 'draft',
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['line-haul-drafts'] });
    },
  });
}

export function useApplyLineHaulDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (draftId: string) => {
      const response = await apiClient.post(`/logistics/line-haul-planner/drafts/${draftId}/apply`);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['line-haul-drafts'] });
    },
  });
}
