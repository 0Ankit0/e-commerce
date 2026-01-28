'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { Subscription, PaymentMethod } from '@/types';

export function useSubscription() {
  return useQuery({
    queryKey: ['subscription'],
    queryFn: async () => {
      const response = await apiClient.get<Subscription>('/finances/subscriptions/');
      return response.data;
    },
  });
}

export function usePaymentMethods() {
  return useQuery({
    queryKey: ['payment-methods'],
    queryFn: async () => {
      const response = await apiClient.get<{ results: PaymentMethod[] }>(
        '/finances/payment-methods/'
      );
      return response.data.results;
    },
  });
}

export function useCreatePaymentIntent() {
  return useMutation({
    mutationFn: async (data: { amount: number; currency?: string }) => {
      const response = await apiClient.post<{ client_secret: string }>(
        '/finances/payment-intents/',
        data
      );
      return response.data;
    },
  });
}

export function useCreateSetupIntent() {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<{ client_secret: string }>('/finances/setup-intents/');
      return response.data;
    },
  });
}

export function useUpdateSubscription() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { price_id: string }) => {
      const response = await apiClient.post<Subscription>('/finances/subscription/update/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
    },
  });
}

export function useCancelSubscription() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/finances/subscription/cancel/');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
    },
  });
}

export function useTransactions() {
  return useQuery({
    queryKey: ['transactions'],
    queryFn: async () => {
      const response = await apiClient.get<{ results: unknown[] }>('/finances/transactions/');
      return response.data.results;
    },
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const response = await apiClient.get<{ results: unknown[] }>('/finances/invoices/');
      return response.data.results;
    },
  });
}
