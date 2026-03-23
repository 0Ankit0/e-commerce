'use client';

import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { CheckCircle2, Heart, Minus, Plus, Star, Truck } from 'lucide-react';
import { useCatalogProduct } from '@/hooks/use-catalog';
import {
  useAddToCart,
  useAddToWishlist,
  useApiErrorMessage,
  useRemoveFromWishlist,
  useWishlist,
} from '@/hooks/use-commerce';
import { SiteHeader } from '@/components/storefront/site-header';
import { SiteFooter } from '@/components/storefront/site-footer';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency } from '@/lib/commerce-format';
import { useAuthStore } from '@/store/auth-store';

export default function ProductDetailPage() {
  const params = useParams<{ productId: string }>();
  const productId = Array.isArray(params.productId) ? params.productId[0] : params.productId;
  const { isAuthenticated } = useAuthStore();
  const { getErrorMessage } = useApiErrorMessage();
  const { data: product, isLoading, isError, error, refetch } = useCatalogProduct(productId);
  const { data: wishlistData } = useWishlist(isAuthenticated);
  const addToCart = useAddToCart();
  const addToWishlist = useAddToWishlist();
  const removeFromWishlist = useRemoveFromWishlist();
  const [selectedVariantId, setSelectedVariantId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [feedback, setFeedback] = useState<string | null>(null);
  const heroImage = product?.images.find((image) => image.is_primary)?.url ?? product?.images[0]?.url;
  const variants = useMemo(() => product?.variants ?? [], [product]);
  const selectedVariant = useMemo(
    () => variants.find((variant) => variant.id === selectedVariantId) ?? variants[0] ?? null,
    [selectedVariantId, variants]
  );
  const isWishlisted = product ? (wishlistData?.items.some((item) => item.product_id === product.id) ?? false) : false;
  const canPurchase = Boolean(product && selectedVariant && variants.length > 0);

  useEffect(() => {
    setSelectedVariantId(variants.find((variant) => variant.is_default)?.id ?? variants[0]?.id ?? '');
  }, [product?.id, variants]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#fcf7f0]">
        <SiteHeader />
        <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]" role="status" aria-label="Loading product detail">
            <div className="aspect-[4/3] animate-pulse rounded-[38px] bg-white" />
            <div className="h-[560px] animate-pulse rounded-[38px] bg-white" />
          </div>
        </main>
        <SiteFooter />
      </div>
    );
  }

  if (isError) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    return (
      <div className="min-h-screen bg-[#fcf7f0]">
        <SiteHeader />
        <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
          <StorefrontState
            eyebrow={status === 404 ? 'Product not found' : 'Product unavailable'}
            title={status === 404 ? 'This product does not exist' : 'We could not load this product'}
            description={
              status === 404
                ? 'The requested product ID did not resolve to a live catalog item.'
                : 'The product detail request failed, so cart and wishlist actions stay disabled until a real product is available.'
            }
            actionLabel={status === 404 ? 'Back to shop' : 'Retry'}
            onAction={() => {
              if (status === 404) {
                window.location.assign('/shop');
                return;
              }
              void refetch();
            }}
          />
        </main>
        <SiteFooter />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-[#fcf7f0]">
        <SiteHeader />
        <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
          <StorefrontState
            eyebrow="Product not found"
            title="This product is unavailable"
            description="No live product data is available for this route."
            actionLabel="Back to shop"
            onAction={() => {
              window.location.assign('/shop');
            }}
          />
        </main>
        <SiteFooter />
      </div>
    );
  }

  const activeProduct = product;

  async function handleAddToCart() {
    if (!selectedVariant) {
      return;
    }
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    try {
      await addToCart.mutateAsync({
        variantId: selectedVariant.id,
        quantity,
      });
      setFeedback('Added to cart. You can review everything before checkout.');
    } catch (err) {
      setFeedback(getErrorMessage(err));
    }
  }

  async function handleToggleWishlist() {
    if (!canPurchase) {
      return;
    }
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    try {
      if (isWishlisted) {
        await removeFromWishlist.mutateAsync(activeProduct.id);
        setFeedback('Removed from your wishlist.');
        return;
      }
      await addToWishlist.mutateAsync(activeProduct.id);
      setFeedback('Saved to your wishlist.');
    } catch (err) {
      setFeedback(getErrorMessage(err));
    }
  }

  return (
    <div className="min-h-screen bg-[#fcf7f0]">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="overflow-hidden rounded-[38px] border border-[rgba(25,30,45,0.08)] bg-white shadow-[0_20px_60px_rgba(25,30,45,0.06)]">
            <div className="aspect-[4/3] bg-[radial-gradient(circle_at_top,#f4d2a8,transparent_60%),linear-gradient(135deg,#fbf6ef,#efe3d0)]">
              {heroImage ? (
                <img src={heroImage} alt={activeProduct.name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center font-[family:var(--font-display)] text-5xl text-[#6f6257]">
                  {activeProduct.name}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[38px] border border-[rgba(25,30,45,0.08)] bg-white p-8 shadow-[0_20px_60px_rgba(25,30,45,0.06)]">
            <p className="text-xs uppercase tracking-[0.28em] text-[#8b6e57]">
              {activeProduct.category?.name ?? 'Product detail'}
            </p>
            <h1 className="mt-4 font-[family:var(--font-display)] text-6xl leading-[0.92] text-[#1d1b18]">
              {activeProduct.name}
            </h1>
            <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-[#66584c]">
              <span className="inline-flex items-center gap-2 rounded-full bg-[#f7efe1] px-3 py-1">
                <Star className="h-4 w-4 fill-current text-[#c96d44]" />
                {activeProduct.avg_rating.toFixed(1)} rating
              </span>
              <span>{activeProduct.review_count} reviews</span>
              <span>{activeProduct.view_count} views</span>
            </div>
            <p className="mt-6 text-base leading-7 text-[#55483d]">
              {activeProduct.description || activeProduct.short_description}
            </p>

            <div className="mt-8 rounded-[28px] bg-[#fcf7f0] p-6">
              <p className="text-xs uppercase tracking-[0.24em] text-[#8b6e57]">Price</p>
              <p className="mt-2 text-4xl font-semibold text-[#1d1b18]">
                {formatCurrency(selectedVariant?.selling_price ?? activeProduct.min_selling_price)}
              </p>
              <div className="mt-5 grid gap-3">
                <div className="flex items-center gap-3 text-sm text-[#55483d]">
                  <CheckCircle2 className="h-4 w-4 text-[#1a6f4c]" />
                  {selectedVariant?.available_qty ? `${selectedVariant.available_qty} units ready for checkout` : 'Currently restocking'}
                </div>
                <div className="flex items-center gap-3 text-sm text-[#55483d]">
                  <Truck className="h-4 w-4 text-[#c96d44]" />
                  Shipping status and milestones are supported end-to-end in the backend.
                </div>
              </div>
            </div>

            <div className="mt-8 space-y-5">
              <div className="grid gap-4 md:grid-cols-[1fr_auto]">
                <label className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm text-[#55483d]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[#8b6e57]">Variant</span>
                  <select
                    value={selectedVariant?.id ?? ''}
                    onChange={(event) => setSelectedVariantId(event.target.value)}
                    className="w-full bg-transparent outline-none"
                    disabled={!canPurchase}
                  >
                    {variants.length > 0 ? (
                      variants.map((variant) => (
                        <option key={variant.id} value={variant.id}>
                          {variant.name} · {formatCurrency(variant.selling_price)}
                        </option>
                      ))
                    ) : (
                      <option value="">No variants available</option>
                    )}
                  </select>
                </label>
                <div className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm text-[#55483d]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[#8b6e57]">Quantity</span>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setQuantity((value) => Math.max(1, value - 1))}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[#1d1b18] disabled:opacity-60"
                      disabled={!canPurchase}
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <span className="min-w-8 text-center text-base font-semibold text-[#1d1b18]">{quantity}</span>
                    <button
                      type="button"
                      onClick={() => setQuantity((value) => Math.min(selectedVariant?.available_qty || 1, value + 1))}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[#1d1b18] disabled:opacity-60"
                      disabled={!canPurchase}
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
              {feedback ? (
                <div className="rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-[#fff7ed] px-4 py-3 text-sm text-[#7a573f]">
                  {feedback}
                </div>
              ) : null}
              {!canPurchase ? (
                <div className="rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-white px-4 py-3 text-sm text-[#7a573f]">
                  Real variant inventory is not available for this product yet, so cart and wishlist actions stay disabled.
                </div>
              ) : null}
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={addToCart.isPending || !selectedVariant?.available_qty || !canPurchase}
                className="inline-flex items-center justify-center rounded-full bg-[#1d1b18] px-6 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isAuthenticated ? 'Add to cart' : 'Sign in to buy'}
              </button>
              <button
                type="button"
                onClick={handleToggleWishlist}
                disabled={!canPurchase}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-[rgba(25,30,45,0.08)] px-6 py-3 text-sm font-semibold text-[#3e352d] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Heart className={`h-4 w-4 ${isWishlisted ? 'fill-current text-[#c96d44]' : ''}`} />
                {isWishlisted ? 'Saved to wishlist' : 'Save for later'}
              </button>
              <Link
                href="/shop"
                className="inline-flex items-center justify-center rounded-full border border-[rgba(25,30,45,0.08)] px-6 py-3 text-sm font-semibold text-[#3e352d]"
              >
                Back to shop
              </Link>
            </div>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {Object.entries(selectedVariant?.attributes ?? {}).length > 0
                ? Object.entries(selectedVariant?.attributes ?? {}).map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b6e57]">{key}</p>
                      <p className="mt-2 text-sm font-medium text-[#1d1b18]">{String(value)}</p>
                    </div>
                  ))
                : [
                    <div
                      key="purchase-ready"
                      className="rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b6e57]">Checkout</p>
                      <p className="mt-2 text-sm font-medium text-[#1d1b18]">Supports quote fingerprinting and order idempotency.</p>
                    </div>,
                    <div
                      key="returns"
                      className="rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b6e57]">Returns</p>
                      <p className="mt-2 text-sm font-medium text-[#1d1b18]">Customer returns and refund timelines are available after delivery.</p>
                    </div>,
                    <div
                      key="tracking"
                      className="rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b6e57]">Tracking</p>
                      <p className="mt-2 text-sm font-medium text-[#1d1b18]">Shipment events and current delivery location appear in your order detail screen.</p>
                    </div>,
                  ]}
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
