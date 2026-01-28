import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';

export interface ContentItem {
  id: string;
  slug: string;
  external_id: string;
  content_type: string;
  fields: Record<string, any>;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export const useContentItems = (type?: string) => {
  return useQuery({
    queryKey: ['content-items', type],
    queryFn: async () => {
      const params = type ? { content_type: type } : {};
      const response = await apiClient.get<ContentItem[]>('/content/items/', { params });
      return response.data;
    },
  });
};

export const useProductContent = () => {
  return useContentItems('product');
};
