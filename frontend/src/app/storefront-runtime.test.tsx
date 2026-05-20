import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { act, type ReactElement, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ShopPage from './shop/page';
import VendorProductsPage from './(vendor-dashboard)/vendor/products/page';
import ProductDetailPage from './products/[productId]/page';
import type { CatalogProduct } from '@/types';

// React 19 requires this flag for manual act() usage in jsdom tests.
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const useParamsMock = vi.fn();
const useCatalogProductsMock = vi.fn();
const useCatalogAutocompleteMock = vi.fn();
const useCatalogCategoriesMock = vi.fn();
const useCatalogBrandsMock = vi.fn();
const useCatalogProductMock = vi.fn();
const useCatalogRecommendationsMock = vi.fn();
const useVendorProductsMock = vi.fn();
const useWishlistMock = vi.fn();
const useAddToCartMock = vi.fn();
const useAddToWishlistMock = vi.fn();
const useRemoveFromWishlistMock = vi.fn();
const useAuthStoreMock = vi.fn();

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('next/navigation', () => ({
  useParams: () => useParamsMock(),
}));

vi.mock('@/hooks/use-catalog', () => ({
  useCatalogProducts: (...args: unknown[]) => useCatalogProductsMock(...args),
  useCatalogAutocomplete: (...args: unknown[]) => useCatalogAutocompleteMock(...args),
  useCatalogCategories: (...args: unknown[]) => useCatalogCategoriesMock(...args),
  useCatalogBrands: (...args: unknown[]) => useCatalogBrandsMock(...args),
  useCatalogProduct: (...args: unknown[]) => useCatalogProductMock(...args),
  useCatalogRecommendations: (...args: unknown[]) => useCatalogRecommendationsMock(...args),
  useVendorProducts: (...args: unknown[]) => useVendorProductsMock(...args),
}));

vi.mock('@/hooks/use-commerce', () => ({
  useWishlist: (...args: unknown[]) => useWishlistMock(...args),
  useAddToCart: (...args: unknown[]) => useAddToCartMock(...args),
  useAddToWishlist: (...args: unknown[]) => useAddToWishlistMock(...args),
  useRemoveFromWishlist: (...args: unknown[]) => useRemoveFromWishlistMock(...args),
  useApiErrorMessage: () => ({ getErrorMessage: () => 'Request failed' }),
}));

vi.mock('@/store/auth-store', () => ({
  useAuthStore: () => useAuthStoreMock(),
}));

vi.mock('@/components/storefront/site-header', () => ({
  SiteHeader: () => <div>Header</div>,
}));

vi.mock('@/components/storefront/site-footer', () => ({
  SiteFooter: () => <div>Footer</div>,
}));

vi.mock('@/components/storefront/product-card', () => ({
  ProductCard: ({ product }: { product: CatalogProduct }) => <div data-testid="product-card">{product.name}</div>,
}));

function createProduct(overrides: Partial<CatalogProduct> = {}): CatalogProduct {
  return {
    id: 'prod-1',
    vendor_id: 'vendor-1',
    category: { id: 'cat-1', name: 'Lighting', slug: 'lighting' },
    brand: { id: 'brand-1', name: 'Northline', slug: 'northline' },
    name: 'Sculpted Table Lamp',
    slug: 'sculpted-table-lamp',
    short_description: 'Warm ceramic glow for focused corners.',
    description: 'A tactile lamp built for worktops, sideboards, and reading nooks.',
    specifications: {},
    status: 'active',
    avg_rating: 4.8,
    review_count: 132,
    view_count: 904,
    is_featured: true,
    images: [],
    variants: [
      {
        id: 'variant-1',
        sku: 'lamp-standard',
        name: 'Standard',
        mrp: 94,
        selling_price: 94,
        attributes: { finish: 'matte' },
        available_qty: 10,
        is_default: true,
        is_active: true,
      },
    ],
    min_selling_price: 94,
    in_stock: true,
    created_at: '2026-03-23T00:00:00Z',
    ...overrides,
  };
}

function queryState<T>(overrides: Partial<{
  data: T;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => Promise<unknown>;
}>) {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

function render(element: ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(element);
  });
  return {
    container,
    unmount() {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function findButton(container: HTMLElement, label: string) {
  return Array.from(container.querySelectorAll('button')).find((button) => button.textContent?.includes(label));
}

function axiosError(status: number) {
  return { isAxiosError: true, response: { status } };
}

describe('storefront runtime states', () => {
  let roots: Array<{ unmount: () => void }> = [];

  beforeEach(() => {
    vi.spyOn(axios, 'isAxiosError').mockImplementation((value) => Boolean((value as { isAxiosError?: boolean })?.isAxiosError));
    useParamsMock.mockReturnValue({ productId: 'prod-1' });
    useCatalogProductsMock.mockReturnValue(queryState({ data: { items: [createProduct()], total: 1 } }));
    useCatalogAutocompleteMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    useCatalogCategoriesMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    useCatalogBrandsMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    useCatalogProductMock.mockReturnValue(queryState({ data: createProduct() }));
    useCatalogRecommendationsMock.mockReturnValue(
      queryState({ data: { strategy: 'ml_ranker_v2', items: [createProduct({ id: 'prod-2', name: 'Recommended Lamp' })] } })
    );
    useVendorProductsMock.mockReturnValue(queryState({ data: { items: [createProduct()], total: 1 } }));
    useWishlistMock.mockReturnValue({ data: { items: [] } });
    useAddToCartMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    useAddToWishlistMock.mockReturnValue({ mutateAsync: vi.fn() });
    useRemoveFromWishlistMock.mockReturnValue({ mutateAsync: vi.fn() });
    useAuthStoreMock.mockReturnValue({ isAuthenticated: true });
  });

  afterEach(() => {
    roots.forEach((root) => root.unmount());
    roots = [];
    document.body.innerHTML = '';
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it('keeps audited production pages free of mock-commerce imports', () => {
    const auditedFiles = [
      'app/page.tsx',
      'app/shop/page.tsx',
      'app/products/[productId]/page.tsx',
      'app/(vendor-dashboard)/vendor/products/page.tsx',
      'app/(user-dashboard)/dashboard/page.tsx',
    ];

    for (const relativePath of auditedFiles) {
      const source = fs.readFileSync(
        path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', relativePath),
        'utf-8'
      );
      expect(source).not.toContain('mock-commerce');
    }
  });

  it('renders a loading state on the shop page', () => {
    useCatalogProductsMock.mockReturnValue(queryState({ isLoading: true }));
    const view = render(<ShopPage />);
    roots.push(view);

    expect(view.container.querySelector('[aria-label="Loading products"]')).not.toBeNull();
  });

  it('renders an empty state on the shop page when the API returns no products', () => {
    useCatalogProductsMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    const view = render(<ShopPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('Try a broader search or switch collections.');
  });

  it('renders an error state on the shop page and retries on demand', () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    useCatalogProductsMock.mockReturnValue(
      queryState({
        isError: true,
        error: axiosError(500),
        refetch,
      })
    );
    const view = render(<ShopPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('Products unavailable');
    const retryButton = findButton(view.container, 'Retry');
    expect(retryButton).toBeTruthy();

    act(() => {
      retryButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(refetch).toHaveBeenCalledOnce();
  });

  it('renders vendor loading and empty states honestly', () => {
    useVendorProductsMock.mockReturnValueOnce(queryState({ isLoading: true }));
    const loadingView = render(<VendorProductsPage />);
    roots.push(loadingView);
    expect(loadingView.container.querySelector('[aria-label="Loading vendor products"]')).not.toBeNull();

    useVendorProductsMock.mockReturnValueOnce(queryState({ data: { items: [], total: 0 } }));
    const emptyView = render(<VendorProductsPage />);
    roots.push(emptyView);
    expect(emptyView.container.textContent).toContain('No products yet');
  });

  it('renders a vendor error state with retry', () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    useVendorProductsMock.mockReturnValue(
      queryState({
        isError: true,
        error: axiosError(403),
        refetch,
      })
    );
    const view = render(<VendorProductsPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('Inventory unavailable');
    expect(view.container.textContent).toContain('access denied for this resource');

    const retryButton = findButton(view.container, 'Retry');
    act(() => {
      retryButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(refetch).toHaveBeenCalledOnce();
  });

  it('renders loading and not-found states on the product page', () => {
    useCatalogProductMock.mockReturnValueOnce(queryState({ isLoading: true }));
    const loadingView = render(<ProductDetailPage />);
    roots.push(loadingView);
    expect(loadingView.container.querySelector('[aria-label="Loading product detail"]')).not.toBeNull();

    useCatalogProductMock.mockReturnValueOnce(
      queryState({
        isError: true,
        error: axiosError(404),
      })
    );
    const missingView = render(<ProductDetailPage />);
    roots.push(missingView);
    expect(missingView.container.textContent).toContain('This product does not exist');
  });

  it('keeps cart and wishlist actions disabled when the product has no real variants', () => {
    useCatalogProductMock.mockReturnValue(
      queryState({
        data: createProduct({ variants: [], min_selling_price: 94 }),
      })
    );
    const view = render(<ProductDetailPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('Real variant inventory is not available for this product yet');

    const buttons = Array.from(view.container.querySelectorAll('button'));
    const addToCartButton = buttons.find((button) => button.textContent?.includes('Add to cart'));
    const wishlistButton = buttons.find((button) => button.textContent?.includes('Save for later'));

    expect(addToCartButton?.hasAttribute('disabled')).toBe(true);
    expect(wishlistButton?.hasAttribute('disabled')).toBe(true);
  });

  it('renders a retryable product error state for non-404 failures', () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    useCatalogProductMock.mockReturnValue(
      queryState({
        isError: true,
        error: axiosError(500),
        refetch,
      })
    );
    const view = render(<ProductDetailPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('We could not load this product');

    const retryButton = findButton(view.container, 'Retry');
    act(() => {
      retryButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(refetch).toHaveBeenCalledOnce();
  });
});
