'use client';

import axios from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  Address,
  AddressSuggestion,
  Cart,
  CatalogBanner,
  CheckoutQuote,
  SharedWishlistResponse,
  StaticPage,
  WishlistItem,
  WishlistShareLink,
} from '@/types';

interface CartItemPayload {
  variantId: string;
  quantity: number;
}

interface AddressPayload {
  name: string;
  phone: string;
  line1: string;
  line2?: string;
  city: string;
  state: string;
  pincode: string;
  country?: string;
  landmark?: string;
  type?: string;
  isDefault?: boolean;
}

export interface CheckoutPayload {
  addressId: string;
  paymentMethod: string;
  paymentTransactionId?: string;
  shippingOptionCode?: string;
  quoteFingerprint?: string;
  notes?: string;
}

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg ?? 'Request failed').join(', ');
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Something went wrong.';
}

function invalidateCommerceQueries(queryClient: ReturnType<typeof useQueryClient>) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ['cart'] }),
    queryClient.invalidateQueries({ queryKey: ['orders'] }),
    queryClient.invalidateQueries({ queryKey: ['wishlist'] }),
    queryClient.invalidateQueries({ queryKey: ['addresses'] }),
  ]);
}

export function useApiErrorMessage() {
  return { getErrorMessage };
}

export function useCart(enabled = true) {
  return useQuery({
    queryKey: ['cart'],
    queryFn: async () => {
      const response = await apiClient.get<Cart>('/cart');
      return response.data;
    },
    enabled,
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ variantId, quantity }: CartItemPayload) => {
      const response = await apiClient.post<Cart>('/cart/items', {
        variant_id: variantId,
        quantity,
      });
      return response.data;
    },
    onSuccess: async () => {
      await invalidateCommerceQueries(queryClient);
    },
  });
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, quantity }: { itemId: string; quantity: number }) => {
      const response = await apiClient.patch<Cart>(`/cart/items/${itemId}`, { quantity });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useRemoveCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (itemId: string) => {
      const response = await apiClient.delete<Cart>(`/cart/items/${itemId}`);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useApplyCoupon() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (code: string) => {
      const response = await apiClient.post<Cart>('/cart/coupon', { code });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useWishlist(enabled = true) {
  return useQuery({
    queryKey: ['wishlist'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: WishlistItem[]; total: number }>('/wishlist');
      return response.data;
    },
    enabled,
  });
}

export function useAddToWishlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (productId: string) => {
      const response = await apiClient.post(`/wishlist/${productId}`);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['wishlist'] });
    },
  });
}

export function useRemoveFromWishlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (productId: string) => {
      const response = await apiClient.delete(`/wishlist/${productId}`);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['wishlist'] });
    },
  });
}

export function useWishlistShareLinks(enabled = true) {
  return useQuery({
    queryKey: ['wishlist-share-links'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: WishlistShareLink[]; total: number }>('/wishlist/share-links');
      return response.data;
    },
    enabled,
  });
}

export function useCreateWishlistShareLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (title: string) => {
      const response = await apiClient.post<{ share_link: WishlistShareLink }>('/wishlist/share-links', { title });
      return response.data.share_link;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['wishlist-share-links'] });
    },
  });
}

export function useRevokeWishlistShareLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (shareId: string) => {
      const response = await apiClient.delete(`/wishlist/share-links/${shareId}`);
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['wishlist-share-links'] });
    },
  });
}

export function useSharedWishlist(token: string) {
  return useQuery({
    queryKey: ['shared-wishlist', token],
    queryFn: async () => {
      const response = await apiClient.get<SharedWishlistResponse>(`/wishlist/shared/${token}`);
      return response.data;
    },
    enabled: Boolean(token),
  });
}

export function useAddresses(enabled = true) {
  return useQuery({
    queryKey: ['addresses'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: Address[]; total: number }>('/addresses');
      return response.data;
    },
    enabled,
  });
}

export function useAddressAutocomplete(query: string, enabled = true) {
  return useQuery({
    queryKey: ['address-autocomplete', query],
    queryFn: async () => {
      const response = await apiClient.get<{ items: AddressSuggestion[] }>('/addresses/autocomplete', {
        params: { q: query, limit: 6 },
      });
      return response.data.items;
    },
    enabled: enabled && query.trim().length >= 3,
    staleTime: 30_000,
  });
}

export function useCreateAddress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: AddressPayload) => {
      const response = await apiClient.post<{ address: Address }>('/addresses', {
        name: payload.name,
        phone: payload.phone,
        line1: payload.line1,
        line2: payload.line2 ?? '',
        city: payload.city,
        state: payload.state,
        pincode: payload.pincode,
        country: payload.country ?? 'Nepal',
        landmark: payload.landmark ?? '',
        type: payload.type ?? 'home',
        is_default: payload.isDefault ?? false,
      });
      return response.data.address;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['addresses'] });
    },
  });
}

export function useSetDefaultAddress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (addressId: string) => {
      const response = await apiClient.post<{ address: Address }>(`/addresses/${addressId}/default`);
      return response.data.address;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['addresses'] });
    },
  });
}

export function useCheckoutQuote(params: {
  addressId?: string;
  paymentMethod?: string;
  shippingOptionCode?: string;
}) {
  return useQuery({
    queryKey: ['checkout-quote', params.addressId, params.paymentMethod, params.shippingOptionCode],
    queryFn: async () => {
      const response = await apiClient.get<CheckoutQuote>('/checkout/quote', {
        params: {
          address_id: params.addressId,
          payment_method: params.paymentMethod ?? 'cod',
          shipping_option_code: params.shippingOptionCode,
        },
      });
      return response.data;
    },
    enabled: Boolean(params.addressId),
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CheckoutPayload) => {
      const response = await apiClient.post<{ order: unknown }>(
        '/checkout',
        {
          address_id: payload.addressId,
          payment_method: payload.paymentMethod,
          payment_transaction_id: payload.paymentTransactionId,
          shipping_option_code: payload.shippingOptionCode,
          quote_fingerprint: payload.quoteFingerprint,
          notes: payload.notes ?? '',
        },
        {
          headers: {
            'Idempotency-Key': `${payload.addressId}:${payload.quoteFingerprint ?? payload.paymentMethod}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: async () => {
      await invalidateCommerceQueries(queryClient);
    },
  });
}

export function useContentBanners(placement = 'home') {
  return useQuery({
    queryKey: ['content-banners', placement],
    queryFn: async () => {
      const response = await apiClient.get<{ items: CatalogBanner[]; total: number }>('/content/banners', {
        params: { placement },
      });
      return response.data;
    },
    staleTime: 5 * 60_000,
  });
}

export function useStaticPage(slug: string) {
  return useQuery({
    queryKey: ['static-page', slug],
    queryFn: async () => {
      const response = await apiClient.get<{ page: StaticPage }>(`/content/pages/${slug}`);
      return response.data.page;
    },
    enabled: Boolean(slug),
    staleTime: 5 * 60_000,
  });
}
