import { describe, expect, it } from 'vitest';
import { deriveCategoryLevel, wouldCreateCycle } from './category-hierarchy';

const categories = [
  { id: 'a', name: 'A', slug: 'a', level: 1, description: '', attributes: [] },
  { id: 'b', parent_id: 'a', name: 'B', slug: 'b', level: 2, description: '', attributes: [] },
  { id: 'c', parent_id: 'b', name: 'C', slug: 'c', level: 3, description: '', attributes: [] },
];

describe('category hierarchy helpers', () => {
  it('derives levels from parent chain', () => {
    expect(deriveCategoryLevel(undefined, categories)).toBe(1);
    expect(deriveCategoryLevel('a', categories)).toBe(2);
    expect(deriveCategoryLevel('b', categories)).toBe(3);
  });

  it('detects cycles', () => {
    expect(wouldCreateCycle('a', 'c', categories)).toBe(true);
    expect(wouldCreateCycle('b', 'b', categories)).toBe(true);
    expect(wouldCreateCycle('c', 'a', categories)).toBe(false);
  });
});
