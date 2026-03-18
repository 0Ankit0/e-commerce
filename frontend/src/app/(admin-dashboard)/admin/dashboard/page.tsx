'use client';

import Link from 'next/link';
import { Activity, BadgeDollarSign, LayoutGrid, ShieldCheck, Store, Truck, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const stats = [
  { label: 'Orders under watch', value: '124', icon: Activity, color: 'bg-[#d9eafb] text-[#13324f]' },
  { label: 'Vendors in review', value: '08', icon: Store, color: 'bg-[#f7efe1] text-[#c96d44]' },
  { label: 'Open logistics exceptions', value: '11', icon: Truck, color: 'bg-[#f6ebc9] text-[#9a6a16]' },
  { label: 'Pending settlements', value: '$18.2k', icon: BadgeDollarSign, color: 'bg-[#dff1e8] text-[#123f35]' },
];

export default function AdminDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[#8b6e57]">Admin control</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">
          Monitor the entire marketplace from one operations command surface.
        </h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="rounded-[28px]">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[#8b6e57]">{stat.label}</p>
                  <p className="mt-1 text-2xl font-semibold text-[#1d1b18]">{stat.value}</p>
                </div>
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${stat.color}`}>
                  <stat.icon className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

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
                className="rounded-[24px] border border-[rgba(25,30,45,0.08)] p-5 transition-colors hover:bg-[#fcf7f0]"
              >
                <item.icon className="h-5 w-5 text-[#c96d44]" />
                <p className="mt-3 font-medium text-[#1d1b18]">{item.label}</p>
                <p className="mt-2 text-sm text-[#6f6257]">{item.desc}</p>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-[32px] bg-[#1d1b18] text-white">
          <CardHeader>
            <CardTitle>Security posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-[rgba(255,255,255,0.72)]">
            <div className="rounded-[22px] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.04)] p-4">
              Admin OTP readiness is surfaced directly in the backend and should be reviewed regularly.
            </div>
            <div className="rounded-[22px] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.04)] p-4">
              Role-aware navigation keeps privileged links out of sidebars for users who should not see them.
            </div>
            <Link
              href="/admin/security-review"
              className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#1d1b18]"
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
