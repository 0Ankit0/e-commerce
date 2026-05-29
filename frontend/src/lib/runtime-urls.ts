const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';
const DEFAULT_WS_BASE_URL = 'ws://localhost:8000';

function normalizeLocalHost(rawUrl: string): string {
  if (typeof window === 'undefined') {
    return rawUrl;
  }

  const browserHost = window.location.hostname;
  if (browserHost !== 'localhost' && browserHost !== '127.0.0.1') {
    return rawUrl;
  }

  try {
    const parsed = new URL(rawUrl);
    if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
      parsed.hostname = browserHost;
      return parsed.toString().replace(/\/$/, '');
    }
    return rawUrl;
  } catch {
    return rawUrl;
  }
}

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_BASE_URL;
  return normalizeLocalHost(configured);
}

export function getWsBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL ?? DEFAULT_WS_BASE_URL;
  return normalizeLocalHost(configured);
}