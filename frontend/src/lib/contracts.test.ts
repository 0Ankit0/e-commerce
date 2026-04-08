import { describe, expect, it } from 'vitest';

import { asApiEnum, type StrictPaginatedResponse } from '@/types/contracts';

describe('API contract helpers', () => {
  it('maps unknown enum values to unknown for forward compatibility', () => {
    const known = ['acknowledged', 'resolved'] as const;
    expect(asApiEnum('acknowledged', known)).toBe('acknowledged');
    expect(asApiEnum('new_status_added_later', known)).toBe('unknown');
  });

  it('requires pagination metadata in response payload contracts', () => {
    const payload: StrictPaginatedResponse<{ id: string }> = {
      items: [{ id: 'abc' }],
      total: 1,
      skip: 0,
      limit: 10,
      has_more: false,
    };

    expect(payload.has_more).toBe(false);
  });

  it('keeps nullable fields present even when null', () => {
    type Incident = {
      actor_user_id: string | null;
      reviewed_by: string | null;
    };

    const payload: Incident = {
      actor_user_id: null,
      reviewed_by: null,
    };

    expect(payload).toHaveProperty('actor_user_id');
    expect(payload).toHaveProperty('reviewed_by');
  });
});
