'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/auth-store';
import type { User, UserProfile } from '@/types';

export function useCurrentUser() {
  const { setUser } = useAuthStore();

  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await apiClient.get<User>('/users/me/');
      setUser(response.data);
      return response.data;
    },
  });
}

export function useUserProfile() {
  return useQuery({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const response = await apiClient.get<UserProfile>('/users/profile/');
      return response.data;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { setUser } = useAuthStore();

  return useMutation({
    mutationFn: async (data: { first_name?: string; last_name?: string; avatar?: File }) => {
      const formData = new FormData();
      if (data.first_name) formData.append('first_name', data.first_name);
      if (data.last_name) formData.append('last_name', data.last_name);
      if (data.avatar) formData.append('avatar', data.avatar);

      const response = await apiClient.patch<UserProfile>('/users/profile/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      if (data.user) {
        setUser(data.user);
      }
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (data: { old_password: string; new_password: string }) => {
      const response = await apiClient.post('/users/change-password/', data);
      return response.data;
    },
  });
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: async (email: string) => {
      const response = await apiClient.post('/users/password-reset/', { email });
      return response.data;
    },
  });
}

export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: async (data: { token: string; uid: string; new_password: string }) => {
      const response = await apiClient.post('/users/password-reset/confirm/', data);
      return response.data;
    },
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.delete('/users/me/');
      return response.data;
    },
  });
}
