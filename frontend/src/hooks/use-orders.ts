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

export interface VendorShipmentSummary {
  id: string;
  awb: string;
  status: string;
  current_location: string;
  eta: string | null;
}

export interface VendorOrderSummary {
  id: string;
  order_id: string;
  vendor_order_number: string;
  status: string;
  subtotal: number;
  commission: number;
  vendor_amount: number;
  shipment: VendorShipmentSummary | null;
}

export interface AdminLiveFeedItem {
  source: string;
  event_type: string;
  message: string;
  actor_user_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
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

export function useVendorOrders() {
  return useQuery({
    queryKey: ['vendor-orders'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: VendorOrderSummary[]; total: number }>('/vendor/orders');
      return response.data;
    },
    staleTime: 15_000,
  });
}

export function useUpdateVendorOrderStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { vendorOrderId: string; status: string; location?: string; remarks?: string }) => {
      const response = await apiClient.post(`/vendor/orders/${payload.vendorOrderId}/status`, {
        status: payload.status,
        location: payload.location ?? '',
        remarks: payload.remarks ?? '',
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['vendor-orders'] });
    },
  });
}

export function useRejectVendorOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { vendorOrderId: string; reason: string }) => {
      const response = await apiClient.post(`/vendor/orders/${payload.vendorOrderId}/reject`, {
        reason: payload.reason,
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['vendor-orders'] });
    },
  });
}

export function useCreateVendorPickupJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { vendorOrderId: string; branchId?: string }) => {
      const response = await apiClient.post(`/vendor/orders/${payload.vendorOrderId}/pickup-jobs`, null, {
        params: payload.branchId ? { branch_id: payload.branchId } : undefined,
      });
      return response.data as { pickup_job_id: string };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['vendor-orders'] });
    },
  });
}

export function useGenerateVendorShipmentLabel() {
  return useMutation({
    mutationFn: async (payload: { shipmentId: string; force?: boolean }) => {
      const response = await apiClient.post(`/vendor/shipments/${payload.shipmentId}/label`, null, {
        params: payload.force ? { force: true } : undefined,
      });
      return response.data as {
        shipment_id: string;
        awb: string;
        label_url: string;
        generated_at: string;
        label: Record<string, unknown>;
      };
    },
  });
}

export function useAdminOrders(query?: string) {
  return useQuery({
    queryKey: ['admin-orders', query ?? ''],
    queryFn: async () => {
      const response = await apiClient.get<{ items: CustomerOrder[]; total: number }>('/admin/orders', {
        params: query ? { q: query } : undefined,
      });
      return response.data;
    },
    staleTime: 10_000,
  });
}

export function useAdminOrderLiveFeed(limit = 50) {
  return useQuery({
    queryKey: ['admin-order-live-feed', limit],
    queryFn: async () => {
      const response = await apiClient.get<{ items: AdminLiveFeedItem[]; total: number }>('/admin/orders/live-feed', {
        params: { limit },
      });
      return response.data;
    },
    staleTime: 10_000,
    refetchInterval: 10_000,
    refetchIntervalInBackground: true,
  });
}

export function useCreateAdminOrderNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { orderId: string; note: string; noteType?: string; isCustomerVisible?: boolean }) => {
      const response = await apiClient.post(`/admin/orders/${payload.orderId}/notes`, {
        note: payload.note,
        note_type: payload.noteType ?? 'internal',
        is_customer_visible: payload.isCustomerVisible ?? false,
      });
      return response.data as { note_id: string };
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-orders'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-order-live-feed'] }),
      ]);
    },
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
