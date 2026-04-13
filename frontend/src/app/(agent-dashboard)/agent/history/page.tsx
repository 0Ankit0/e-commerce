'use client';

import Link from 'next/link';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useBranchDashboardSnapshot } from '@/hooks/use-observability';

export default function AgentHistoryPage() {
  const { data: snapshot } = useBranchDashboardSnapshot({ timezone: 'UTC' });

  return (
    <div className="space-y-4">
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Delivery history</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-[var(--text-secondary)]">
          <p>Review completed deliveries, exception notes, and POD activity.</p>
          <p className="rounded-lg border p-3 text-xs">
            Branch consistency signal: first-attempt success {snapshot?.snapshot.attempt_success_rate_percent ?? 0}% ·
            aging queue 6h+ {snapshot?.snapshot.aging_queue_over_6h ?? 0}
          </p>
          <Link
            href="/agent/branch-cockpit"
            className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-transparent px-4 py-2 text-base font-medium transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Open branch manager cockpit
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
