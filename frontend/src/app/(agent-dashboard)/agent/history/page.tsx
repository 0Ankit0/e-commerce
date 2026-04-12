'use client';

import Link from 'next/link';

import { Button } from '@/components/ui/button';
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
            Branch consistency signal: first-attempt success {snapshot?.snapshot.first_attempt_success_rate_percent ?? 0}% ·
            aging queue 6h+ {snapshot?.snapshot.aging_queue_over_6h ?? 0}
          </p>
          <Button asChild variant="outline"><Link href="/agent/branch-cockpit">Open branch manager cockpit</Link></Button>
        </CardContent>
      </Card>
    </div>
  );
}
