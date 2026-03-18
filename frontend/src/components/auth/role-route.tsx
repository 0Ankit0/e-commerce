'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from './protected-route';
import { useAuthStore } from '@/store/auth-store';
import { canAccessPortal, getDefaultPortalPath, type PortalKey } from '@/lib/portal';

interface RoleRouteProps {
  portal: PortalKey;
  children: React.ReactNode;
}

export function RoleRoute({ portal, children }: RoleRouteProps) {
  const user = useAuthStore((state) => state.user);
  const router = useRouter();

  useEffect(() => {
    if (user && !canAccessPortal(user, portal)) {
      router.replace(getDefaultPortalPath(user));
    }
  }, [portal, router, user]);

  if (user && !canAccessPortal(user, portal)) {
    return null;
  }

  return <ProtectedRoute>{children}</ProtectedRoute>;
}
