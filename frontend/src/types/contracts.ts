export type ApiEnum<T extends string> = T | 'unknown';

export const asApiEnum = <T extends string>(value: string, known: readonly T[]): ApiEnum<T> => {
  return known.includes(value as T) ? (value as T) : 'unknown';
};

export interface StrictPaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}
