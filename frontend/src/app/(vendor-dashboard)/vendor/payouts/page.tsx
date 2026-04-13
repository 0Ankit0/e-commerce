'use client';

import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency, formatDateTimeLabel, titleCaseStatus } from '@/lib/commerce-format';
import {
  useCreateVendorPayoutRequest,
  useVendorAnalytics,
  useVendorPayoutRequests,
  useVendorPayouts,
} from '@/hooks/use-vendors';

export default function VendorPayoutsPage() {
  const analytics = useVendorAnalytics();
  const payouts = useVendorPayouts();
  const requests = useVendorPayoutRequests();
  const createRequest = useCreateVendorPayoutRequest();
  const [amount, setAmount] = useState('');
  const [notes, setNotes] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const payoutItems = useMemo(() => payouts.data?.items ?? [], [payouts.data?.items]);
  const requestItems = useMemo(() => requests.data?.items ?? [], [requests.data?.items]);

  const summary = useMemo(() => {
    const paidTotal = payoutItems
      .filter((item) => item.status === 'paid')
      .reduce((total, item) => total + item.amount, 0);
    const pendingRequests = requestItems.filter((item) => item.status !== 'paid' && item.status !== 'rejected');
    return {
      netRevenue: analytics.data?.analytics.net_revenue ?? 0,
      paidTotal,
      pendingRequests: pendingRequests.length,
      pendingAmount: pendingRequests.reduce((total, item) => total + item.amount, 0),
    };
  }, [analytics.data?.analytics.net_revenue, payoutItems, requestItems]);

  async function handleSubmit() {
    const parsedAmount = Number.parseFloat(amount);
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setFeedback('Enter a valid payout amount.');
      return;
    }
    setFeedback(null);
    await createRequest.mutateAsync({ amount: parsedAmount, notes });
    setAmount('');
    setNotes('');
    setFeedback('Payout request submitted for review.');
  }

  if (analytics.isLoading || payouts.isLoading || requests.isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Payout requests</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading payouts">
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

  if (analytics.isError || payouts.isError || requests.isError) {
    return (
      <StorefrontState
        eyebrow="Vendor payouts"
        title="Payout data unavailable"
        description="The vendor payout summary could not be loaded from the live backend."
        actionLabel="Retry"
        onAction={() => {
          void Promise.all([analytics.refetch(), payouts.refetch(), requests.refetch()]);
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Payout requests</h1>
        <p className="mt-3 max-w-3xl text-sm text-[var(--text-secondary)]">
          Submit payout requests, review approval state, and monitor settled payout batches from the live vendor finance API.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Net revenue', value: formatCurrency(summary.netRevenue) },
          { label: 'Paid out', value: formatCurrency(summary.paidTotal) },
          { label: 'Pending requests', value: summary.pendingRequests },
          { label: 'Pending amount', value: formatCurrency(summary.pendingAmount) },
        ].map((item) => (
          <Card key={item.label} className="rounded-[24px]">
            <CardContent className="pt-5">
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{item.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="rounded-[28px]">
        <CardHeader>
          <CardTitle>Submit payout request</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-[0.35fr_1fr_auto]">
          <Input
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="Amount"
          />
          <Input
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Settlement note or payout window"
          />
          <Button isLoading={createRequest.isPending} onClick={() => void handleSubmit()}>
            Submit request
          </Button>
        </CardContent>
      </Card>

      {feedback ? (
        <div className="rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          {feedback}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-[28px]">
          <CardHeader>
            <CardTitle>Request queue</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {requestItems.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">No payout requests yet.</p>
            ) : (
              requestItems.map((request) => (
                <div key={request.id} className="rounded-[22px] border border-[var(--border-color)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-[var(--text-primary)]">{formatCurrency(request.amount)}</p>
                    <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                      {titleCaseStatus(request.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">{request.notes || 'No vendor note provided.'}</p>
                  <p className="mt-2 text-xs text-[var(--text-muted)]">Submitted {formatDateTimeLabel(request.created_at)}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[28px]">
          <CardHeader>
            <CardTitle>Payout history</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {payoutItems.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">No payout batches have been settled yet.</p>
            ) : (
              payoutItems.map((payout) => (
                <div key={payout.id} className="rounded-[22px] border border-[var(--border-color)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-[var(--text-primary)]">{payout.reference || 'Reference pending'}</p>
                      <p className="text-sm text-[var(--text-secondary)]">
                        Amount {formatCurrency(payout.amount)} · Commission {formatCurrency(payout.commission_amount)}
                      </p>
                    </div>
                    <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                      {titleCaseStatus(payout.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-[var(--text-muted)]">
                    Created {formatDateTimeLabel(payout.created_at)} · Paid {formatDateTimeLabel(payout.paid_at)}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
