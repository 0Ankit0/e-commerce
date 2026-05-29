'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/auth-store';
import { useCurrentUser, useNotificationDevices, useNotificationPreferences, usePushConfig, useRegisterNotificationDevice, useSystemCapabilities } from '@/hooks';
import { registerCurrentPushDevice } from '@/lib/push-registration';

export function TemplateRuntimeProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const hasHydrated = useAuthStore((state) => state._hasHydrated);
  const isStorefrontRoute =
    pathname === '/' ||
    pathname.startsWith('/shop') ||
    pathname.startsWith('/products') ||
    pathname.startsWith('/wishlist/shared');
  const shouldHydrateCurrentUser = Boolean(
    isStorefrontRoute &&
    hasHydrated &&
      !isAuthenticated &&
      typeof window !== 'undefined' &&
      localStorage.getItem('access_token')
  );

  useCurrentUser({ enabled: shouldHydrateCurrentUser });
  const { data: capabilities } = useSystemCapabilities();
  const { data: pushConfig } = usePushConfig();
  const { data: preferences } = useNotificationPreferences({ enabled: isAuthenticated });
  const notificationsEnabled = capabilities?.modules.notifications ?? true;
  const activePushProvider = pushConfig?.provider;
  const shouldQueryPushDevices = Boolean(isAuthenticated && notificationsEnabled && activePushProvider);
  const { data: devices } = useNotificationDevices({ enabled: shouldQueryPushDevices });
  const registerDevice = useRegisterNotificationDevice();
  const shouldRegisterPush = Boolean(
    isAuthenticated &&
      notificationsEnabled &&
      preferences?.push_enabled &&
      activePushProvider
  );
  const hasMatchingDevice = Boolean(
    activePushProvider &&
      devices?.some((device) => device.provider === activePushProvider && device.is_active)
  );

  useEffect(() => {
    if (!shouldRegisterPush || !pushConfig || hasMatchingDevice || registerDevice.isPending) {
      return;
    }

    let cancelled = false;

    const syncDevice = async () => {
      const payload = await registerCurrentPushDevice(activePushProvider, pushConfig);

      if (!cancelled && payload) {
        registerDevice.mutate(payload);
      }
    };

    void syncDevice();

    return () => {
      cancelled = true;
    };
  }, [activePushProvider, hasMatchingDevice, pushConfig, registerDevice, shouldRegisterPush]);

  return <>{children}</>;
}
