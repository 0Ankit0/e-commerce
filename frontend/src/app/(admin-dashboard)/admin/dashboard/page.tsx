'use client';

import Link from 'next/link';
import { Activity, BadgeDollarSign, LayoutGrid, ShieldCheck, Truck, Users } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useOrders } from '@/hooks/use-orders';
import { useListUsers } from '@/hooks/use-users';
import { useVendorProducts } from '@/hooks/use-catalog';
import { useAdminOTPStatus } from '@/hooks/use-admin-security';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { getRuntimeErrorState, isPaginatedPayload } from '@/lib/runtime-route';

export default function AdminDashboardPage() {
  const [otpRecommendation, setOtpRecommendation] = useState<string | null>(null);
  const { data: ordersData, isLoading: loadingOrders, isError: ordersError, error: ordersErrorValue, refetch: refetchOrders } = useOrders();
  const { data: usersData, isLoading: loadingUsers, isError: usersError, error: usersErrorValue, refetch: refetchUsers } = useListUsers({ limit: 10 });
  const {
    data: vendorProductsData,
    isLoading: loadingVendorProducts,
    isError: vendorProductsError,
    error: vendorProductsErrorValue,
    refetch: refetchVendorProducts,
  } = useVendorProducts();
  const { data: adminOTPStatus } = useAdminOTPStatus();

  useEffect(() => {
    const message = sessionStorage.getItem('admin_otp_recommendation');
    setOtpRecommendation(message);
    if (message) {
      sessionStorage.removeItem('admin_otp_recommendation');
    }
  }, []);

  const otpReadiness = useMemo(() => {
    const items = adminOTPStatus?.items ?? [];
    const verified = items.filter((item) => item.otp_enabled && item.otp_verified).length;
    const pending = items.filter((item) => !item.otp_verified).length;
    return { total: items.length, verified, pending };
  }, [adminOTPStatus]);

  const hasPartialOrdersPayload = ordersData !== undefined && !isPaginatedPayload(ordersData);
  const hasPartialUsersPayload = usersData !== undefined && !isPaginatedPayload(usersData);
  const hasPartialVendorProductsPayload = vendorProductsData !== undefined && !isPaginatedPayload(vendorProductsData);

  const hasDataError =
    ordersError ||
    usersError ||
    vendorProductsError ||
    hasPartialOrdersPayload ||
    hasPartialUsersPayload ||
    hasPartialVendorProductsPayload;

  const stats = [
    { label: 'Orders under watch', value: String(ordersData?.total ?? 0), icon: Activity, color: 'bg-[var(--accent-soft)] text-[var(--accent)]' },
    { label: 'Users in scope', value: String(usersData?.total ?? 0), icon: Users, color: 'bg-[var(--warning-soft)] text-[var(--text-secondary)]' },
    {
      label: 'Vendor SKUs visible',
      value: String(vendorProductsData?.total ?? 0),
      icon: Truck,
      color: 'bg-[var(--warning-soft)] text-[var(--text-secondary)]',
    },
    { label: 'Pending settlements', value: '$18.2k', icon: BadgeDollarSign, color: 'bg-[var(--success-soft)] text-[var(--text-secondary)]' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Admin control</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[var(--text-primary)]">
          Monitor the entire marketplace from one operations command surface.
        </h1>
      </div>

      {loadingOrders || loadingUsers || loadingVendorProducts ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" role="status" aria-label="Loading admin metrics">
          {[1, 2, 3, 4].map((stat) => (
            <div key={stat} className="h-32 animate-pulse rounded-[28px] bg-white" />
          ))}
        </div>
      ) : hasDataError ? (
        <StorefrontState
          eyebrow="Admin runtime"
          title="Admin metrics unavailable"
          description="One or more admin metric feeds failed validation or request execution. This route does not fall back to placeholder totals."
          details={
            hasPartialOrdersPayload || hasPartialUsersPayload || hasPartialVendorProductsPayload
              ? 'Payload validation failed for /orders, /users, or /vendor/products (expected paginated shape).'
              : [ordersErrorValue, usersErrorValue, vendorProductsErrorValue]
                  .filter(Boolean)
                  .map((error) => getRuntimeErrorState(error, 'Admin metrics unavailable').details)
                  .join(' | ')
          }
          actionLabel="Retry"
          onAction={() => {
            void Promise.all([refetchOrders(), refetchUsers(), refetchVendorProducts()]);
          }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.label} className="rounded-[28px]">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--text-muted)]">{stat.label}</p>
                    <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">{stat.value}</p>
                  </div>
                  <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${stat.color}`}>
                    <stat.icon className="h-5 w-5" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <Card className="rounded-[32px]">
          <CardHeader>
            <CardTitle>Control areas</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {[
              { href: '/admin/orders', label: 'Orders', icon: Activity, desc: 'Investigate order progress and notes' },
              { href: '/admin/vendors', label: 'Vendors', icon: Users, desc: 'Review onboarding and payouts' },
              { href: '/admin/catalog', label: 'Catalog', icon: LayoutGrid, desc: 'Moderate storefront quality' },
              { href: '/admin/live-feed', label: 'Live Feed', icon: Truck, desc: 'Watch mixed commerce events' },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-[24px] border border-[var(--border-color)] p-5 transition-colors hover:bg-[var(--surface-muted)]"
              >
                <item.icon className="h-5 w-5 text-[var(--accent)]" />
                <p className="mt-3 font-medium text-[var(--text-primary)]">{item.label}</p>
                <p className="mt-2 text-sm text-[var(--text-muted)]">{item.desc}</p>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-[32px] bg-[var(--foreground)] text-[var(--background)]">
          <CardHeader>
            <CardTitle>Security posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm opacity-80">
            {otpRecommendation ? (
              <div className="rounded-[22px] border border-amber-200 bg-amber-50/90 p-4 text-amber-900">
                {otpRecommendation}
              </div>
            ) : null}
            <div className="rounded-[22px] border border-[rgba(128,128,128,0.2)] bg-[rgba(128,128,128,0.06)] p-4">
              Admin OTP readiness: {otpReadiness.verified}/{otpReadiness.total} verified. {otpReadiness.pending} account(s) need setup or verification.
            </div>
            <div className="rounded-[22px] border border-[rgba(128,128,128,0.2)] bg-[rgba(128,128,128,0.06)] p-4">
              Role-aware navigation keeps privileged links out of sidebars for users who should not see them.
            </div>
            <Link
              href="/admin/security-review"
              className="inline-flex items-center gap-2 rounded-full bg-[var(--background)] px-4 py-2 text-sm font-semibold text-[var(--foreground)]"
            >
              <ShieldCheck className="h-4 w-4" />
              Review security
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
