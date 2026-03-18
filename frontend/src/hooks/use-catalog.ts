'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  CatalogBrand,
  CatalogCategory,
  CatalogListResponse,
  CatalogProduct,
  ProductDetailResponse,
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

export function useCatalogProducts(options: ProductQueryOptions = {}) {
  return useQuery({
    queryKey: ['catalog-products', options],
    queryFn: async () => {
      const response = await apiClient.get<CatalogListResponse<CatalogProduct>>('/products', {
        params: {
          q: options.q,
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
  });
}
