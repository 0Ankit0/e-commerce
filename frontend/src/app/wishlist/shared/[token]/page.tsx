'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { SiteFooter } from '@/components/storefront/site-footer';
import { SiteHeader } from '@/components/storefront/site-header';
import { useSharedWishlist } from '@/hooks/use-commerce';
import { formatCurrency } from '@/lib/commerce-format';

export default function SharedWishlistPage() {
  const params = useParams<{ token: string }>();
  const token = Array.isArray(params.token) ? params.token[0] : params.token;
  const { data, isLoading } = useSharedWishlist(token);

  return (
    <div className="min-h-screen bg-[#fcf7f0]">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="rounded-[36px] border border-[rgba(25,30,45,0.08)] bg-white p-8 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
          {isLoading ? (
            <p className="text-sm text-[#6f6257]">Loading shared wishlist...</p>
          ) : data ? (
            <>
              <p className="text-xs uppercase tracking-[0.28em] text-[#8b6e57]">Shared wishlist</p>
              <h1 className="mt-4 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">
                {data.share_link.title || `${data.owner.username}'s saved picks`}
              </h1>
              <p className="mt-3 max-w-2xl text-sm text-[#6f6257]">
                Public wishlist sharing is powered by the backend share-link flow. Browse the collection and open any product to continue shopping.
              </p>
              <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data.items.map((item) => (
                  <Link
                    key={item.product_id}
                    href={`/products/${item.product_id}`}
                    className="rounded-[28px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] p-5 transition-transform hover:-translate-y-1"
                  >
                    <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">{item.variant_name || 'Shared pick'}</p>
                    <p className="mt-2 text-lg font-medium text-[#1d1b18]">{item.name}</p>
                    <p className="mt-2 text-sm text-[#6f6257]">{item.slug.replace(/-/g, ' ')}</p>
                    <p className="mt-4 text-sm font-semibold text-[#1d1b18]">{formatCurrency(item.price)}</p>
                  </Link>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center">
              <p className="text-xs uppercase tracking-[0.28em] text-[#8b6e57]">Not available</p>
              <h1 className="mt-4 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">This share link is no longer active.</h1>
              <Link href="/shop" className="mt-6 inline-flex rounded-full bg-[#1d1b18] px-5 py-3 text-sm font-semibold text-white">
                Explore the storefront
              </Link>
            </div>
          )}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
