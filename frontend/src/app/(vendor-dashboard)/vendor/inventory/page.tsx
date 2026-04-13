'use client';

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { useUpdateVendorInventory, useVendorInventorySummary } from '@/hooks/use-catalog';

interface InventoryDraft {
  quantity: string;
  reorderLevel: string;
  reorderQty: string;
}

export default function VendorInventoryPage() {
  const { data, isLoading, isError, refetch } = useVendorInventorySummary();
  const updateInventory = useUpdateVendorInventory();
  const [drafts, setDrafts] = useState<Record<string, InventoryDraft>>({});
  const [feedback, setFeedback] = useState<string | null>(null);

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const activeVariantId = (updateInventory.variables as { variantId?: string } | undefined)?.variantId ?? null;

  useEffect(() => {
    setDrafts((current) => {
      const next = { ...current };
      let changed = false;

      for (const item of items) {
        if (!next[item.variant_id]) {
          next[item.variant_id] = {
            quantity: String(item.quantity),
            reorderLevel: String(item.reorder_level),
            reorderQty: String(item.reorder_qty),
          };
          changed = true;
        }
      }

      return changed ? next : current;
    });
  }, [items]);

  const summary = useMemo(() => {
    return {
      variants: items.length,
      lowStock: items.filter((item) => item.low_stock).length,
      reservedUnits: items.reduce((total, item) => total + item.reserved_qty, 0),
      availableUnits: items.reduce((total, item) => total + item.available_qty, 0),
    };
  }, [items]);

  async function handleSave(variantId: string) {
    const draft = drafts[variantId];
    if (!draft) {
      return;
    }

    setFeedback(null);
    await updateInventory.mutateAsync({
      variantId,
      quantity: Number.parseInt(draft.quantity || '0', 10),
      reorderLevel: Number.parseInt(draft.reorderLevel || '0', 10),
      reorderQty: Number.parseInt(draft.reorderQty || '0', 10),
    });
    setFeedback('Inventory update saved.');
  }

  if (isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Inventory console</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading inventory">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-24 animate-pulse rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)]"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <StorefrontState
        eyebrow="Vendor inventory"
        title="Inventory unavailable"
        description="The vendor inventory summary could not be loaded from the live backend."
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  if (items.length === 0) {
    return (
      <StorefrontState
        eyebrow="Vendor inventory"
        title="No tracked variants yet"
        description="Publish products with variants to start tracking on-hand, reserved, and low-stock inventory in this console."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Inventory console</h1>
        <p className="mt-3 max-w-3xl text-sm text-[var(--text-secondary)]">
          Monitor on-hand stock, reservation pressure, and reorder policy per variant. Save updates directly against the live vendor inventory API.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Tracked variants', value: summary.variants },
          { label: 'Low-stock alerts', value: summary.lowStock },
          { label: 'Reserved units', value: summary.reservedUnits },
          { label: 'Available units', value: summary.availableUnits },
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
        {items.map((item) => {
          const draft = drafts[item.variant_id] ?? {
            quantity: String(item.quantity),
            reorderLevel: String(item.reorder_level),
            reorderQty: String(item.reorder_qty),
          };

          return (
            <Card key={item.variant_id} className="rounded-[28px]">
              <CardContent className="space-y-4 pt-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{item.sku}</p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">Variant {item.variant_id} · Product {item.product_id}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-[var(--text-secondary)]">On hand {item.quantity}</span>
                      <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-[var(--accent)]">Reserved {item.reserved_qty}</span>
                      <span className="rounded-full bg-[var(--success-soft)] px-3 py-1 text-emerald-700">Available {item.available_qty}</span>
                      {item.low_stock ? (
                        <span className="rounded-full bg-[var(--warning-soft)] px-3 py-1 text-[var(--text-secondary)]">Low stock</span>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <label className="space-y-1 text-sm">
                    <span className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">Quantity</span>
                    <input
                      type="number"
                      min={0}
                      value={draft.quantity}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [item.variant_id]: {
                            ...draft,
                            quantity: event.target.value,
                          },
                        }))
                      }
                      className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2"
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">Reorder level</span>
                    <input
                      type="number"
                      min={0}
                      value={draft.reorderLevel}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [item.variant_id]: {
                            ...draft,
                            reorderLevel: event.target.value,
                          },
                        }))
                      }
                      className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2"
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">Reorder quantity</span>
                    <input
                      type="number"
                      min={0}
                      value={draft.reorderQty}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [item.variant_id]: {
                            ...draft,
                            reorderQty: event.target.value,
                          },
                        }))
                      }
                      className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2"
                    />
                  </label>
                </div>

                <div className="flex justify-end">
                  <Button
                    size="sm"
                    isLoading={updateInventory.isPending && activeVariantId === item.variant_id}
                    onClick={() => {
                      void handleSave(item.variant_id);
                    }}
                  >
                    Save inventory
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
