export type OAuthProvider = 'google' | 'github' | 'facebook' | 'apple';

import { getApiBaseUrl } from '@/lib/runtime-urls';

const OAUTH_PROVIDERS: OAuthProvider[] = ['google', 'github', 'facebook', 'apple'];

const BACKEND_URL = getApiBaseUrl();

/** Starts an OAuth login by redirecting the current browser window to the backend. */
export function startOAuthLogin(provider: OAuthProvider) {
  window.location.assign(`${BACKEND_URL}/auth/social/${provider}/`);
}

/** Returns the list of providers currently enabled on the backend. */
export async function getEnabledProviders(): Promise<OAuthProvider[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/auth/social/providers/`, {
      // Revalidate every hour — providers are static config, not runtime data.
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = (await res.json()) as { providers: string[] };
    return (data.providers ?? []).filter((provider): provider is OAuthProvider =>
      OAUTH_PROVIDERS.includes(provider as OAuthProvider)
    );
  } catch {
    return [];
  }
}
