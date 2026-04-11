'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useNotificationChannelPerformance, useNotificationTemplatePerformance } from '@/hooks/use-observability';

function asPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function asMs(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '—';
  return `${Math.round(value)} ms`;
}

export default function NotificationAnalyticsPage() {
  const channelQuery = useNotificationChannelPerformance({ limit: 30 });
  const templateQuery = useNotificationTemplatePerformance({ limit: 30 });

  const channelRows = channelQuery.data?.items ?? [];
  const templateRows = templateQuery.data?.items ?? [];

  const totals = channelRows.reduce(
    (acc, row) => {
      acc.total += row.total;
      acc.failed += row.failed;
      acc.delivered += row.delivered;
      acc.latency += row.avg_latency_ms;
      return acc;
    },
    { total: 0, delivered: 0, failed: 0, latency: 0 }
  );

  const latencyAvg = channelRows.length ? totals.latency / channelRows.length : 0;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Notification delivery analytics</CardTitle>
          <CardDescription>Channel and template-level performance trends with failure diagnostics.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Delivery rate</p>
            <p className="text-2xl font-semibold">{asPercent(totals.total ? totals.delivered / totals.total : 0)}</p>
          </div>
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Failure rate</p>
            <p className="text-2xl font-semibold">{asPercent(totals.total ? totals.failed / totals.total : 0)}</p>
          </div>
          <div className="rounded-xl border p-3">
            <p className="text-xs text-[var(--text-muted)]">Average latency</p>
            <p className="text-2xl font-semibold">{asMs(latencyAvg)}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Channel performance trend</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {channelRows.map((row) => (
            <div key={`${row.day}-${row.channel}`} className="rounded-xl border p-3">
              <p className="font-medium">{row.day} · {row.channel}</p>
              <p className="text-xs text-[var(--text-muted)]">
                Delivered {asPercent(row.delivery_rate)} · Failed {asPercent(row.failure_rate)} · Latency {asMs(row.avg_latency_ms)}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Template performance trend</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {templateRows.map((row) => (
            <div key={`${row.day}-${row.template}-${row.channel}`} className="rounded-xl border p-3">
              <p className="font-medium">{row.day} · template {row.template} · {row.channel}</p>
              <p className="text-xs text-[var(--text-muted)]">
                Total {row.total} · Delivered {asPercent(row.delivery_rate)} · Failed {asPercent(row.failure_rate)}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
