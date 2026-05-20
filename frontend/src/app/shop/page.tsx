'use client';

import axios from 'axios';
import { useDeferredValue, useState } from 'react';
import { Search } from 'lucide-react';
import { useCatalogAutocomplete, useCatalogBrands, useCatalogCategories, useCatalogProducts } from '@/hooks/use-catalog';
import { ProductCard } from '@/components/storefront/product-card';
import { SiteHeader } from '@/components/storefront/site-header';
import { SiteFooter } from '@/components/storefront/site-footer';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency } from '@/lib/commerce-format';
import { getRuntimeErrorState, isPaginatedPayload } from '@/lib/runtime-route';

export default function ShopPage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [brand, setBrand] = useState('');
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const deferredQuery = useDeferredValue(query);
  const trimmedQuery = query.trim();
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
  const { data: autocompleteData } = useCatalogAutocomplete(deferredQuery);
  const {
    data: categoriesData,
    isLoading: areCategoriesLoading,
    isError: areCategoriesError,
    error: categoriesError,
    refetch: refetchCategories,
  } = useCatalogCategories();
  const { data: brandsData } = useCatalogBrands();

  const products = productsData?.items ?? [];
  const searchSuggestions = autocompleteData?.items ?? [];
  const categories = categoriesData?.items ?? [];
  const brands = brandsData?.items ?? [];
  const groupedCategories = categories.slice(0, 6);
  const visibleResults = productsData?.total ?? products.length;
  const productsErrorStatus = axios.isAxiosError(productsError) ? productsError.response?.status : undefined;
  const hasPartialProductsPayload = productsData !== undefined && !isPaginatedPayload(productsData);
  const hasPartialCategoriesPayload = categoriesData !== undefined && !isPaginatedPayload(categoriesData);
  const productsRuntimeError = getRuntimeErrorState(productsError, 'Products unavailable');
  const categoriesRuntimeError = getRuntimeErrorState(categoriesError, 'Collections unavailable');

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
                  <div className="relative w-full">
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Search products, materials, moods..."
                      className="w-full bg-transparent text-sm outline-none"
                      aria-label="Search products"
                    />
                    {trimmedQuery.length >= 2 && searchSuggestions.length > 0 ? (
                      <div className="absolute left-0 right-0 top-[calc(100%+0.75rem)] z-10 rounded-[24px] border border-[var(--border-color)] bg-white p-2 shadow-[0_20px_55px_rgba(25,30,45,0.12)]">
                        {searchSuggestions.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setQuery(item.name)}
                            className="flex w-full items-center justify-between rounded-[18px] px-3 py-2 text-left transition-colors hover:bg-[var(--surface-muted)]"
                          >
                            <div>
                              <p className="text-sm font-medium text-[var(--text-primary)]">{item.name}</p>
                              {item.reason ? <p className="text-xs text-[var(--text-secondary)]">{item.reason}</p> : null}
                            </div>
                            <span className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">
                              {item.score.toFixed(1)}
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
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
                    <p className="font-[family:var(--font-display)] text-3xl text-[var(--text-primary)]">{visibleResults}</p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {trimmedQuery ? 'ranked by relevance' : `from ${products[0]?.min_selling_price ? formatCurrency(products[0].min_selling_price) : 'live quotes'}`}
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
              ) : areCategoriesError || hasPartialCategoriesPayload ? (
                <StorefrontState
                  eyebrow="Collections"
                  title="Collections unavailable"
                  description={
                    hasPartialCategoriesPayload
                      ? 'The collections API returned an incomplete payload, so category chips are hidden until a complete response is available.'
                      : categoriesRuntimeError.description
                  }
                  details={
                    hasPartialCategoriesPayload
                      ? 'Payload validation failed: expected { items: [], total: number } from /categories.'
                      : categoriesRuntimeError.details
                  }
                  actionLabel="Retry"
                  onAction={() => {
                    void refetchCategories();
                  }}
                />
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
        ) : isProductsError || hasPartialProductsPayload ? (
          <div className="mt-10">
            <StorefrontState
              eyebrow={productsErrorStatus === 404 ? 'Catalog not found' : 'Catalog unavailable'}
              title={hasPartialProductsPayload ? 'Catalog response incomplete' : productsRuntimeError.title}
              description={
                hasPartialProductsPayload
                  ? 'The products API returned a partial payload. This route avoids hidden fallback behavior and is blocking render until complete data is available.'
                  : productsRuntimeError.description
              }
              details={
                hasPartialProductsPayload
                  ? 'Payload validation failed: expected { items: [], total: number } from /products.'
                  : productsRuntimeError.details
              }
              actionLabel={productsRuntimeError.actionLabel}
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
              description="The live full-text search and filters did not find a match for this combination of query, category, and brand."
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
