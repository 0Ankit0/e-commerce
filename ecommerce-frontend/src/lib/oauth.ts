/**
 * OAuth Configuration and Helpers
 */

export enum OAuthProvider {
  Google = 'google-oauth2',
  Facebook = 'facebook',
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate the OAuth login URL for a specific provider
 */
export const getOAuthUrl = (provider: OAuthProvider, locale = 'en'): string => {
  const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
  return `${API_URL}/api/auth/social/login/${provider}?next=${encodeURIComponent(currentUrl)}&locale=${locale}`;
};

/**
 * Redirect to OAuth provider login page
 */
export const startOAuthLogin = (provider: OAuthProvider, locale = 'en'): void => {
  if (typeof window !== 'undefined') {
    window.location.href = getOAuthUrl(provider, locale);
  }
};

/**
 * OAuth Button configurations
 */
export const oauthProviders = [
  {
    id: OAuthProvider.Google,
    name: 'Google',
    icon: 'google',
    bgClass: 'bg-white hover:bg-gray-50 border border-gray-300',
    textClass: 'text-gray-700',
  },
  {
    id: OAuthProvider.Facebook,
    name: 'Facebook',
    icon: 'facebook',
    bgClass: 'bg-[#1877F2] hover:bg-[#166FE5]',
    textClass: 'text-white',
  },
];
