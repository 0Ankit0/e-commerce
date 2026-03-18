'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  CustomerOrder,
  OrderInvoice,
  OrderNote,
  OrderTracking,
  ReturnRequestSummary,
  TimelineEvent,
} from '@/types';

interface ReturnPayload {
  orderId: string;
  orderItemId?: string;
  reason: string;
  details?: string;
  refundMethod?: string;
}

export function useOrders(enabled = true) {
  return useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: CustomerOrder[]; total: number }>('/orders');
      return response.data;
    },
    enabled,
  });
}

export function useOrderDetail(orderId: string, enabled = true) {
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: async () => {
      const response = await apiClient.get<{ order: CustomerOrder }>(`/orders/${orderId}`);
      return response.data.order;
    },
    enabled: enabled && Boolean(orderId),
  });
}

export function useOrderTimeline(orderId: string, enabled = true) {
  return useQuery({
    queryKey: ['order-timeline', orderId],
    queryFn: async () => {
      const response = await apiClient.get<{ items: TimelineEvent[] }>(`/orders/${orderId}/timeline`);
      return response.data.items;
    },
    enabled: enabled && Boolean(orderId),
  });
}

export function useOrderNotes(orderId: string, enabled = true) {
  return useQuery({
    queryKey: ['order-notes', orderId],
    queryFn: async () => {
      const response = await apiClient.get<{ items: OrderNote[] }>(`/orders/${orderId}/notes`);
      return response.data.items;
    },
    enabled: enabled && Boolean(orderId),
  });
}

export function useOrderInvoice(orderId: string, enabled = true) {
  return useQuery({
    queryKey: ['order-invoice', orderId],
    queryFn: async () => {
      const response = await apiClient.get<OrderInvoice>(`/orders/${orderId}/invoice`);
      return response.data;
    },
    enabled: enabled && Boolean(orderId),
  });
}

export function useOrderTracking(orderId: string, enabled = true) {
  return useQuery({
    queryKey: ['order-tracking', orderId],
    queryFn: async () => {
      const response = await apiClient.get<OrderTracking>(`/tracking/${orderId}`);
      return response.data;
    },
    enabled: enabled && Boolean(orderId),
    refetchInterval: 45_000,
  });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (orderId: string) => {
      const response = await apiClient.post<{ order: CustomerOrder }>(`/orders/${orderId}/cancel`);
      return response.data.order;
    },
    onSuccess: async (_, orderId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['orders'] }),
        queryClient.invalidateQueries({ queryKey: ['order', orderId] }),
        queryClient.invalidateQueries({ queryKey: ['order-timeline', orderId] }),
        queryClient.invalidateQueries({ queryKey: ['order-tracking', orderId] }),
      ]);
    },
  });
}

export function useCreateReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ReturnPayload) => {
      const response = await apiClient.post<{ return_request_id: string; status: string }>('/returns', {
        order_id: payload.orderId,
        order_item_id: payload.orderItemId,
        reason: payload.reason,
        details: payload.details ?? '',
        refund_method: payload.refundMethod ?? 'original',
      });
      return response.data;
    },
    onSuccess: async (_, payload) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['orders'] }),
        queryClient.invalidateQueries({ queryKey: ['order', payload.orderId] }),
        queryClient.invalidateQueries({ queryKey: ['order-timeline', payload.orderId] }),
      ]);
    },
  });
}

export function useReturnDetail(returnRequestId: string, enabled = true) {
  return useQuery({
    queryKey: ['return', returnRequestId],
    queryFn: async () => {
      const response = await apiClient.get<{ return_request: ReturnRequestSummary }>(`/returns/${returnRequestId}`);
      return response.data.return_request;
    },
    enabled: enabled && Boolean(returnRequestId),
  });
}

export function useReturnTimeline(returnRequestId: string, enabled = true) {
  return useQuery({
    queryKey: ['return-timeline', returnRequestId],
    queryFn: async () => {
      const response = await apiClient.get<{ items: TimelineEvent[] }>(`/returns/${returnRequestId}/timeline`);
      return response.data.items;
    },
    enabled: enabled && Boolean(returnRequestId),
  });
}
