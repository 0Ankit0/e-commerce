'use client';

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatDateTimeLabel, titleCaseStatus } from '@/lib/commerce-format';
import { useAdminOrderLiveFeed } from '@/hooks/use-orders';

const SOURCES = ['all', 'order', 'return', 'shipment', 'payout', 'vendor'] as const;

export default function AdminLiveFeedPage() {
  const [sourceFilter, setSourceFilter] = useState<(typeof SOURCES)[number]>('all');
  const { data, isLoading, isError, refetch } = useAdminOrderLiveFeed(50);

  const items = useMemo(() => {
    const rows = data?.items ?? [];
    if (sourceFilter === 'all') {
      return rows;
    }
    return rows.filter((item) => item.source === sourceFilter);
  }, [data?.items, sourceFilter]);

  if (isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Live operations feed</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading live feed">
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
        eyebrow="Admin operations"
        title="Live feed unavailable"
        description="The cross-domain operations stream could not be loaded from the admin live-feed endpoint."
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Admin console</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Live operations feed</h1>
        <p className="mt-3 max-w-3xl text-sm text-[var(--text-secondary)]">
          Watch order, return, shipment, payout, and vendor events in a single queue backed by the live admin feed endpoint.
        </p>
      </div>

      <Card className="rounded-[28px]">
        <CardContent className="flex flex-wrap gap-2 pt-5">
          {SOURCES.map((source) => (
            <button
              key={source}
              type="button"
              onClick={() => setSourceFilter(source)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                sourceFilter === source
                  ? 'bg-[var(--foreground)] text-[var(--background)]'
                  : 'bg-[var(--surface-muted)] text-[var(--text-secondary)]'
              }`}
            >
              {source === 'all' ? 'All events' : titleCaseStatus(source)}
            </button>
          ))}
        </CardContent>
      </Card>

      {items.length === 0 ? (
        <StorefrontState
          eyebrow="Admin operations"
          title="No events for this filter"
          description="Try a different source filter to inspect other live operational activity."
        />
      ) : (
        <div className="space-y-4">
          {items.map((item, index) => (
            <Card key={`${item.source}-${item.event_type}-${item.created_at}-${index}`} className="rounded-[28px]">
              <CardContent className="space-y-3 pt-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                        {titleCaseStatus(item.source)}
                      </span>
                      <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent)]">
                        {item.event_type}
                      </span>
                    </div>
                    <p className="text-base font-semibold text-[var(--text-primary)]">{item.message}</p>
                    <p className="text-xs text-[var(--text-muted)]">
                      Actor {item.actor_user_id ?? 'system'} · {formatDateTimeLabel(item.created_at)}
                    </p>
                  </div>
                </div>

                {Object.keys(item.payload).length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(item.payload).map(([key, value]) => (
                      <span
                        key={key}
                        className="rounded-full border border-[var(--border-color)] px-3 py-1 text-xs text-[var(--text-secondary)]"
                      >
                        {key}: {String(value)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
