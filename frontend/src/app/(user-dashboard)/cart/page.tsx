'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Minus, Plus, Trash2 } from 'lucide-react';
import {
  useApiErrorMessage,
  useApplyCoupon,
  useCart,
  useRemoveCartItem,
  useUpdateCartItem,
} from '@/hooks/use-commerce';
import { formatCurrency } from '@/lib/commerce-format';

export default function CartPage() {
  const [coupon, setCoupon] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const { getErrorMessage } = useApiErrorMessage();
  const { data: cart, isLoading } = useCart();
  const updateItem = useUpdateCartItem();
  const removeItem = useRemoveCartItem();
  const applyCoupon = useApplyCoupon();

  async function handleApplyCoupon() {
    if (!coupon.trim()) {
      return;
    }

    try {
      await applyCoupon.mutateAsync(coupon.trim());
      setMessage(`Coupon ${coupon.trim().toUpperCase()} applied to your cart.`);
      setCoupon('');
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[#8b6e57]">Cart</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">Everything queued for checkout.</h1>
      </div>

      {message ? (
        <div className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fff7ed] px-5 py-4 text-sm text-[#7a573f]">
          {message}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="space-y-4">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-28 animate-pulse rounded-[28px] bg-[#f7efe1]" />
            ))
          ) : cart?.items.length ? (
            cart.items.map((item) => (
              <div
                key={item.id}
                className="rounded-[28px] border border-[rgba(25,30,45,0.08)] bg-white p-5 shadow-[0_16px_45px_rgba(25,30,45,0.05)]"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">{item.variant_name || item.sku}</p>
                    <p className="mt-2 text-lg font-medium text-[#1d1b18]">{item.product_name}</p>
                    <p className="mt-1 text-sm text-[#6f6257]">
                      {formatCurrency(item.unit_price)} each · {item.available_qty} available
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 rounded-full bg-[#fcf7f0] px-3 py-2">
                      <button
                        type="button"
                        onClick={() => updateItem.mutate({ itemId: item.id, quantity: Math.max(1, item.quantity - 1) })}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white text-[#1d1b18]"
                      >
                        <Minus className="h-4 w-4" />
                      </button>
                      <span className="min-w-8 text-center text-sm font-semibold text-[#1d1b18]">{item.quantity}</span>
                      <button
                        type="button"
                        onClick={() =>
                          updateItem.mutate({
                            itemId: item.id,
                            quantity: Math.min(item.available_qty || item.quantity + 1, item.quantity + 1),
                          })
                        }
                        className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white text-[#1d1b18]"
                      >
                        <Plus className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="min-w-24 text-right text-lg font-semibold text-[#1d1b18]">{formatCurrency(item.line_total)}</p>
                    <button
                      type="button"
                      onClick={() => removeItem.mutate(item.id)}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[rgba(25,30,45,0.08)] text-[#8c3d3d]"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="rounded-[32px] border border-dashed border-[rgba(25,30,45,0.12)] bg-white p-10 text-center">
              <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Cart empty</p>
              <h2 className="mt-3 font-[family:var(--font-display)] text-4xl text-[#1d1b18]">Nothing here yet.</h2>
              <p className="mt-3 text-sm text-[#6f6257]">Add a product from the storefront and come back here for quote-ready checkout.</p>
              <Link href="/shop" className="mt-5 inline-flex rounded-full bg-[#1d1b18] px-5 py-3 text-sm font-semibold text-white">
                Browse the catalog
              </Link>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <p className="text-xs uppercase tracking-[0.24em] text-[#8b6e57]">Order summary</p>
            <div className="mt-6 space-y-3 text-sm text-[#55483d]">
              <div className="flex items-center justify-between">
                <span>Subtotal</span>
                <span className="font-medium text-[#1d1b18]">{formatCurrency(cart?.subtotal ?? 0)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Discount</span>
                <span className="font-medium text-[#1d1b18]">- {formatCurrency(cart?.discount ?? 0)}</span>
              </div>
              <div className="flex items-center justify-between border-t border-[rgba(25,30,45,0.08)] pt-3 text-base">
                <span className="font-medium text-[#1d1b18]">Cart total</span>
                <span className="font-semibold text-[#1d1b18]">{formatCurrency(cart?.total ?? 0)}</span>
              </div>
            </div>
            {cart?.coupon_code ? (
              <div className="mt-4 rounded-[20px] bg-[#f7efe1] px-4 py-3 text-sm text-[#6b5648]">
                Coupon applied: <span className="font-semibold">{cart.coupon_code}</span>
              </div>
            ) : null}
            <div className="mt-5 flex gap-2">
              <input
                value={coupon}
                onChange={(event) => setCoupon(event.target.value)}
                placeholder="Coupon code"
                className="flex-1 rounded-full border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm outline-none"
              />
              <button
                type="button"
                onClick={handleApplyCoupon}
                className="rounded-full border border-[rgba(25,30,45,0.08)] px-4 py-3 text-sm font-semibold text-[#3e352d]"
              >
                Apply
              </button>
            </div>
            <Link
              href="/checkout"
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#1d1b18] px-5 py-3 text-sm font-semibold text-white"
            >
              Continue to checkout
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-[#1d1b18] p-6 text-white">
            <p className="text-xs uppercase tracking-[0.24em] text-[rgba(255,255,255,0.48)]">Built into backend</p>
            <p className="mt-4 font-[family:var(--font-display)] text-3xl">Quotes, tax rules, serviceability, and idempotent checkout.</p>
            <p className="mt-3 text-sm text-[rgba(255,255,255,0.72)]">
              Your final shipping and tax values are recalculated at checkout against the selected delivery address.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
