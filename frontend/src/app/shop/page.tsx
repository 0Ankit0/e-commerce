'use client';

import axios from 'axios';
import { useDeferredValue, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { useCatalogBrands, useCatalogCategories, useCatalogProducts } from '@/hooks/use-catalog';
import { ProductCard } from '@/components/storefront/product-card';
import { SiteHeader } from '@/components/storefront/site-header';
import { SiteFooter } from '@/components/storefront/site-footer';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency } from '@/lib/commerce-format';

export default function ShopPage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [brand, setBrand] = useState('');
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const deferredQuery = useDeferredValue(query);
  const {
    data: productsData,
    isLoading: isProductsLoading,
    isError: isProductsError,
    error: productsError,
    refetch: refetchProducts,
  } = useCatalogProducts({
    q: deferredQuery || undefined,
    category: category || undefined,
    brand: brand || undefined,
    isFeatured: featuredOnly || undefined,
    limit: 24,
  });
  const {
    data: categoriesData,
    isLoading: areCategoriesLoading,
    isError: areCategoriesError,
  } = useCatalogCategories();
  const { data: brandsData } = useCatalogBrands();

  const products = productsData?.items ?? [];
  const categories = categoriesData?.items ?? [];
  const brands = brandsData?.items ?? [];
  const groupedCategories = useMemo(() => categories.slice(0, 6), [categories]);
  const productsErrorStatus = axios.isAxiosError(productsError) ? productsError.response?.status : undefined;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="rounded-[36px] border border-[var(--border-color)] bg-white p-6 shadow-[0_20px_60px_rgba(25,30,45,0.06)] sm:p-8">
          <div className="grid gap-6 lg:grid-cols-[0.7fr_1.3fr]">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">All products</p>
              <h1 className="mt-4 font-[family:var(--font-display)] text-5xl leading-none text-[var(--text-primary)]">
                A storefront built for browsing and buying.
              </h1>
              <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
                Search the catalog, jump across featured collections, and connect each product card to the live backend product detail route.
              </p>
            </div>
            <div className="grid gap-4">
              <div className="flex flex-col gap-3 sm:flex-row">
                <label className="flex flex-1 items-center gap-3 rounded-full border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3">
                  <Search className="h-4 w-4 text-[var(--text-muted)]" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search products, materials, moods..."
                    className="w-full bg-transparent text-sm outline-none"
                    aria-label="Search products"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => setFeaturedOnly((value) => !value)}
                  className={`rounded-full px-5 py-3 text-sm font-medium transition-colors ${
                    featuredOnly ? 'bg-[var(--foreground)] text-[var(--background)]' : 'border border-[var(--border-color)] bg-white text-[var(--text-secondary)]'
                  }`}
                >
                  Featured only
                </button>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <label className="rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">Category</span>
                  <select
                    value={category}
                    onChange={(event) => setCategory(event.target.value)}
                    className="w-full bg-transparent outline-none"
                    aria-label="Category"
                  >
                    <option value="">All collections</option>
                    {categories.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">Brand</span>
                  <select
                    value={brand}
                    onChange={(event) => setBrand(event.target.value)}
                    className="w-full bg-transparent outline-none"
                    aria-label="Brand"
                  >
                    <option value="">All makers</option>
                    {brands.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">Visible results</span>
                  <div className="flex items-end justify-between gap-3">
                    <p className="font-[family:var(--font-display)] text-3xl text-[var(--text-primary)]">{products.length}</p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      from {products[0]?.min_selling_price ? formatCurrency(products[0].min_selling_price) : 'live quotes'}
                    </p>
                  </div>
                </div>
              </div>
              {areCategoriesLoading ? (
                <div className="flex flex-wrap gap-2">
                  {[1, 2, 3].map((item) => (
                    <div key={item} className="h-7 w-28 animate-pulse rounded-full bg-[var(--surface-muted)]" />
                  ))}
                </div>
              ) : areCategoriesError ? (
                <p className="text-sm text-[var(--text-secondary)]">Category chips are unavailable right now, but product search is still live.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {groupedCategories.map((item) => (
                    <span key={item.id} className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                      {item.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {isProductsLoading ? (
          <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-3" role="status" aria-label="Loading products">
            {[1, 2, 3, 4, 5, 6].map((item) => (
              <div key={item} className="h-[420px] animate-pulse rounded-[28px] bg-white" />
            ))}
          </div>
        ) : isProductsError ? (
          <div className="mt-10">
            <StorefrontState
              eyebrow={productsErrorStatus === 404 ? 'Catalog not found' : 'Catalog unavailable'}
              title={productsErrorStatus === 404 ? 'Catalog endpoint not found' : 'Products unavailable'}
              description={
                productsErrorStatus === 404
                  ? 'The live products endpoint did not return a catalog response for this storefront request.'
                  : 'The storefront could not load products from the live API. No placeholder products are shown when the catalog request fails.'
              }
              actionLabel="Retry"
              onAction={() => {
                void refetchProducts();
              }}
            />
          </div>
        ) : products.length === 0 ? (
          <div className="mt-10">
            <StorefrontState
              eyebrow="No exact matches"
              title="Try a broader search or switch collections."
              description="The backend search and filters are live, but this combination of query, category, and brand returned no products."
            />
          </div>
        ) : (
          <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
