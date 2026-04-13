'use client';

import { useState } from 'react';
import { Plus, ShoppingBag, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency, formatDateLabel, titleCaseStatus } from '@/lib/commerce-format';
import { useAdminOrders, useCreateAdminOrderNote } from '@/hooks/use-orders';
import {
  isSupportedOrderReference,
  normalizeOrderReference,
  ORDER_REFERENCE_PLACEHOLDER,
} from '@/lib/order-reference';

function AddOrderNoteModal({
  onClose,
  onSubmit,
  isLoading,
}: {
  onClose: () => void;
  onSubmit: (payload: { orderId: string; note: string }) => Promise<void>;
  isLoading: boolean;
}) {
  const [orderId, setOrderId] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSupportedOrderReference(orderId)) {
      setError('Use an order number (current/legacy) or hashid.');
      return;
    }
    setError('');
    try {
      await onSubmit({ orderId: normalizeOrderReference(orderId), note });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this note.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-[28px] border border-[var(--border-color)] bg-[var(--surface)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.16)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Add order note</h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></Button>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Order number</label>
            <Input
              value={orderId}
              onChange={(e) => setOrderId(normalizeOrderReference(e.target.value))}
              placeholder={ORDER_REFERENCE_PLACEHOLDER}
              required
            />
            {error && <p className="text-xs text-red-600">{error}</p>}
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Admin note</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
              placeholder="Capture your findings or actions taken on this order."
              required
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" type="button" onClick={onClose}>Cancel</Button>
            <Button type="submit" isLoading={isLoading}>Save note</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminOrdersPage() {
  const { data, isLoading, isError, refetch } = useAdminOrders();
  const createNote = useCreateAdminOrderNote();
  const [showAdd, setShowAdd] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'all' | string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const orders = data?.items ?? [];

  const normalizedSearch = searchTerm.trim();
  const filteredByStatus = statusFilter === 'all' ? orders : orders.filter((o) => o.status === statusFilter);
  const filtered = !normalizedSearch
      ? filteredByStatus
      : filteredByStatus.filter((order) => {
        const normalizedOrderNumber = order.order_number.toUpperCase();
        const products = order.items.map((item) => item.product_name).join(' ').toUpperCase();
        if (isSupportedOrderReference(normalizedSearch)) {
          const normalizedRef = normalizeOrderReference(normalizedSearch);
          return normalizedOrderNumber === normalizedRef || order.id === normalizedRef;
        }
        return normalizedOrderNumber.includes(normalizedSearch.toUpperCase()) || products.includes(normalizedSearch.toUpperCase());
      });

  const activeCount = orders.filter((o) => !['delivered', 'cancelled'].includes(o.status)).length;

  async function handleCreateNote(payload: { orderId: string; note: string }) {
    await createNote.mutateAsync({
      orderId: payload.orderId,
      note: payload.note,
      noteType: 'internal',
      isCustomerVisible: false,
    });
  }

  if (isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Order oversight</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading admin orders">
          {Array.from({ length: 5 }).map((_, index) => (
            <div
              key={index}
              className="h-20 animate-pulse rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)]"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <StorefrontState
        eyebrow="Admin console"
        title="Order oversight unavailable"
        description="The admin orders queue could not be loaded from the live backend."
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Order Oversight</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
            View cross-platform order activity, intervene on order notes, and inspect status progression.
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          Add note
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Total orders', value: orders.length },
          { label: 'Active', value: activeCount },
          { label: 'Delivered', value: orders.filter((o) => o.status === 'delivered').length },
        ].map((stat) => (
          <Card key={stat.label} className="rounded-[24px]">
            <CardContent className="pt-5">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">{stat.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="rounded-[28px]">
        <CardHeader className="border-b border-[var(--border-color)]">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Order queue</CardTitle>
              <CardDescription className="mt-1">Monitor and intervene on active orders across all vendors.</CardDescription>
            </div>
            <Input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={ORDER_REFERENCE_PLACEHOLDER}
              className="w-full sm:w-72"
            />
            <div className="flex flex-wrap rounded-xl border border-[var(--border-color)] bg-white p-1">
              {(['all', 'pending', 'processing', 'packed', 'shipped', 'delivered', 'cancelled'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setStatusFilter(f)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    statusFilter === f
                      ? 'bg-[var(--foreground)] text-[var(--background)]'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)]'
                  }`}
                >
                  {f[0].toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <div className="px-6 py-14 text-center">
              <p className="text-sm font-medium text-[var(--text-primary)]">No orders found.</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">Try a different filter.</p>
            </div>
          ) : (
            <ul className="divide-y divide-[var(--border-color)]">
              {filtered.map((order) => (
                <li key={order.id} className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--surface-muted)] text-[var(--text-muted)]">
                      <ShoppingBag className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[var(--text-primary)]">{order.order_number}</p>
                      <p className="truncate text-xs text-[var(--text-muted)]">
                        {order.items.map((item) => item.product_name).join(', ') || 'Order items unavailable'} · {formatCurrency(order.total)}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full bg-[var(--surface-muted)] px-2.5 py-1 text-xs font-semibold text-[var(--text-secondary)]">
                      {titleCaseStatus(order.status)}
                    </span>
                    <span className="text-xs text-[var(--text-muted)]">{formatDateLabel(order.created_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {showAdd && (
        <AddOrderNoteModal
          onClose={() => setShowAdd(false)}
          onSubmit={handleCreateNote}
          isLoading={createNote.isPending}
        />
      )}
    </div>
  );
}
