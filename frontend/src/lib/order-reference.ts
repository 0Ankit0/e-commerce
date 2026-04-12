const CURRENT_ORDER_REFERENCE = /^ORD-[A-Z0-9]{10}$/;
const LEGACY_ORDER_REFERENCE = /^ORD-\d{4}-[A-Z0-9]{4,}$/;
const HASHID_OR_NUMERIC = /^[A-Za-z0-9]{2,}$/;

export const ORDER_REFERENCE_PLACEHOLDER = 'ORD-XXXXXXXXXX or hashid';

export function isOrderNumber(value: string): boolean {
  const normalized = value.trim().toUpperCase();
  return CURRENT_ORDER_REFERENCE.test(normalized) || LEGACY_ORDER_REFERENCE.test(normalized);
}

export function isSupportedOrderReference(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (isOrderNumber(trimmed)) return true;
  return HASHID_OR_NUMERIC.test(trimmed);
}

export function normalizeOrderReference(value: string): string {
  const trimmed = value.trim();
  return isOrderNumber(trimmed) ? trimmed.toUpperCase() : trimmed;
}
