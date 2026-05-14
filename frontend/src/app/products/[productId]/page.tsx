'use client';

import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { CheckCircle2, Heart, Minus, Plus, Star, Truck } from 'lucide-react';
import { useCatalogProduct, useCatalogRecommendations } from '@/hooks/use-catalog';
import {
  useAddToCart,
  useAddToWishlist,
  useApiErrorMessage,
  useRemoveFromWishlist,
  useWishlist,
} from '@/hooks/use-commerce';
import { SiteHeader } from '@/components/storefront/site-header';
import { SiteFooter } from '@/components/storefront/site-footer';
import { ProductCard } from '@/components/storefront/product-card';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency } from '@/lib/commerce-format';
import { useAuthStore } from '@/store/auth-store';

export default function ProductDetailPage() {
  const params = useParams<{ productId: string }>();
  const productId = Array.isArray(params.productId) ? params.productId[0] : params.productId;
  const { isAuthenticated } = useAuthStore();
  const { getErrorMessage } = useApiErrorMessage();
  const { data: product, isLoading, isError, error, refetch } = useCatalogProduct(productId);
  const {
    data: recommendationsData,
    isLoading: recommendationsLoading,
    isError: recommendationsError,
    refetch: refetchRecommendations,
  } = useCatalogRecommendations('product_detail', {
    productId,
    limit: 4,
    enabled: Boolean(productId),
  });
  const { data: wishlistData } = useWishlist(isAuthenticated);
  const addToCart = useAddToCart();
  const addToWishlist = useAddToWishlist();
  const removeFromWishlist = useRemoveFromWishlist();
  const [selectedVariantId, setSelectedVariantId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [feedback, setFeedback] = useState<string | null>(null);
  const heroImage = product?.images.find((image) => image.is_primary)?.url ?? product?.images[0]?.url;
  const recommendedProducts = recommendationsData?.items ?? [];
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
      <div className="min-h-screen bg-[var(--background)]">
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
      <div className="min-h-screen bg-[var(--background)]">
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
      <div className="min-h-screen bg-[var(--background)]">
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
    <div className="min-h-screen bg-[var(--background)]">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="overflow-hidden rounded-[38px] border border-[var(--border-color)] bg-white shadow-[0_20px_60px_rgba(25,30,45,0.06)]">
            <div className="aspect-[4/3] bg-[radial-gradient(circle_at_top,#f4d2a8,transparent_60%),linear-gradient(135deg,#fbf6ef,#efe3d0)]">
              {heroImage ? (
                <img src={heroImage} alt={activeProduct.name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center font-[family:var(--font-display)] text-5xl text-[var(--text-secondary)]">
                  {activeProduct.name}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[38px] border border-[var(--border-color)] bg-white p-8 shadow-[0_20px_60px_rgba(25,30,45,0.06)]">
            <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">
              {activeProduct.category?.name ?? 'Product detail'}
            </p>
            <h1 className="mt-4 font-[family:var(--font-display)] text-6xl leading-[0.92] text-[var(--text-primary)]">
              {activeProduct.name}
            </h1>
            <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-[var(--text-secondary)]">
              <span className="inline-flex items-center gap-2 rounded-full bg-[var(--surface-muted)] px-3 py-1">
                <Star className="h-4 w-4 fill-current text-[var(--accent)]" />
                {activeProduct.avg_rating.toFixed(1)} rating
              </span>
              <span>{activeProduct.review_count} reviews</span>
              <span>{activeProduct.view_count} views</span>
            </div>
            <p className="mt-6 text-base leading-7 text-[var(--text-secondary)]">
              {activeProduct.description || activeProduct.short_description}
            </p>

            <div className="mt-8 rounded-[28px] bg-[var(--background)] p-6">
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Price</p>
              <p className="mt-2 text-4xl font-semibold text-[var(--text-primary)]">
                {formatCurrency(selectedVariant?.selling_price ?? activeProduct.min_selling_price)}
              </p>
              <div className="mt-5 grid gap-3">
                <div className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                  <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                  {selectedVariant?.available_qty ? `${selectedVariant.available_qty} units ready for checkout` : 'Currently restocking'}
                </div>
                <div className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                  <Truck className="h-4 w-4 text-[var(--accent)]" />
                  Shipping status and milestones are supported end-to-end in the backend.
                </div>
              </div>
            </div>

            <div className="mt-8 space-y-5">
              <div className="grid gap-4 md:grid-cols-[1fr_auto]">
                <label className="rounded-[24px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">Variant</span>
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
                <div className="rounded-[24px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                  <span className="mb-2 block text-[11px] uppercase tracking-[0.22em] text-[var(--text-muted)]">Quantity</span>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setQuantity((value) => Math.max(1, value - 1))}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[var(--text-primary)] disabled:opacity-60"
                      disabled={!canPurchase}
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <span className="min-w-8 text-center text-base font-semibold text-[var(--text-primary)]">{quantity}</span>
                    <button
                      type="button"
                      onClick={() => setQuantity((value) => Math.min(selectedVariant?.available_qty || 1, value + 1))}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[var(--text-primary)] disabled:opacity-60"
                      disabled={!canPurchase}
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
              {feedback ? (
                <div className="rounded-[22px] border border-[var(--border-color)] bg-[var(--warning-soft)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                  {feedback}
                </div>
              ) : null}
              {!canPurchase ? (
                <div className="rounded-[22px] border border-[var(--border-color)] bg-white px-4 py-3 text-sm text-[var(--text-secondary)]">
                  Real variant inventory is not available for this product yet, so cart and wishlist actions stay disabled.
                </div>
              ) : null}
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={addToCart.isPending || !selectedVariant?.available_qty || !canPurchase}
                className="inline-flex items-center justify-center rounded-full bg-[var(--foreground)] px-6 py-3 text-sm font-semibold text-[var(--background)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isAuthenticated ? 'Add to cart' : 'Sign in to buy'}
              </button>
              <button
                type="button"
                onClick={handleToggleWishlist}
                disabled={!canPurchase}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-[var(--border-color)] px-6 py-3 text-sm font-semibold text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Heart className={`h-4 w-4 ${isWishlisted ? 'fill-current text-[var(--accent)]' : ''}`} />
                {isWishlisted ? 'Saved to wishlist' : 'Save for later'}
              </button>
              <Link
                href="/shop"
                className="inline-flex items-center justify-center rounded-full border border-[var(--border-color)] px-6 py-3 text-sm font-semibold text-[var(--text-secondary)]"
              >
                Back to shop
              </Link>
            </div>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {Object.entries(selectedVariant?.attributes ?? {}).length > 0
                ? Object.entries(selectedVariant?.attributes ?? {}).map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded-[22px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--text-muted)]">{key}</p>
                      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{String(value)}</p>
                    </div>
                  ))
                : [
                    <div
                      key="purchase-ready"
                      className="rounded-[22px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--text-muted)]">Checkout</p>
                      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">Supports quote fingerprinting and order idempotency.</p>
                    </div>,
                    <div
                      key="returns"
                      className="rounded-[22px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--text-muted)]">Returns</p>
                      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">Customer returns and refund timelines are available after delivery.</p>
                    </div>,
                    <div
                      key="tracking"
                      className="rounded-[22px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-4"
                    >
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--text-muted)]">Tracking</p>
                      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">Shipment events and current delivery location appear in your order detail screen.</p>
                    </div>,
                  ]}
            </div>
          </div>
        </div>

        <section className="mt-12">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Recommended next</p>
              <h2 className="mt-2 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">
                Similar products shaped by live shopping signals.
              </h2>
            </div>
          </div>
          {recommendationsLoading ? (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {[1, 2, 3, 4].map((item) => (
                <div key={item} className="h-[360px] animate-pulse rounded-[28px] bg-white" />
              ))}
            </div>
          ) : recommendationsError ? (
            <StorefrontState
              eyebrow="Recommendations"
              title="Related products unavailable"
              description="The product detail page could not load recommendation results right now."
              actionLabel="Retry"
              onAction={() => {
                void refetchRecommendations();
              }}
            />
          ) : recommendedProducts.length === 0 ? (
            <StorefrontState
              eyebrow="Recommendations"
              title="No related products yet"
              description="Recommendation results will appear here after the catalog collects more product and shopping signals."
            />
          ) : (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {recommendedProducts.map((recommendedProduct) => (
                <ProductCard key={recommendedProduct.id} product={recommendedProduct} />
              ))}
            </div>
          )}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
