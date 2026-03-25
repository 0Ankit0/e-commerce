'use client';

import Link from 'next/link';
import { Search, ShoppingBag, Sparkles, Store } from 'lucide-react';
import { useCart } from '@/hooks/use-commerce';
import { useAuthStore } from '@/store/auth-store';
import { getDefaultPortalPath } from '@/lib/portal';

export function SiteHeader() {
  const { isAuthenticated, user } = useAuthStore();
  const portalHref = getDefaultPortalPath(user);
  const { data: cart } = useCart(isAuthenticated);
  const itemCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--border-color)] bg-[color-mix(in_srgb,var(--background)_86%,transparent)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3 text-[var(--text-primary)]">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--foreground)] text-[var(--background)] shadow-[0_15px_35px_rgba(0,0,0,0.2)]">
            <Store className="h-5 w-5" />
          </div>
          <div>
            <p className="font-[family:var(--font-display)] text-2xl leading-none">Northstar Market</p>
            <p className="mt-1 text-[10px] uppercase tracking-[0.28em] text-[var(--text-muted)]">
              Crafted marketplace
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium text-[var(--text-secondary)] md:flex">
          <Link href="/shop" className="transition-colors hover:text-[var(--text-primary)]">Shop</Link>
          <a href="#collections" className="transition-colors hover:text-[var(--text-primary)]">Collections</a>
          <a href="#vendors" className="transition-colors hover:text-[var(--text-primary)]">Vendors</a>
          <a href="#services" className="transition-colors hover:text-[var(--text-primary)]">Services</a>
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/shop"
            className="hidden rounded-full border border-[var(--border-color)] bg-white px-4 py-2 text-sm font-medium text-[var(--text-secondary)] shadow-[0_12px_24px_rgba(25,30,45,0.05)] sm:inline-flex sm:items-center sm:gap-2"
          >
            <Search className="h-4 w-4" />
            Explore
          </Link>
          <Link
            href="/cart"
            className="relative inline-flex h-11 w-11 items-center justify-center rounded-full border border-[var(--border-color)] bg-white text-[var(--text-secondary)] shadow-[0_12px_24px_rgba(25,30,45,0.05)] transition-transform hover:-translate-y-0.5"
            aria-label="Open cart"
          >
            <ShoppingBag className="h-4 w-4" />
            {itemCount > 0 ? (
              <span className="absolute -right-1 -top-1 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[var(--accent)] px-1 text-[10px] font-semibold text-[var(--accent-foreground)]">
                {itemCount > 9 ? '9+' : itemCount}
              </span>
            ) : null}
          </Link>
          {isAuthenticated ? (
            <Link
              href={portalHref}
              className="inline-flex items-center gap-2 rounded-full bg-[var(--foreground)] px-4 py-2 text-sm font-medium text-[var(--background)] shadow-[0_15px_35px_rgba(0,0,0,0.18)] transition-transform hover:-translate-y-0.5"
            >
              <Sparkles className="h-4 w-4" />
              Open dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className="rounded-full px-4 py-2 text-sm font-medium text-[var(--text-secondary)]">
                Sign in
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 rounded-full bg-[var(--foreground)] px-4 py-2 text-sm font-medium text-[var(--background)] shadow-[0_15px_35px_rgba(0,0,0,0.18)] transition-transform hover:-translate-y-0.5"
              >
                <ShoppingBag className="h-4 w-4" />
                Join now
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
