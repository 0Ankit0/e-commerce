'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { CreditCard, RotateCcw, Truck } from 'lucide-react';
import { useApiErrorMessage } from '@/hooks/use-commerce';
import {
  useCancelOrder,
  useCreateReturn,
  useOrderDetail,
  useOrderInvoice,
  useOrderNotes,
  useOrderTimeline,
  useOrderTracking,
} from '@/hooks/use-orders';
import { formatCurrency, formatDateLabel, formatDateTimeLabel, titleCaseStatus } from '@/lib/commerce-format';

export default function OrderDetailPage() {
  const params = useParams<{ orderId: string }>();
  const orderId = Array.isArray(params.orderId) ? params.orderId[0] : params.orderId;
  const [returnReason, setReturnReason] = useState('');
  const [returnItemId, setReturnItemId] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const { getErrorMessage } = useApiErrorMessage();
  const { data: order } = useOrderDetail(orderId);
  const { data: timeline } = useOrderTimeline(orderId);
  const { data: notes } = useOrderNotes(orderId);
  const { data: invoice } = useOrderInvoice(orderId);
  const { data: tracking } = useOrderTracking(orderId);
  const cancelOrder = useCancelOrder();
  const createReturn = useCreateReturn();

  if (!order) {
    return <div className="rounded-[28px] bg-white p-6 text-sm text-[#6f6257]">Loading order details...</div>;
  }

  const currentOrder = order;

  async function handleCancelOrder() {
    try {
      await cancelOrder.mutateAsync(currentOrder.id);
      setMessage('Order cancelled successfully.');
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  }

  async function handleReturnRequest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!returnReason.trim()) {
      setMessage('Add a short reason for the return request.');
      return;
    }

    try {
      const response = await createReturn.mutateAsync({
        orderId: currentOrder.id,
        orderItemId: returnItemId || undefined,
        reason: returnReason,
      });
      setMessage(`Return request submitted with status ${titleCaseStatus(response.status)}.`);
      setReturnReason('');
      setReturnItemId('');
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-[#8b6e57]">Order detail</p>
          <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">{order.order_number}</h1>
          <p className="mt-3 text-sm text-[#6f6257]">
            {titleCaseStatus(currentOrder.status)} · {formatDateLabel(currentOrder.created_at)} · {titleCaseStatus(currentOrder.payment_status)}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleCancelOrder}
            className="rounded-full border border-[rgba(25,30,45,0.08)] px-4 py-2 text-sm font-semibold text-[#8c3d3d]"
          >
            Cancel order
          </button>
        </div>
      </div>

      {message ? (
        <div className="rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fff7ed] px-5 py-4 text-sm text-[#7a573f]">
          {message}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <div className="space-y-6">
          <section className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Items</p>
            <div className="mt-5 space-y-3">
              {currentOrder.items.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col gap-3 rounded-[24px] border border-[rgba(25,30,45,0.08)] p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-[#1d1b18]">{item.product_name}</p>
                    <p className="mt-1 text-xs text-[#6f6257]">
                      {item.variant_name} · qty {item.quantity} · {titleCaseStatus(item.status)}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-[#1d1b18]">{formatCurrency(item.total_price)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <div className="flex items-center gap-3">
              <Truck className="h-5 w-5 text-[#c96d44]" />
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Tracking</p>
                <p className="text-lg font-medium text-[#1d1b18]">Shipment progress</p>
              </div>
            </div>
            <div className="mt-5 space-y-4">
              {tracking?.shipments.map((shipment) => (
                <div key={shipment.shipment_id} className="rounded-[24px] bg-[#fcf7f0] p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-[#8b6e57]">{shipment.awb}</p>
                      <p className="mt-1 text-sm font-medium text-[#1d1b18]">{titleCaseStatus(shipment.status)}</p>
                      <p className="mt-1 text-xs text-[#6f6257]">{shipment.current_location || 'Awaiting first scan'}</p>
                    </div>
                  </div>
                  <div className="mt-4 space-y-3 border-l border-[rgba(25,30,45,0.08)] pl-4">
                    {shipment.events.map((event) => (
                      <div key={`${shipment.shipment_id}-${event.timestamp}-${event.status}`} className="relative">
                        <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-[#c96d44]" />
                        <p className="text-sm font-medium text-[#1d1b18]">{titleCaseStatus(event.status)}</p>
                        <p className="text-xs text-[#6f6257]">{event.location} · {event.remarks}</p>
                        <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-[#8b6e57]">{formatDateTimeLabel(event.timestamp)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <div className="flex items-center gap-3">
              <CreditCard className="h-5 w-5 text-[#1a6f4c]" />
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Invoice</p>
                <p className="text-lg font-medium text-[#1d1b18]">{invoice?.invoice_number ?? 'Generating'}</p>
              </div>
            </div>
            <div className="mt-5 space-y-3 text-sm text-[#55483d]">
              <div className="flex items-center justify-between"><span>Subtotal</span><span>{formatCurrency(currentOrder.subtotal)}</span></div>
              <div className="flex items-center justify-between"><span>Discount</span><span>- {formatCurrency(currentOrder.discount)}</span></div>
              <div className="flex items-center justify-between"><span>Shipping</span><span>{formatCurrency(currentOrder.shipping_charge)}</span></div>
              <div className="flex items-center justify-between"><span>Tax</span><span>{formatCurrency(currentOrder.tax)}</span></div>
              <div className="flex items-center justify-between border-t border-[rgba(25,30,45,0.08)] pt-3 text-base font-semibold text-[#1d1b18]">
                <span>Total</span>
                <span>{formatCurrency(currentOrder.total)}</span>
              </div>
            </div>
          </section>

          <section className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Timeline</p>
            <div className="mt-5 space-y-4 border-l border-[rgba(25,30,45,0.08)] pl-4">
              {timeline?.map((event) => (
                <div key={event.id} className="relative">
                  <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-[#1d1b18]" />
                  <p className="text-sm font-medium text-[#1d1b18]">{event.message}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-[#8b6e57]">{formatDateTimeLabel(event.created_at)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Customer-visible notes</p>
            <div className="mt-4 space-y-3">
              {notes?.length ? (
                notes.map((note) => (
                  <div key={note.id} className="rounded-[22px] bg-[#fcf7f0] px-4 py-3">
                    <p className="text-sm text-[#1d1b18]">{note.note}</p>
                    <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-[#8b6e57]">{formatDateTimeLabel(note.created_at)}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-[22px] bg-[#fcf7f0] px-4 py-3 text-sm text-[#6f6257]">No customer-facing notes on this order.</div>
              )}
            </div>
          </section>

          <section className="rounded-[32px] border border-[rgba(25,30,45,0.08)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <div className="flex items-center gap-3">
              <RotateCcw className="h-5 w-5 text-[#c96d44]" />
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[#8b6e57]">Return</p>
                <p className="text-lg font-medium text-[#1d1b18]">Request a return</p>
              </div>
            </div>
            <form onSubmit={handleReturnRequest} className="mt-5 space-y-4">
              <select
                value={returnItemId}
                onChange={(event) => setReturnItemId(event.target.value)}
                className="w-full rounded-full border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm outline-none"
              >
                <option value="">Entire order</option>
                {currentOrder.items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.product_name} · {item.variant_name}
                  </option>
                ))}
              </select>
              <textarea
                value={returnReason}
                onChange={(event) => setReturnReason(event.target.value)}
                rows={4}
                placeholder="Tell us why you want to return this order."
                className="w-full rounded-[24px] border border-[rgba(25,30,45,0.08)] bg-[#fcf7f0] px-4 py-3 text-sm outline-none"
              />
              <button type="submit" className="rounded-full bg-[#1d1b18] px-5 py-3 text-sm font-semibold text-white">
                Submit return request
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
