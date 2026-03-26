'use client';

import Link from 'next/link';
import { Bell, Heart, Package, Shield, ShoppingBag, Store } from 'lucide-react';
import { useCart, useWishlist } from '@/hooks/use-commerce';
import { useAuthStore } from '@/store/auth-store';
import { useNotifications } from '@/hooks/use-notifications';
import { useFeaturedProducts } from '@/hooks/use-catalog';
import { useOrders } from '@/hooks/use-orders';
import { formatCurrency, formatDateLabel, titleCaseStatus } from '@/lib/commerce-format';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PORTAL_DEFINITIONS, getUserPortals } from '@/lib/portal';

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: cart } = useCart();
  const { data: ordersData } = useOrders();
  const { data: wishlistData } = useWishlist();
  const { data: notifData, isLoading: loadingNotifs } = useNotifications({ limit: 5 });
  const {
    data: featuredProductsData,
    isLoading: featuredProductsLoading,
    isError: featuredProductsError,
    refetch: refetchFeaturedProducts,
  } = useFeaturedProducts(4);

  const recentNotifs = notifData?.items ?? [];
  const unreadCount = notifData?.unread_count ?? 0;
  const orders = ordersData?.items ?? [];
  const wishlist = wishlistData?.items ?? [];
  const activeOrders = orders.filter((order) => !['delivered', 'cancelled'].includes(order.status)).length;
  const cartUnits = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
  const latestOrder = orders[0];
  const featuredProducts = featuredProductsData?.items ?? [];
  const accessiblePortals = getUserPortals(user).filter((portal) => portal !== 'customer');

  const stats = [
    {
      name: 'Wishlist drops',
      value: unreadCount > 0 ? String(Math.min(unreadCount, 9)) : '0',
      icon: Heart,
      href: '/wishlist',
      color: 'text-[var(--accent)] bg-[var(--surface-muted)]',
    },
    {
      name: 'Orders in motion',
      value: String(activeOrders).padStart(2, '0'),
      icon: Package,
      href: '/orders',
      color: 'text-emerald-700 bg-[var(--success-soft)]',
    },
    {
      name: 'Security posture',
      value: user?.otp_enabled ? 'Enabled' : 'Review',
      icon: Shield,
      href: '/settings',
      color: user?.otp_enabled ? 'text-emerald-700 bg-[var(--success-soft)]' : 'text-amber-700 bg-[var(--warning-soft)]',
    },
    {
      name: 'Saved products',
      value: String(wishlist.length).padStart(2, '0'),
      icon: ShoppingBag,
      href: '/wishlist',
      color: 'text-[var(--accent)] bg-[var(--accent-soft)]',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Customer portal</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[var(--text-primary)]">
          A buying dashboard that feels like a lounge, not a spreadsheet.
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
          Welcome back
          {user?.first_name ? `, ${user.first_name}` : user?.username ? `, ${user.username}` : ''}. Track orders, catch price drops, and move from discovery to checkout without leaving your own space.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.name} href={stat.href}>
            <Card className="cursor-pointer rounded-[28px] border-[var(--border-color)] bg-white transition-shadow hover:shadow-[0_20px_45px_rgba(25,30,45,0.08)]">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--text-muted)]">{stat.name}</p>
                    <p className="mt-1 text-2xl font-bold text-[var(--text-primary)]">{stat.value}</p>
                  </div>
                  <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${stat.color}`}>
                    <stat.icon className="h-6 w-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="rounded-[32px] border-[var(--border-color)] bg-white">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Recent activity
            </CardTitle>
            <Link href="/notifications" className="text-sm text-[var(--accent)] hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {loadingNotifs ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded bg-gray-100" />
                ))}
              </div>
            ) : recentNotifs.length === 0 ? (
              <div className="py-8 text-center">
                <Bell className="mx-auto mb-2 h-8 w-8 text-[var(--text-muted)]" />
                <p className="text-sm text-[var(--text-muted)]">No notifications yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentNotifs.map((n) => (
                  <div
                    key={n.id}
                    className={`flex items-start gap-3 rounded-2xl p-3 ${n.is_read ? 'bg-[var(--surface-muted)]' : 'bg-[var(--accent-soft)]'}`}
                  >
                    <div
                      className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${
                        n.is_read ? 'bg-[var(--text-muted)]' : 'bg-[var(--accent)]'
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-[var(--text-primary)]">{n.title}</p>
                      <p className="truncate text-xs text-[var(--text-secondary)]">{n.body}</p>
                    </div>
                    <span className="flex-shrink-0 text-xs text-[var(--text-muted)]">
                      {new Date(n.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-[var(--border-color)] bg-white">
          <CardHeader>
            <CardTitle>Featured for you</CardTitle>
          </CardHeader>
          <CardContent>
            {latestOrder ? (
              <div className="rounded-[26px] bg-[var(--surface-muted)] p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Latest order</p>
                <p className="mt-2 font-[family:var(--font-display)] text-3xl text-[var(--text-primary)]">{latestOrder.order_number}</p>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  {titleCaseStatus(latestOrder.status)} · {formatDateLabel(latestOrder.created_at)} · {formatCurrency(latestOrder.total)}
                </p>
                <div className="mt-4 grid gap-2">
                  {latestOrder.shipments.slice(0, 2).map((shipment) => (
                    <div key={shipment.id} className="rounded-2xl border border-[var(--border-color)] bg-white px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">{shipment.awb}</p>
                      <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">{titleCaseStatus(shipment.status)}</p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">{shipment.current_location || 'Awaiting shipment update'}</p>
                    </div>
                  ))}
                </div>
                <Link href={`/orders/${latestOrder.id}`} className="mt-4 inline-flex text-sm font-semibold text-[var(--accent)] hover:underline">
                  Open order detail
                </Link>
              </div>
            ) : featuredProductsLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="h-20 animate-pulse rounded-2xl bg-[var(--surface-muted)]" />
                ))}
              </div>
            ) : featuredProductsError ? (
              <StorefrontState
                eyebrow="Featured for you"
                title="Featured products unavailable"
                description="The dashboard could not load live featured products right now."
                actionLabel="Retry"
                onAction={() => {
                  void refetchFeaturedProducts();
                }}
              />
            ) : featuredProducts.length > 0 ? (
              <div className="space-y-3">
                {featuredProducts.map((product) => (
                  <Link
                    key={product.id}
                    href={`/products/${product.id}`}
                    className="flex items-center justify-between rounded-2xl border border-[var(--border-color)] p-4 transition-colors hover:bg-[var(--background)]"
                  >
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">
                        {product.category?.name ?? 'Product'}
                      </p>
                      <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">{product.name}</p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {product.min_selling_price ? formatCurrency(product.min_selling_price) : 'Quote'}
                      </p>
                    </div>
                    <Store className="h-4 w-4 text-[var(--accent)]" />
                  </Link>
                ))}
              </div>
            ) : (
              <StorefrontState
                eyebrow="Featured for you"
                title="No featured products yet"
                description="Featured catalog recommendations will appear here after vendors publish inventory."
              />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <Card className="rounded-[32px] border-[var(--border-color)] bg-white">
          <CardHeader>
            <CardTitle>Cart pulse</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-[26px] bg-[var(--surface-muted)] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">Ready to checkout</p>
              <p className="mt-3 font-[family:var(--font-display)] text-5xl text-[var(--text-primary)]">{cartUnits}</p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                {cartUnits === 0 ? 'Your cart is empty right now.' : `${cart?.items.length ?? 0} line items waiting for a shipping quote.`}
              </p>
              <Link href="/cart" className="mt-5 inline-flex rounded-full bg-[var(--foreground)] px-4 py-2 text-sm font-semibold text-[var(--background)]">
                Review cart
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-[var(--border-color)] bg-white">
          <CardHeader>
            <CardTitle>Pickup where you left off</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <Link href="/shop" className="rounded-[24px] border border-[var(--border-color)] p-5 transition-colors hover:bg-[var(--background)]">
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Browse</p>
              <p className="mt-2 text-lg font-medium text-[var(--text-primary)]">Discover something new</p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">Jump back into the live catalog with search, category, and brand filters.</p>
            </Link>
            <Link href="/wishlist" className="rounded-[24px] border border-[var(--border-color)] p-5 transition-colors hover:bg-[var(--background)]">
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Wishlist</p>
              <p className="mt-2 text-lg font-medium text-[var(--text-primary)]">Share saved picks</p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">Create public share links and keep an eye on live price-drop alerts.</p>
            </Link>
          </CardContent>
        </Card>
      </div>

      {accessiblePortals.length > 0 ? (
        <Card className="rounded-[32px] border-[var(--border-color)] bg-[var(--foreground)] text-white">
          <CardContent className="pt-6">
            <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
              <div>
                <p className="text-xs uppercase tracking-[0.26em] text-[rgba(255,255,255,0.48)]">
                  Multi-role access
                </p>
                <h2 className="mt-3 font-[family:var(--font-display)] text-4xl">
                  You have more than one portal available.
                </h2>
                <p className="mt-3 text-sm text-[rgba(255,255,255,0.7)]">
                  Switch between storefront buying, commerce operations, and oversight from the same account without exposing links you cannot use.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {accessiblePortals.map((portal) => (
                  <Link
                    key={portal}
                    href={PORTAL_DEFINITIONS[portal].home}
                    className="rounded-[26px] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.04)] p-5 transition-transform hover:-translate-y-0.5"
                  >
                    <p className="font-medium">{PORTAL_DEFINITIONS[portal].label}</p>
                    <p className="mt-2 text-sm text-[rgba(255,255,255,0.68)]">
                      {PORTAL_DEFINITIONS[portal].description}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
