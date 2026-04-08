import axios from 'axios';

export type RuntimeErrorState = {
  title: string;
  description: string;
  details: string;
  actionLabel: string;
};

export function getRuntimeErrorState(error: unknown, fallbackTitle: string): RuntimeErrorState {
  const status = axios.isAxiosError(error) ? error.response?.status : undefined;
  const statusLabel = status ? `HTTP ${status}` : 'Network error';

  if (status === 401) {
    return {
      title: fallbackTitle,
      description: 'Your session expired. Sign in again and retry this request.',
      details: `${statusLabel}: authentication is required for this route.`,
      actionLabel: 'Retry after sign in',
    };
  }
  if (status === 403) {
    return {
      title: fallbackTitle,
      description: 'Your account does not have permission to load this route data.',
      details: `${statusLabel}: access denied for this resource.`,
      actionLabel: 'Retry',
    };
  }
  if (status === 404) {
    return {
      title: fallbackTitle,
      description: 'The requested resource was not found.',
      details: `${statusLabel}: verify URL, record IDs, or environment configuration.`,
      actionLabel: 'Retry',
    };
  }
  if (status === 409) {
    return {
      title: fallbackTitle,
      description: 'The request conflicts with the latest server state.',
      details: `${statusLabel}: refresh data and retry once concurrent changes settle.`,
      actionLabel: 'Refresh and retry',
    };
  }
  if (status === 422) {
    return {
      title: fallbackTitle,
      description: 'The server rejected this request as invalid.',
      details: `${statusLabel}: verify required fields and request shape before retrying.`,
      actionLabel: 'Review and retry',
    };
  }
  if (status === 429) {
    return {
      title: fallbackTitle,
      description: 'Too many requests were sent in a short time.',
      details: `${statusLabel}: wait briefly before retrying to avoid rate limiting.`,
      actionLabel: 'Retry shortly',
    };
  }
  if (status && status >= 500) {
    return {
      title: fallbackTitle,
      description: 'The API is currently unavailable for this route.',
      details: `${statusLabel}: server-side failure, no fallback data is being shown.`,
      actionLabel: 'Retry',
    };
  }

  return {
    title: fallbackTitle,
    description: 'This route could not load live data.',
    details: `${statusLabel}: check your connection and retry.`,
    actionLabel: 'Retry',
  };
}

export function isPaginatedPayload(value: unknown): value is { items: unknown[]; total: number } {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const candidate = value as { items?: unknown; total?: unknown };
  return Array.isArray(candidate.items) && typeof candidate.total === 'number';
}
