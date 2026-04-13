'use client';

import { useMemo, useState } from 'react';
import { PackageCheck, PackageOpen, Truck, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency, formatDateLabel, titleCaseStatus } from '@/lib/commerce-format';
import { useRejectVendorOrder, useUpdateVendorOrderStatus, useVendorOrders } from '@/hooks/use-orders';

const STATUS_ACTIONS = [
  { status: 'accepted', label: 'Accept', icon: PackageCheck },
  { status: 'packed', label: 'Mark packed', icon: PackageOpen },
  { status: 'shipped', label: 'Ship', icon: Truck },
  { status: 'delivered', label: 'Deliver', icon: PackageCheck },
] as const;

export default function VendorOrdersPage() {
  const { data, isLoading, isError, refetch } = useVendorOrders();
  const updateStatus = useUpdateVendorOrderStatus();
  const rejectOrder = useRejectVendorOrder();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [rejectingOrderId, setRejectingOrderId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const orders = useMemo(() => data?.items ?? [], [data?.items]);
  const actionOrderId = (updateStatus.variables as { vendorOrderId?: string } | undefined)?.vendorOrderId
    ?? (rejectOrder.variables as { vendorOrderId?: string } | undefined)?.vendorOrderId
    ?? null;

  const summary = useMemo(() => {
    const active = orders.filter((order) => !['delivered', 'cancelled', 'rejected', 'returned'].includes(order.status));
    return {
      total: orders.length,
      active: active.length,
      readyToShip: orders.filter((order) => order.status === 'packed').length,
      delivered: orders.filter((order) => order.status === 'delivered').length,
    };
  }, [orders]);

  async function handleStatusUpdate(vendorOrderId: string, status: string, remarks: string, location = '') {
    setFeedback(null);
    await updateStatus.mutateAsync({ vendorOrderId, status, remarks, location });
    setFeedback(`Vendor order updated to ${titleCaseStatus(status)}.`);
  }

  async function handleReject(orderId: string) {
    if (!rejectReason.trim()) {
      return;
    }
    setFeedback(null);
    await rejectOrder.mutateAsync({ vendorOrderId: orderId, reason: rejectReason.trim() });
    setRejectReason('');
    setRejectingOrderId(null);
    setFeedback('Vendor order rejected and the customer order was updated.');
  }

  if (isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Vendor orders</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading vendor orders">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-28 animate-pulse rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)]"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <StorefrontState
        eyebrow="Vendor orders"
        title="Orders unavailable"
        description="The vendor fulfillment queue could not be loaded from the live backend."
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  if (orders.length === 0) {
    return (
      <StorefrontState
        eyebrow="Vendor orders"
        title="No vendor orders yet"
        description="Accepted customer checkouts will appear here so your team can accept, pack, ship, and complete them."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Fulfillment queue</h1>
        <p className="mt-3 max-w-3xl text-sm text-[var(--text-secondary)]">
          Accept customer orders, advance fulfillment stages, and reject orders with an explicit vendor reason when necessary.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Total orders', value: summary.total },
          { label: 'Active queue', value: summary.active },
          { label: 'Packed and ready', value: summary.readyToShip },
          { label: 'Delivered', value: summary.delivered },
        ].map((item) => (
          <Card key={item.label} className="rounded-[24px]">
            <CardContent className="pt-5">
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{item.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {feedback ? (
        <div className="rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          {feedback}
        </div>
      ) : null}

      <div className="space-y-4">
        {orders.map((order) => {
          const isFinal = ['delivered', 'cancelled', 'rejected', 'returned'].includes(order.status);
          const isCurrentAction = actionOrderId === order.id && (updateStatus.isPending || rejectOrder.isPending);

          return (
            <Card key={order.id} className="rounded-[28px]">
              <CardContent className="space-y-4 pt-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{order.vendor_order_number}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                        {titleCaseStatus(order.status)}
                      </span>
                      {order.shipment ? (
                        <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent)]">
                          AWB {order.shipment.awb}
                        </span>
                      ) : null}
                    </div>
                    <p className="text-sm text-[var(--text-secondary)]">
                      Order total {formatCurrency(order.subtotal)} · Vendor net {formatCurrency(order.vendor_amount)} ·
                      Commission {formatCurrency(order.commission)}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      Shipment status {titleCaseStatus(order.shipment?.status ?? 'pending')} ·
                      ETA {formatDateLabel(order.shipment?.eta)}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {STATUS_ACTIONS.map((action) => (
                      <Button
                        key={action.status}
                        size="sm"
                        variant={order.status === action.status ? 'primary' : 'outline'}
                        disabled={isFinal || isCurrentAction || order.status === action.status}
                        isLoading={isCurrentAction && updateStatus.isPending && order.status !== action.status}
                        onClick={() =>
                          void handleStatusUpdate(
                            order.id,
                            action.status,
                            `Vendor marked order as ${action.status.replace('_', ' ')}.`,
                            action.status === 'shipped'
                              ? order.shipment?.current_location || 'Vendor dispatch'
                              : order.shipment?.current_location || ''
                          )
                        }
                      >
                        <action.icon className="mr-2 h-4 w-4" />
                        {action.label}
                      </Button>
                    ))}
                    {!isFinal ? (
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={isCurrentAction}
                        onClick={() => {
                          setRejectingOrderId(order.id);
                          setRejectReason('');
                        }}
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        Reject
                      </Button>
                    ) : null}
                  </div>
                </div>

                {order.shipment ? (
                  <div className="rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)] p-4 text-sm text-[var(--text-secondary)]">
                    <p className="font-medium text-[var(--text-primary)]">Shipment activity</p>
                    <p className="mt-1">
                      Current location: {order.shipment.current_location || 'Awaiting carrier scan'} · ETA {formatDateLabel(order.shipment.eta)}
                    </p>
                  </div>
                ) : null}

                {rejectingOrderId === order.id ? (
                  <div className="space-y-3 rounded-[22px] border border-[var(--border-color)] p-4">
                    <p className="text-sm font-medium text-[var(--text-primary)]">Reject vendor order</p>
                    <textarea
                      value={rejectReason}
                      onChange={(event) => setRejectReason(event.target.value)}
                      rows={3}
                      className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
                      placeholder="Explain why this order cannot be fulfilled."
                    />
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setRejectingOrderId(null);
                          setRejectReason('');
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        isLoading={rejectOrder.isPending && actionOrderId === order.id}
                        onClick={() => {
                          void handleReject(order.id);
                        }}
                      >
                        Confirm rejection
                      </Button>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
