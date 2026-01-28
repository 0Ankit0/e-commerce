import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Tenant } from '@/types';

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setTenant: (tenant: Tenant | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      tenant: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setTenant: (tenant) => {
        if (typeof window !== 'undefined' && tenant) {
          localStorage.setItem('tenant_id', tenant.id);
        }
        set({ tenant });
      },
      logout: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('tenant_id');
        }
        set({ user: null, tenant: null, isAuthenticated: false });
      },
    }),
    { name: 'auth-storage' }
  )
);
