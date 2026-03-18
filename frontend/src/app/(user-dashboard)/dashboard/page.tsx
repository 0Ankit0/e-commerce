'use client';

import Link from 'next/link';
import { Bell, Heart, Package, Shield, ShoppingBag, Store } from 'lucide-react';
import { useCart, useWishlist } from '@/hooks/use-commerce';
import { useAuthStore } from '@/store/auth-store';
import { useNotifications } from '@/hooks/use-notifications';
import { useFeaturedProducts } from '@/hooks/use-catalog';
import { useOrders } from '@/hooks/use-orders';
import { formatCurrency, formatDateLabel, titleCaseStatus } from '@/lib/commerce-format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PORTAL_DEFINITIONS, getUserPortals } from '@/lib/portal';
import { mockProducts } from '@/lib/mock-commerce';

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: cart } = useCart();
  const { data: ordersData } = useOrders();
  const { data: wishlistData } = useWishlist();
  const { data: notifData, isLoading: loadingNotifs } = useNotifications({ limit: 5 });
  const { data: featuredProductsData } = useFeaturedProducts(4);

  const recentNotifs = notifData?.items ?? [];
  const unreadCount = notifData?.unread_count ?? 0;
  const orders = ordersData?.items ?? [];
  const wishlist = wishlistData?.items ?? [];
  const activeOrders = orders.filter((order) => !['delivered', 'cancelled'].includes(order.status)).length;
  const cartUnits = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
  const latestOrder = orders[0];
  const featuredProducts = featuredProductsData?.items?.length ? featuredProductsData.items : mockProducts.slice(0, 4);
  const accessiblePortals = getUserPortals(user).filter((portal) => portal !== 'customer');

  const stats = [
    {
      name: 'Wishlist drops',
      value: unreadCount > 0 ? String(Math.min(unreadCount, 9)) : '0',
      icon: Heart,
      href: '/wishlist',
      color: 'text-[#c96d44] bg-[#f7efe1]',
    },
    {
      name: 'Orders in motion',
      value: String(activeOrders).padStart(2, '0'),
      icon: Package,
      href: '/orders',
      color: 'text-[#123f35] bg-[#dff1e8]',
    },
    {
      name: 'Security posture',
      value: user?.otp_enabled ? 'Enabled' : 'Review',
      icon: Shield,
      href: '/settings',
      color: user?.otp_enabled ? 'text-[#123f35] bg-[#dff1e8]' : 'text-[#9a6a16] bg-[#f6ebc9]',
    },
    {
      name: 'Saved products',
      value: String(wishlist.length).padStart(2, '0'),
      icon: ShoppingBag,
      href: '/wishlist',
      color: 'text-[#7c2f74] bg-[#f0d6ef]',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[#8b6e57]">Customer portal</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">
          A buying dashboard that feels like a lounge, not a spreadsheet.
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[#66584c]">
          Welcome back
          {user?.first_name ? `, ${user.first_name}` : user?.username ? `, ${user.username}` : ''}. Track orders, catch price drops, and move from discovery to checkout without leaving your own space.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.name} href={stat.href}>
            <Card className="cursor-pointer rounded-[28px] border-[rgba(25,30,45,0.08)] bg-white transition-shadow hover:shadow-[0_20px_45px_rgba(25,30,45,0.08)]">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[#8b6e57]">{stat.name}</p>
                    <p className="mt-1 text-2xl font-bold text-[#1d1b18]">{stat.value}</p>
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
        <Card className="rounded-[32px] border-[rgba(25,30,45,0.08)] bg-white">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Recent activity
            </CardTitle>
            <Link href="/notifications" className="text-sm text-[#6f4f3c] hover:underline">
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
                <Bell className="mx-auto mb-2 h-8 w-8 text-[#d0b59b]" />
                <p className="text-sm text-[#7d6758]">No notifications yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentNotifs.map((n) => (
                  <div
                    key={n.id}
                    className={`flex items-start gap-3 rounded-2xl p-3 ${n.is_read ? 'bg-[#fcf7f0]' : 'bg-[#f7efe1]'}`}
                  >
                    <div
                      className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${
                        n.is_read ? 'bg-[#d0b59b]' : 'bg-[#c96d44]'
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-[#1d1b18]">{n.title}</p>
                      <p className="truncate text-xs text-[#6f6257]">{n.body}</p>
                    </div>
                    <span className="flex-shrink-0 text-xs text-[#8b6e57]">
                      {new Date(n.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-[rgba(25,30,45,0.08)] bg-white">
          <CardHeader>
            <CardTitle>Featured for you</CardTitle>
          </CardHeader>
          <CardContent>
            {latestOrder ? (
              <div className="rounded-[26px] bg-[#fcf7f0] p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">Latest order</p>
                <p className="mt-2 font-[family:var(--font-display)] text-3xl text-[#1d1b18]">{latestOrder.order_number}</p>
                <p className="mt-2 text-sm text-[#6f6257]">
                  {titleCaseStatus(latestOrder.status)} · {formatDateLabel(latestOrder.created_at)} · {formatCurrency(latestOrder.total)}
                </p>
                <div className="mt-4 grid gap-2">
                  {latestOrder.shipments.slice(0, 2).map((shipment) => (
                    <div key={shipment.id} className="rounded-2xl border border-[rgba(25,30,45,0.08)] bg-white px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">{shipment.awb}</p>
                      <p className="mt-1 text-sm font-medium text-[#1d1b18]">{titleCaseStatus(shipment.status)}</p>
                      <p className="mt-1 text-xs text-[#6f6257]">{shipment.current_location || 'Awaiting shipment update'}</p>
                    </div>
                  ))}
                </div>
                <Link href={`/orders/${latestOrder.id}`} className="mt-4 inline-flex text-sm font-semibold text-[#6f4f3c] hover:underline">
                  Open order detail
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {featuredProducts.map((product) => (
                  <Link
                    key={product.id}
                    href={`/products/${product.id}`}
                    className="flex items-center justify-between rounded-2xl border border-[rgba(25,30,45,0.08)] p-4 transition-colors hover:bg-[#fcf7f0]"
                  >
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">
                        {product.category?.name ?? 'Product'}
                      </p>
                      <p className="mt-1 text-sm font-medium text-[#1d1b18]">{product.name}</p>
                      <p className="mt-1 text-xs text-[#6f6257]">
                        {product.min_selling_price ? formatCurrency(product.min_selling_price) : 'Quote'}
                      </p>
                    </div>
                    <Store className="h-4 w-4 text-[#c96d44]" />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <Card className="rounded-[32px] border-[rgba(25,30,45,0.08)] bg-white">
          <CardHeader>
            <CardTitle>Cart pulse</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-[26px] bg-[#fcf7f0] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Ready to checkout</p>
              <p className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">{cartUnits}</p>
              <p className="mt-2 text-sm text-[#6f6257]">
                {cartUnits === 0 ? 'Your cart is empty right now.' : `${cart?.items.length ?? 0} line items waiting for a shipping quote.`}
              </p>
              <Link href="/cart" className="mt-5 inline-flex rounded-full bg-[#1d1b18] px-4 py-2 text-sm font-semibold text-white">
                Review cart
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-[rgba(25,30,45,0.08)] bg-white">
          <CardHeader>
            <CardTitle>Pickup where you left off</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <Link href="/shop" className="rounded-[24px] border border-[rgba(25,30,45,0.08)] p-5 transition-colors hover:bg-[#fcf7f0]">
              <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">Browse</p>
              <p className="mt-2 text-lg font-medium text-[#1d1b18]">Discover something new</p>
              <p className="mt-2 text-sm text-[#6f6257]">Jump back into the live catalog with search, category, and brand filters.</p>
            </Link>
            <Link href="/wishlist" className="rounded-[24px] border border-[rgba(25,30,45,0.08)] p-5 transition-colors hover:bg-[#fcf7f0]">
              <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">Wishlist</p>
              <p className="mt-2 text-lg font-medium text-[#1d1b18]">Share saved picks</p>
              <p className="mt-2 text-sm text-[#6f6257]">Create public share links and keep an eye on future price-drop alerts.</p>
            </Link>
          </CardContent>
        </Card>
      </div>

      {accessiblePortals.length > 0 ? (
        <Card className="rounded-[32px] border-[rgba(25,30,45,0.08)] bg-[#1d1b18] text-white">
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
