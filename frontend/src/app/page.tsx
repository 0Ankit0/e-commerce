'use client';

import Link from 'next/link';
import { ArrowRight, Layers3, ShieldCheck, Sparkles, Store, Truck, Wallet } from 'lucide-react';
import { useCatalogCategories, useFeaturedProducts } from '@/hooks/use-catalog';
import { useAuthStore } from '@/store/auth-store';
import { SiteFooter } from '@/components/storefront/site-footer';
import { SiteHeader } from '@/components/storefront/site-header';
import { ProductCard } from '@/components/storefront/product-card';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { getDefaultPortalPath } from '@/lib/portal';

export default function Home() {
  const { isAuthenticated, user } = useAuthStore();
  const {
    data: featuredProductsData,
    isLoading: isFeaturedLoading,
    isError: isFeaturedError,
    refetch: refetchFeaturedProducts,
  } = useFeaturedProducts(6);
  const {
    data: categoriesData,
    isLoading: areCategoriesLoading,
    isError: areCategoriesError,
    refetch: refetchCategories,
  } = useCatalogCategories();

  const featuredProducts = featuredProductsData?.items ?? [];
  const categories = categoriesData?.items?.slice(0, 4) ?? [];
  const portalHref = getDefaultPortalPath(user);

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--text-primary)]">
      <SiteHeader />

      <main>
        <section className="grain-overlay overflow-hidden border-b border-[var(--border-color)] [background:linear-gradient(135deg,var(--surface-muted)_0%,var(--accent-soft)_54%,var(--success-soft)_100%)]">
          <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8 lg:py-24">
            <div className="relative z-[1]">
              <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border-color)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-[var(--text-muted)] shadow-[0_12px_30px_rgba(25,30,45,0.05)]">
                <Sparkles className="h-3.5 w-3.5" />
                Marketplace + operations portals
              </div>
              <h1 className="mt-8 max-w-3xl font-[family:var(--font-display)] text-6xl leading-[0.92] sm:text-7xl">
                Commerce with a public storefront and the right dashboard for every operator.
              </h1>
              <p className="mt-6 max-w-2xl text-lg text-[var(--text-secondary)]">
                Northstar Market combines product discovery, wishlists, checkout, shipping, payouts, and admin oversight in one web experience built around who you are and what you’re allowed to do.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/shop"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-[var(--foreground)] px-6 py-3 text-sm font-semibold text-[var(--background)] shadow-[0_18px_40px_rgba(0,0,0,0.18)] transition-transform hover:-translate-y-0.5"
                >
                  Browse products
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href={isAuthenticated ? portalHref : '/signup'}
                  className="inline-flex items-center justify-center gap-2 rounded-full border border-[var(--border-color)] bg-white px-6 py-3 text-sm font-semibold text-[var(--text-secondary)] shadow-[0_12px_30px_rgba(25,30,45,0.06)] transition-transform hover:-translate-y-0.5"
                >
                  {isAuthenticated ? 'Open your portal' : 'Create an account'}
                </Link>
              </div>
              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                {[
                  { value: '4', label: 'role-aware portals' },
                  { value: '6', label: 'supported payment methods' },
                  { value: '24/7', label: 'operations visibility' },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-[26px] border border-[var(--border-color)] bg-white p-5 backdrop-blur">
                    <p className="font-[family:var(--font-display)] text-4xl">{stat.value}</p>
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">{stat.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 translate-x-6 translate-y-8 rounded-[40px] bg-[var(--foreground)]" />
              <div className="relative overflow-hidden rounded-[40px] border border-[var(--border-color)] bg-white p-6 shadow-[0_24px_70px_rgba(25,30,45,0.12)]">
                {isFeaturedLoading ? (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {[1, 2].map((item) => (
                      <div key={item} className="h-48 animate-pulse rounded-[28px] bg-[var(--surface-muted)]" />
                    ))}
                  </div>
                ) : isFeaturedError ? (
                  <StorefrontState
                    eyebrow="Storefront"
                    title="Featured products unavailable"
                    description="The home page could not load the live featured catalog feed."
                    actionLabel="Retry"
                    onAction={() => {
                      void refetchFeaturedProducts();
                    }}
                  />
                ) : featuredProducts.length === 0 ? (
                  <StorefrontState
                    eyebrow="Storefront"
                    title="No featured products yet"
                    description="Featured inventory has not been published yet, so the home page is waiting for live catalog data."
                  />
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {featuredProducts.slice(0, 2).map((product) => (
                      <div key={product.id} className="rounded-[28px] border border-[var(--border-color)] bg-[var(--surface-muted)] p-5">
                        <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
                          {product.category?.name ?? 'Curated'}
                        </p>
                        <h3 className="mt-3 font-[family:var(--font-display)] text-3xl">{product.name}</h3>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">{product.short_description}</p>
                        <div className="mt-5 flex items-center justify-between">
                          <span className="text-lg font-semibold">
                            {product.min_selling_price ? `$${product.min_selling_price.toFixed(0)}` : 'Quote'}
                          </span>
                          <span className="rounded-full bg-white px-3 py-1 text-xs text-[var(--text-secondary)] shadow-[0_10px_24px_rgba(25,30,45,0.06)]">
                            {product.in_stock ? 'In stock' : 'Back soon'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-4 rounded-[30px] bg-[var(--foreground)] p-5 text-[var(--background)]">
                  <p className="text-xs uppercase tracking-[0.24em] opacity-60">Portal controls</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {[
                      { icon: Store, title: 'Customer dashboard', text: 'Orders, returns, wishlist, notifications' },
                      { icon: Truck, title: 'Vendor desk', text: 'Catalog, inventory, shipping labels, payouts' },
                      { icon: Wallet, title: 'Admin control', text: 'Live feed, moderation, content, reports' },
                      { icon: ShieldCheck, title: 'Agent console', text: 'Assignments, delivery history, POD flow' },
                    ].map((item) => (
                      <div key={item.title} className="rounded-[24px] border border-[rgba(128,128,128,0.2)] bg-[rgba(128,128,128,0.06)] p-4">
                        <item.icon className="h-4 w-4 text-[var(--accent-soft)]" />
                        <p className="mt-3 font-medium">{item.title}</p>
                        <p className="mt-1 text-sm opacity-70">{item.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="collections" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="mb-10 flex items-end justify-between gap-6">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">Collections</p>
              <h2 className="mt-3 font-[family:var(--font-display)] text-5xl">Browse by mood, room, and ritual.</h2>
            </div>
            <Link href="/shop" className="hidden text-sm font-semibold text-[var(--accent)] sm:inline-flex">
              View full catalog
            </Link>
          </div>
          {areCategoriesLoading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {[1, 2, 3, 4].map((item) => (
                <div key={item} className="h-56 animate-pulse rounded-[30px] bg-white" />
              ))}
            </div>
          ) : areCategoriesError ? (
            <StorefrontState
              eyebrow="Collections"
              title="Collections unavailable"
              description="The storefront could not load the live category list."
              actionLabel="Retry"
              onAction={() => {
                void refetchCategories();
              }}
            />
          ) : categories.length === 0 ? (
            <StorefrontState
              eyebrow="Collections"
              title="No collections published yet"
              description="Category navigation will appear here as soon as catalog collections are available from the backend."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {categories.map((category, index) => (
                <Link
                  key={category.id}
                  href={`/shop?category=${category.id}`}
                  className="rounded-[30px] border border-[var(--border-color)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)] transition-transform hover:-translate-y-1"
                  style={{
                    backgroundImage:
                      index % 2 === 0
                        ? 'linear-gradient(135deg, color-mix(in srgb, var(--accent-soft) 28%, var(--surface)), var(--surface))'
                        : 'linear-gradient(135deg, color-mix(in srgb, var(--success-soft) 55%, var(--surface)), var(--surface))',
                  }}
                >
                  <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Collection</p>
                  <h3 className="mt-6 font-[family:var(--font-display)] text-3xl">{category.name}</h3>
                  <p className="mt-3 text-sm text-[var(--text-secondary)]">{category.description || 'Curated category for focused browsing.'}</p>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-10 flex items-end justify-between gap-6">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">Featured now</p>
              <h2 className="mt-3 font-[family:var(--font-display)] text-5xl">Products ready for the main web storefront.</h2>
            </div>
            <Link href="/shop" className="hidden text-sm font-semibold text-[var(--accent)] sm:inline-flex">
              See all products
            </Link>
          </div>
          {isFeaturedLoading ? (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-[420px] animate-pulse rounded-[28px] bg-white" />
              ))}
            </div>
          ) : isFeaturedError ? (
            <StorefrontState
              eyebrow="Featured now"
              title="Featured feed unavailable"
              description="The storefront could not load featured products from the live API."
              actionLabel="Retry"
              onAction={() => {
                void refetchFeaturedProducts();
              }}
            />
          ) : featuredProducts.length === 0 ? (
            <StorefrontState
              eyebrow="Featured now"
              title="Nothing featured yet"
              description="Featured products will appear here after vendors publish inventory and mark items as featured."
            />
          ) : (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {featuredProducts.slice(0, 6).map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </section>

        <section id="services" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-3">
            {[
              {
                icon: Layers3,
                title: 'Role-aware navigation',
                description: 'Each portal only shows the links a signed-in user can actually access.',
              },
              {
                icon: Truck,
                title: 'Operations-ready flows',
                description: 'Shipping labels, delivery exceptions, returns, and live operational status are wired into the web experience.',
              },
              {
                icon: Wallet,
                title: 'Commerce-native controls',
                description: 'Payouts, payment providers, admin reporting, and notifications are surfaced where each user needs them.',
              },
            ].map((feature) => (
              <div key={feature.title} className="rounded-[32px] border border-[var(--border-color)] bg-white p-7 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
                <feature.icon className="h-5 w-5 text-[var(--accent)]" />
                <h3 className="mt-5 font-[family:var(--font-display)] text-3xl">{feature.title}</h3>
                <p className="mt-3 text-sm leading-6 text-[#66584c]">{feature.description}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
