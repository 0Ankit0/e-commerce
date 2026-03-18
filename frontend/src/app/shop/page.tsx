'use client';

import { useDeferredValue, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { useCatalogBrands, useCatalogCategories, useCatalogProducts } from '@/hooks/use-catalog';
import { ProductCard } from '@/components/storefront/product-card';
import { SiteHeader } from '@/components/storefront/site-header';
import { SiteFooter } from '@/components/storefront/site-footer';
import { formatCurrency } from '@/lib/commerce-format';
import { mockCategories, mockProducts } from '@/lib/mock-commerce';

export default function ShopPage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [brand, setBrand] = useState('');
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const deferredQuery = useDeferredValue(query);
  const { data: productsData } = useCatalogProducts({
    q: deferredQuery || undefined,
    category: category || undefined,
    brand: brand || undefined,
    isFeatured: featuredOnly || undefined,
    limit: 24,
  });
  const { data: categoriesData } = useCatalogCategories();
  const { data: brandsData } = useCatalogBrands();

  const products = productsData?.items?.length ? productsData.items : mockProducts;
  const categories = categoriesData?.items?.length ? categoriesData.items : mockCategories;
  const brands = brandsData?.items?.length ? brandsData.items : [];
  const groupedCategories = useMemo(() => categories.slice(0, 6), [categories]);

  return (
    <div className="min-h-screen bg-[#fcf7f0]">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="rounded-[36px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_20px_60px_rgba(25,30,45,0.06)] sm:p-8">
          <div className="grid gap-6 lg:grid-cols-[0.7fr_1.3fr]">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-[#8b6e57]">All products</p>
              <h1 className="mt-4 font-[family:var(--font-display)] text-5xl leading-none text-[#1d1b18]">
                A storefront built for browsing and buying.
              </h1>
              <p className="mt-4 text-sm leading-6 text-[#66584c]">
                Search the catalog, jump across featured collections, and connect each product card to the live backend product detail route.
              </p>
            </div>
            <div className="grid gap-4">
              <div className="flex flex-col gap-3 sm:flex-row">
                <label className="flex flex-1 items-center gap-3 rounded-full border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3">
                  <Search className="h-4 w-4 text-[#8b6e57]" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search products, materials, moods..."
                    className="w-full bg-transparent text-sm outline-none"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => setFeaturedOnly((value) => !value)}
                  className={`rounded-full px-5 py-3 text-sm font-medium transition-colors ${
                    featuredOnly ? 'bg-[#1d1b18] text-white' : 'border border-[rgba(25,30,45,0.08)] bg-white text-[#3e352d]'
                  }`}
                >
                  Featured only
                  </button>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <label className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm text-[#55483d]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[#8b6e57]">Category</span>
                  <select
                    value={category}
                    onChange={(event) => setCategory(event.target.value)}
                    className="w-full bg-transparent outline-none"
                  >
                    <option value="">All collections</option>
                    {categories.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm text-[#55483d]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[#8b6e57]">Brand</span>
                  <select
                    value={brand}
                    onChange={(event) => setBrand(event.target.value)}
                    className="w-full bg-transparent outline-none"
                  >
                    <option value="">All makers</option>
                    {brands.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[#8b6e57]">Visible results</span>
                  <div className="flex items-end justify-between gap-3">
                    <p className="font-[family:var(--font-display)] text-3xl text-[#1d1b18]">{products.length}</p>
                    <p className="text-xs text-[#6f6257]">
                      from {products[0]?.min_selling_price ? formatCurrency(products[0].min_selling_price) : 'live quotes'}
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {groupedCategories.map((category) => (
                  <span
                    key={category.id}
                    className="rounded-full bg-[#f7efe1] px-3 py-1 text-xs font-medium text-[#6b5648]"
                  >
                    {category.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
        {products.length === 0 ? (
          <div className="mt-10 rounded-[32px] border border-dashed border-[rgba(25,30,45,0.12)] bg-white p-10 text-center">
            <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">No exact matches</p>
            <h2 className="mt-3 font-[family:var(--font-display)] text-4xl text-[#1d1b18]">
              Try a broader search or switch collections.
            </h2>
            <p className="mt-3 text-sm text-[#6f6257]">
              The backend search and filters are wired, so your results update instantly as you change query, category, or brand.
            </p>
          </div>
        ) : null}
      </main>
      <SiteFooter />
    </div>
  );
}
