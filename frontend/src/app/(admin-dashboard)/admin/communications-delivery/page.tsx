'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useEmailDeliveryAnalytics,
  useEmailDeliveryDeadLetters,
  useEmailDeliveryMessages,
} from '@/hooks/use-system';

function asPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export default function CommunicationsDeliveryPage() {
  const analyticsQuery = useEmailDeliveryAnalytics();
  const messagesQuery = useEmailDeliveryMessages();
  const deadLettersQuery = useEmailDeliveryDeadLetters();

  const analytics = analyticsQuery.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Email delivery analytics</CardTitle>
          <CardDescription>
            Track full lifecycle performance across queued, sent, delivered, bounced, failed, and complained.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Total messages</p>
            <p className="text-2xl font-semibold">{analytics?.total ?? 0}</p>
          </div>
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Delivery rate</p>
            <p className="text-2xl font-semibold">{asPercent(analytics?.delivery_rate ?? 0)}</p>
          </div>
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Bounce rate</p>
            <p className="text-2xl font-semibold">{asPercent(analytics?.bounce_rate ?? 0)}</p>
          </div>
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Failure rate</p>
            <p className="text-2xl font-semibold">{asPercent(analytics?.failure_rate ?? 0)}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Status breakdown</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-3">
          {(['queued', 'sent', 'delivered', 'bounced', 'failed', 'complained'] as const).map((status) => (
            <div key={status} className="rounded-xl border p-3 capitalize">
              <p className="text-xs text-[var(--text-muted)]">{status}</p>
              <p className="text-lg font-semibold">{analytics?.status_counts?.[status] ?? 0}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent messages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(messagesQuery.data ?? []).slice(0, 20).map((row) => (
            <div key={row.id} className="rounded-xl border p-3">
              <p className="font-medium">#{row.id} · {row.subject}</p>
              <p className="text-xs text-[var(--text-muted)]">
                {row.status} · provider {row.provider ?? 'n/a'} · attempts {row.attempt_count}/{row.max_attempts}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Failure reasons</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(analytics?.failure_reasons ?? []).map((reason) => (
            <p key={reason.reason}>{reason.reason}: {reason.count}</p>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dead letters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(deadLettersQuery.data ?? []).slice(0, 20).map((row) => (
            <p key={row.id}>#{row.id} · message #{row.message_id} · {row.reason}</p>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
