'use client';

import axios from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  CatalogBrand,
  CatalogCategory,
  CatalogListResponse,
  CatalogProduct,
  CatalogRecommendationsResponse,
  CatalogSearchSuggestion,
  CategoryAttributeSchema,
  ProductDetailResponse,
  RecommendationPlacement,
} from '@/types';

interface ProductQueryOptions {
  q?: string;
  category?: string;
  brand?: string;
  vendorId?: string;
  inStock?: boolean;
  minPrice?: number;
  maxPrice?: number;
  minRating?: number;
  isFeatured?: boolean;
  sort?: string;
  page?: number;
  limit?: number;
}

interface CategoryPayload {
  name: string;
  slug: string;
  parent_id?: string | null;
  level: number;
  description?: string;
  attributes: CategoryAttributeSchema[];
  sort_order?: number;
  expected_updated_at?: string;
}

export interface VendorInventoryItem {
  product_id: string;
  variant_id: string;
  sku: string;
  quantity: number;
  reserved_qty: number;
  available_qty: number;
  reorder_level: number;
  reorder_qty: number;
  low_stock: boolean;
}

function shouldRetryCatalogQuery(failureCount: number, error: unknown) {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (status === 401 || status === 403 || status === 404) {
      return false;
    }
  }
  return failureCount < 2;
}

export function useCatalogProducts(options: ProductQueryOptions = {}) {
  return useQuery({
    queryKey: ['catalog-products', options],
    queryFn: async () => {
      const endpoint = options.q ? '/search' : '/products';
      const response = await apiClient.get<CatalogListResponse<CatalogProduct>>(endpoint, {
        params: {
          ...(options.q ? { q: options.q } : {}),
          category: options.category,
          brand: options.brand,
          vendor_id: options.vendorId,
          in_stock: options.inStock,
          min_price: options.minPrice,
          max_price: options.maxPrice,
          min_rating: options.minRating,
          is_featured: options.isFeatured,
          sort: options.sort,
          page: options.page ?? 1,
          limit: options.limit ?? 12,
        },
      });
      return response.data;
    },
    staleTime: 60_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useFeaturedProducts(limit = 8) {
  return useCatalogProducts({ isFeatured: true, limit, sort: 'newest' });
}

export function useCatalogCategories() {
  return useQuery({
    queryKey: ['catalog-categories'],
    queryFn: async () => {
      const response = await apiClient.get<CatalogListResponse<CatalogCategory>>('/categories');
      return response.data;
    },
    staleTime: 5 * 60_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useCatalogBrands() {
  return useQuery({
    queryKey: ['catalog-brands'],
    queryFn: async () => {
      const response = await apiClient.get<CatalogListResponse<CatalogBrand>>('/brands');
      return response.data;
    },
    staleTime: 5 * 60_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useCatalogProduct(productId: string) {
  return useQuery({
    queryKey: ['catalog-product', productId],
    queryFn: async () => {
      const response = await apiClient.get<ProductDetailResponse>(`/products/${productId}`);
      return response.data.product;
    },
    enabled: Boolean(productId),
    staleTime: 60_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useCatalogAutocomplete(query: string, enabled = true) {
  return useQuery({
    queryKey: ['catalog-autocomplete', query],
    queryFn: async () => {
      const response = await apiClient.get<{ items: CatalogSearchSuggestion[]; total: number }>('/search/autocomplete', {
        params: {
          q: query,
          limit: 6,
        },
      });
      return response.data;
    },
    enabled: enabled && query.trim().length >= 2,
    staleTime: 30_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useCatalogRecommendations(
  placement: RecommendationPlacement,
  options: { limit?: number; productId?: string; enabled?: boolean } = {}
) {
  return useQuery({
    queryKey: ['catalog-recommendations', placement, options],
    queryFn: async () => {
      const response = await apiClient.get<CatalogRecommendationsResponse>('/recommendations', {
        params: {
          type: placement,
          limit: options.limit ?? 6,
          product_id: options.productId,
        },
      });
      return response.data;
    },
    enabled: options.enabled ?? true,
    staleTime: 45_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useTrackCatalogEvent() {
  return useMutation({
    mutationFn: async (payload: {
      eventType: 'view' | 'click' | 'search' | 'add_to_cart' | 'add_to_wishlist' | 'purchase' | 'rating' | 'recommendation_click';
      placement?: RecommendationPlacement;
      productId?: string | null;
      queryText?: string;
      metadata?: Record<string, unknown>;
    }) => {
      const response = await apiClient.post('/recommendations/events', {
        event_type: payload.eventType,
        placement: payload.placement,
        product_id: payload.productId,
        query_text: payload.queryText ?? '',
        metadata: payload.metadata ?? {},
      });
      return response.data;
    },
  });
}

export function useVendorProducts() {
  return useQuery({
    queryKey: ['vendor-products'],
    queryFn: async () => {
      const response = await apiClient.get<CatalogListResponse<CatalogProduct>>('/vendor/products');
      return response.data;
    },
    staleTime: 60_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useVendorInventorySummary() {
  return useQuery({
    queryKey: ['vendor-inventory-summary'],
    queryFn: async () => {
      const response = await apiClient.get<CatalogListResponse<VendorInventoryItem>>('/vendor/inventory/summary');
      return response.data;
    },
    staleTime: 30_000,
    retry: shouldRetryCatalogQuery,
  });
}

export function useUpdateVendorInventory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: {
      variantId: string;
      quantity: number;
      reorderLevel: number;
      reorderQty: number;
    }) => {
      const response = await apiClient.patch(`/vendor/inventory/${payload.variantId}`, {
        quantity: payload.quantity,
        reorder_level: payload.reorderLevel,
        reorder_qty: payload.reorderQty,
      });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vendor-inventory-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['vendor-products'] }),
      ]);
    },
  });
}

export function useAdminCategoryMutations() {
  const queryClient = useQueryClient();

  const invalidateCategories = async () => {
    await queryClient.invalidateQueries({ queryKey: ['catalog-categories'] });
  };

  const createCategory = useMutation({
    mutationFn: async (payload: CategoryPayload) => {
      const response = await apiClient.post('/admin/categories', payload);
      return response.data;
    },
    onSuccess: invalidateCategories,
  });

  const updateCategory = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: CategoryPayload }) => {
      const response = await apiClient.patch(`/admin/categories/${id}`, payload);
      return response.data;
    },
    onSuccess: invalidateCategories,
  });

  const deleteCategory = useMutation({
    mutationFn: async ({ id, migrateToCategoryId }: { id: string; migrateToCategoryId?: string }) => {
      const response = await apiClient.delete(`/admin/categories/${id}`, {
        data: migrateToCategoryId ? { migrate_to_category_id: migrateToCategoryId } : {},
      });
      return response.data;
    },
    onSuccess: invalidateCategories,
  });

  const reorderCategories = useMutation({
    mutationFn: async (items: Array<{ id: string; parent_id?: string | null; sort_order: number }>) => {
      const response = await apiClient.post('/admin/categories/reorder', { items });
      return response.data;
    },
    onSuccess: invalidateCategories,
  });

  return { createCategory, updateCategory, deleteCategory, reorderCategories };
}
