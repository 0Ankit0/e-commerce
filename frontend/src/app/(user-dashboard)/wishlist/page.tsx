'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Check, Copy, Link2, Trash2 } from 'lucide-react';
import {
  useCreateWishlistShareLink,
  useRevokeWishlistShareLink,
  useWishlist,
  useWishlistShareLinks,
} from '@/hooks/use-commerce';
import { formatCurrency, formatDateLabel } from '@/lib/commerce-format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function WishlistPage() {
  const [shareTitle, setShareTitle] = useState('');
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const { data: wishlistData } = useWishlist();
  const { data: shareLinksData } = useWishlistShareLinks();
  const createShareLink = useCreateWishlistShareLink();
  const revokeShareLink = useRevokeWishlistShareLink();
  const items = wishlistData?.items ?? [];
  const shareLinks = shareLinksData?.items ?? [];

  async function handleCopy(token: string) {
    const shareUrl = `${window.location.origin}/wishlist/shared/${token}`;
    await navigator.clipboard.writeText(shareUrl);
    setCopiedToken(token);
    window.setTimeout(() => setCopiedToken(null), 1800);
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Wishlist</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[var(--text-primary)]">Saved pieces and shareable picks</h1>
      </div>

      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Saved products</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {items.map((product) => (
            <Link
              key={product.id}
              href={`/products/${product.product_id}`}
              className="rounded-[24px] border border-[var(--border-color)] p-5 transition-colors hover:bg-[var(--background)]"
            >
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">{product.variant_name || 'Saved item'}</p>
              <p className="mt-2 font-medium text-[var(--text-primary)]">{product.name}</p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{product.slug.replace(/-/g, ' ')}</p>
              <p className="mt-4 text-sm font-semibold text-[var(--text-primary)]">{formatCurrency(product.price)}</p>
            </Link>
          ))}
          {items.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-[rgba(25,30,45,0.12)] bg-[var(--background)] p-6 text-sm text-[var(--text-secondary)]">
              Your wishlist is still empty. Save items from the product detail page and generate share links here.
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Share links</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            className="flex flex-col gap-3 rounded-[24px] border border-[var(--border-color)] bg-[var(--background)] p-4 md:flex-row"
            onSubmit={async (event) => {
              event.preventDefault();
              await createShareLink.mutateAsync(shareTitle);
              setShareTitle('');
            }}
          >
            <input
              value={shareTitle}
              onChange={(event) => setShareTitle(event.target.value)}
              placeholder="Share collection title"
              className="flex-1 rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
            />
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-[var(--foreground)] px-5 py-3 text-sm font-semibold text-[var(--background)]"
            >
              <Link2 className="h-4 w-4" />
              Create share link
            </button>
          </form>
          <div className="space-y-3">
            {shareLinks.map((link) => {
              const shareUrl = `/wishlist/shared/${link.token}`;
              return (
                <div
                  key={link.id}
                  className="flex flex-col gap-4 rounded-[24px] border border-[var(--border-color)] p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">{link.title || 'Untitled wishlist collection'}</p>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Created {formatDateLabel(link.created_at)} · {link.is_active ? 'Active' : 'Revoked'}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">{shareUrl}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopy(link.token)}
                      className="inline-flex items-center gap-2 rounded-full border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)]"
                    >
                      {copiedToken === link.token ? <Check className="h-4 w-4 text-emerald-700" /> : <Copy className="h-4 w-4" />}
                      {copiedToken === link.token ? 'Copied' : 'Copy link'}
                    </button>
                    <button
                      type="button"
                      onClick={() => revokeShareLink.mutate(link.id)}
                      className="inline-flex items-center gap-2 rounded-full border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                      Revoke
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
