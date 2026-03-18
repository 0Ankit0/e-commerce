'use client';

import { Suspense, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { getDefaultPortalPath } from '@/lib/portal';
import { useAuthStore } from '@/store/auth-store';
import { Loader2 } from 'lucide-react';
import type { User } from '@/types';

/**
 * Landing page for social OAuth callbacks.
 * The backend redirects here after a successful social login with
 * access and refresh tokens as query params (when set_cookie=false).
 * Usage: /auth-callback?access=TOKEN&refresh=TOKEN
 */
function AuthCallbackInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();

  useEffect(() => {
    async function completeSocialLogin() {
      const access = searchParams.get('access');
      const refresh = searchParams.get('refresh');
      const error = searchParams.get('error');

      if (error) {
        router.replace(`/login?error=${encodeURIComponent(error)}`);
        return;
      }

      if (!access || !refresh) {
        router.replace('/login?error=oauth_failed');
        return;
      }

      setTokens(access, refresh);

      try {
        const userResponse = await apiClient.get<User>('/users/me/');
        setUser(userResponse.data);
        router.replace(getDefaultPortalPath(userResponse.data));
      } catch {
        router.replace('/login?error=oauth_user_fetch_failed');
      }
    }

    void completeSocialLogin();
  }, [router, searchParams, setTokens, setUser]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
        <p className="text-gray-500 text-sm">Completing sign-in…</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense>
      <AuthCallbackInner />
    </Suspense>
  );
}
