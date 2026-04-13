'use client';

import { useMemo, useState } from 'react';
import { FileText, PackagePlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatDateLabel, titleCaseStatus } from '@/lib/commerce-format';
import {
  useCreateVendorPickupJob,
  useGenerateVendorShipmentLabel,
  useVendorOrders,
} from '@/hooks/use-orders';

export default function VendorShipmentsPage() {
  const { data, isLoading, isError, refetch } = useVendorOrders();
  const createPickupJob = useCreateVendorPickupJob();
  const generateLabel = useGenerateVendorShipmentLabel();
  const [feedback, setFeedback] = useState<string | null>(null);

  const ordersWithShipments = useMemo(
    () => (data?.items ?? []).filter((order) => order.shipment),
    [data?.items]
  );

  const activeOrderId = (createPickupJob.variables as { vendorOrderId?: string } | undefined)?.vendorOrderId ?? null;
  const activeShipmentId = (generateLabel.variables as { shipmentId?: string } | undefined)?.shipmentId ?? null;

  async function handlePickupJob(vendorOrderId: string) {
    setFeedback(null);
    const result = await createPickupJob.mutateAsync({ vendorOrderId });
    setFeedback(`Pickup job ${result.pickup_job_id} created for the selected vendor order.`);
  }

  async function handleLabel(shipmentId: string) {
    setFeedback(null);
    const result = await generateLabel.mutateAsync({ shipmentId });
    if (result.label_url) {
      window.open(result.label_url, '_blank', 'noopener,noreferrer');
    }
    setFeedback(`Shipping label generated for AWB ${result.awb}.`);
  }

  if (isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Shipping labels and shipments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading shipments">
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
        eyebrow="Vendor shipments"
        title="Shipments unavailable"
        description="The shipment and label view could not be loaded from the live backend."
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  if (ordersWithShipments.length === 0) {
    return (
      <StorefrontState
        eyebrow="Vendor shipments"
        title="No shipment records yet"
        description="Once vendor orders create shipment records, this page will expose pickup-job actions and stable shipping-label retrieval."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Shipping labels and shipments</h1>
        <p className="mt-3 max-w-3xl text-sm text-[var(--text-secondary)]">
          Create pickup jobs, open stable shipping labels, and monitor shipment status from the vendor-facing logistics endpoints.
        </p>
      </div>

      {feedback ? (
        <div className="rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          {feedback}
        </div>
      ) : null}

      <div className="space-y-4">
        {ordersWithShipments.map((order) => {
          const shipment = order.shipment;
          if (!shipment) {
            return null;
          }

          return (
            <Card key={order.id} className="rounded-[28px]">
              <CardContent className="space-y-4 pt-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{order.vendor_order_number}</p>
                    <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">AWB {shipment.awb}</p>
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">
                      Status {titleCaseStatus(shipment.status)} · Current location {shipment.current_location || 'Awaiting scan'} · ETA {formatDateLabel(shipment.eta)}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      isLoading={createPickupJob.isPending && activeOrderId === order.id}
                      onClick={() => {
                        void handlePickupJob(order.id);
                      }}
                    >
                      <PackagePlus className="mr-2 h-4 w-4" />
                      Create pickup job
                    </Button>
                    <Button
                      size="sm"
                      isLoading={generateLabel.isPending && activeShipmentId === shipment.id}
                      onClick={() => {
                        void handleLabel(shipment.id);
                      }}
                    >
                      <FileText className="mr-2 h-4 w-4" />
                      Open label
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
