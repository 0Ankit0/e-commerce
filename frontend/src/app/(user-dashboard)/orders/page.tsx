'use client';

import Link from 'next/link';
import { ArrowRight, PackageSearch } from 'lucide-react';
import { useOrders } from '@/hooks/use-orders';
import { formatCurrency, formatDateLabel, titleCaseStatus } from '@/lib/commerce-format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function OrdersPage() {
  const { data, isLoading } = useOrders();
  const orders = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[#8b6e57]">Orders</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">Customer order timeline</h1>
      </div>

      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Recent orders</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-24 animate-pulse rounded-[24px] bg-[#f7efe1]" />
            ))
          ) : orders.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-[rgba(25,30,45,0.12)] bg-[#fcf7f0] p-8 text-center">
              <PackageSearch className="mx-auto h-8 w-8 text-[#c96d44]" />
              <p className="mt-3 text-sm text-[#6f6257]">No orders yet. Once you checkout, tracking and invoice details appear here.</p>
            </div>
          ) : (
            orders.map((order) => (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="flex flex-col gap-4 rounded-[24px] border border-[rgba(25,30,45,0.08)] p-5 transition-colors hover:bg-[#fcf7f0] md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">{order.order_number}</p>
                  <p className="text-sm font-medium text-[#1d1b18]">
                    {order.items.map((item) => item.product_name).join(', ')}
                  </p>
                  <p className="text-xs text-[#6f6257]">
                    Placed {formatDateLabel(order.created_at)} · {order.items.length} items · {titleCaseStatus(order.payment_status)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-[#f7efe1] px-3 py-1 text-xs font-medium text-[#6b5648]">
                    {titleCaseStatus(order.status)}
                  </span>
                  <span className="text-sm font-semibold text-[#1d1b18]">{formatCurrency(order.total)}</span>
                  <ArrowRight className="h-4 w-4 text-[#8b6e57]" />
                </div>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
