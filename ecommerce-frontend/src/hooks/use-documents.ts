'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface Document {
  id: string;
  title: string;
  file_url: string;
  file_type: string;
  file_size: number;
  is_processed: boolean;
  extracted_text?: string;
  thumbnail?: string;
  created_at: string;
  updated_at: string;
}

interface DocumentsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Document[];
}

interface UploadDocumentPayload {
  file: File;
  title?: string;
}

export function useDocuments(page = 1, pageSize = 10) {
  const queryClient = useQueryClient();

  const documentsQuery = useQuery({
    queryKey: ['documents', page, pageSize],
    queryFn: async () => {
      const response = await apiClient.get<DocumentsResponse>('/content/documents/', {
        params: { page, page_size: pageSize },
      });
      return response.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ file, title }: UploadDocumentPayload) => {
      const formData = new FormData();
      formData.append('file', file);
      if (title) {
        formData.append('title', title);
      }

      const response = await apiClient.post<Document>('/content/documents/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/content/documents/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const downloadDocument = async (id: string, filename: string) => {
    const response = await apiClient.get(`/content/documents/${id}/download/`, {
      responseType: 'blob',
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  return {
    documents: documentsQuery.data?.results ?? [],
    totalCount: documentsQuery.data?.count ?? 0,
    hasNext: !!documentsQuery.data?.next,
    hasPrevious: !!documentsQuery.data?.previous,
    isLoading: documentsQuery.isLoading,
    error: documentsQuery.error,
    refetch: documentsQuery.refetch,
    upload: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,
    uploadError: uploadMutation.error,
    deleteDocument: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    downloadDocument,
  };
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: async () => {
      const response = await apiClient.get<Document>(`/content/documents/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}
