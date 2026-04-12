import { describe, expect, it } from 'vitest';

import {
  isOrderNumber,
  isSupportedOrderReference,
  normalizeOrderReference,
} from './order-reference';

describe('order reference helpers', () => {
  it('accepts current and legacy order number formats', () => {
    expect(isOrderNumber('ORD-AB12CD34EF')).toBe(true);
    expect(isOrderNumber('ord-2025-0041')).toBe(true);
  });

  it('accepts hashid-like and numeric compatibility references', () => {
    expect(isSupportedOrderReference('8JxK2aQw')).toBe(true);
    expect(isSupportedOrderReference('12345')).toBe(true);
  });

  it('rejects unsupported references and normalizes order numbers', () => {
    expect(isSupportedOrderReference('ORD-20-41')).toBe(false);
    expect(isSupportedOrderReference('')).toBe(false);
    expect(normalizeOrderReference('ord-2025-0041')).toBe('ORD-2025-0041');
    expect(normalizeOrderReference('8JxK2aQw')).toBe('8JxK2aQw');
  });
});
