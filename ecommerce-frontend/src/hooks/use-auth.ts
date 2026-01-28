'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/auth-store';
import type { LoginCredentials, SignupData, AuthTokens, User } from '@/types';

export function useAuth() {
  const queryClient = useQueryClient();
  const { user, setUser, logout: storeLogout } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await apiClient.post<AuthTokens>('/auth/token/', credentials);
      return response.data;
    },
    onSuccess: (data) => {
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', data.access);
      }
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
  });

  const signupMutation = useMutation({
    mutationFn: async (data: SignupData) => {
      const response = await apiClient.post<AuthTokens>('/auth/signup/', data);
      return response.data;
    },
    onSuccess: (data) => {
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', data.access);
      }
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
  });

  const { data: currentUser, refetch: refetchUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await apiClient.get<User>('/users/me/');
      setUser(response.data);
      return response.data;
    },
    enabled: typeof window !== 'undefined' && !!localStorage.getItem('access_token'),
  });

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout/');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      storeLogout();
      queryClient.clear();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  };

  return {
    user: currentUser || user,
    isAuthenticated: !!(currentUser || user),
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    signup: signupMutation.mutate,
    signupAsync: signupMutation.mutateAsync,
    logout,
    refetchUser,
    isLoading: loginMutation.isPending || signupMutation.isPending,
    loginError: loginMutation.error,
    signupError: signupMutation.error,
  };
}
