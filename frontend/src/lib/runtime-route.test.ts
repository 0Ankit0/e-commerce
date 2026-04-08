import { describe, expect, it } from 'vitest';
import { getRuntimeErrorState, isPaginatedPayload } from './runtime-route';

function axiosError(status: number) {
  return { isAxiosError: true, response: { status } };
}

describe('runtime-route helpers', () => {
  it('differentiates HTTP status families with actionable labels', () => {
    expect(getRuntimeErrorState(axiosError(401), 'x').actionLabel).toContain('sign in');
    expect(getRuntimeErrorState(axiosError(409), 'x').actionLabel).toContain('Refresh');
    expect(getRuntimeErrorState(axiosError(422), 'x').actionLabel).toContain('Review');
    expect(getRuntimeErrorState(axiosError(429), 'x').actionLabel).toContain('shortly');
    expect(getRuntimeErrorState(axiosError(503), 'x').description).toContain('unavailable');
  });

  it('detects valid and partial paginated payloads', () => {
    expect(isPaginatedPayload({ items: [], total: 0 })).toBe(true);
    expect(isPaginatedPayload({ items: [] })).toBe(false);
    expect(isPaginatedPayload(null)).toBe(false);
  });
});
