'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminPromotionsPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Campaign Ops</p>
        <h1 className="text-3xl font-semibold tracking-tight">Promotions</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Review marketplace campaigns and coordinate launch windows across catalog and communications.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Promotions workspace</CardTitle>
          <CardDescription>
            This route is now live and ready for integration with campaign APIs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border px-2 py-1 text-xs text-[var(--text-muted)]">Draft</span>
            <span className="rounded-full border px-2 py-1 text-xs text-[var(--text-muted)]">Scheduled</span>
            <span className="rounded-full border px-2 py-1 text-xs text-[var(--text-muted)]">Active</span>
            <span className="rounded-full border px-2 py-1 text-xs text-[var(--text-muted)]">Archived</span>
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            No active promotions yet. Connect this page to promotion services when they are enabled.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
