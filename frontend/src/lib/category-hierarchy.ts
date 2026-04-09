import type { CatalogCategory } from '@/types';

export function deriveCategoryLevel(parentId: string | null | undefined, categories: CatalogCategory[]): number {
  if (!parentId) return 1;
  const parent = categories.find((item) => item.id === parentId);
  return (parent?.level ?? 0) + 1;
}

export function wouldCreateCycle(categoryId: string, parentId: string | null | undefined, categories: CatalogCategory[]): boolean {
  if (!parentId) return false;
  if (categoryId === parentId) return true;
  const byId = new Map(categories.map((item) => [item.id, item]));
  let cursor: string | null | undefined = parentId;
  while (cursor) {
    if (cursor === categoryId) return true;
    cursor = byId.get(cursor)?.parent_id;
  }
  return false;
}
