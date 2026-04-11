'use client';

import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, FileText, XCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAdminKycDecision, useAdminKycQueue, useAdminVendorTimeline } from '@/hooks';

const FILTERS = [
  { key: 'new', label: 'New' },
  { key: 'pending', label: 'Pending' },
  { key: 'sla_breach', label: 'SLA breach' },
] as const;

export default function AdminVendorsPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['key']>('pending');
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const [reasonCode, setReasonCode] = useState('missing_information');
  const [reason, setReason] = useState('');

  const queue = useAdminKycQueue(filter);
  const items = queue.data?.items ?? [];
  const selected = items.find((item) => item.vendor.id === selectedVendorId) ?? items[0];
  const timeline = useAdminVendorTimeline(selected?.vendor.id);
  const decisionMutation = useAdminKycDecision();

  const decide = async (action: 'approve' | 'reject' | 'request-resubmission') => {
    if (!selected) return;
    await decisionMutation.mutateAsync({ vendorId: selected.vendor.id, action, reasonCode, reason });
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">KYC review queue</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Filter by new, pending, and SLA breach; review packet docs and timeline side-by-side.</p>
      </div>

      <div className="flex rounded-xl border border-[var(--border-color)] bg-white p-1 w-fit">
        {FILTERS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setFilter(item.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${filter === item.key ? 'bg-[var(--foreground)] text-[var(--background)]' : 'text-[var(--text-secondary)]'}`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Queue</CardTitle>
            <CardDescription>{queue.data?.total ?? 0} vendors</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {items.map((item) => (
              <button
                key={item.vendor.id}
                type="button"
                onClick={() => setSelectedVendorId(item.vendor.id)}
                className={`w-full rounded-xl border p-3 text-left ${selected?.vendor.id === item.vendor.id ? 'border-[var(--foreground)]' : 'border-[var(--border-color)]'}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold">{item.vendor.display_name}</p>
                  {item.sla_breach ? <AlertTriangle className="h-4 w-4 text-red-600" /> : <Clock className="h-4 w-4 text-amber-600" />}
                </div>
                <p className="text-xs text-[var(--text-muted)]">{item.vendor.kyc_status} · {item.age_hours}h</p>
                <p className="text-xs text-amber-700">Missing docs: {item.checks.missing_documents.join(', ') || 'none'}</p>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Review panel</CardTitle>
            <CardDescription>Documents + decision timeline</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selected ? (
              <p className="text-sm text-[var(--text-muted)]">No vendor selected.</p>
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  {['GST', 'PAN', 'BANK'].map((doc) => (
                    <div key={doc} className="rounded-xl border border-[var(--border-color)] p-3">
                      <p className="text-xs text-[var(--text-muted)]">{doc}</p>
                      <div className="mt-1 flex items-center gap-2 text-sm">
                        <FileText className="h-4 w-4" />
                        <span>Ready for review</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="space-y-2">
                  <Input value={reasonCode} onChange={(e) => setReasonCode(e.target.value)} placeholder="reason_code" />
                  <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="decision note" />
                  <div className="flex gap-2">
                    <Button onClick={() => decide('approve')}><CheckCircle2 className="mr-1 h-4 w-4" />Approve</Button>
                    <Button variant="outline" onClick={() => decide('request-resubmission')}><Clock className="mr-1 h-4 w-4" />Resubmit</Button>
                    <Button variant="destructive" onClick={() => decide('reject')}><XCircle className="mr-1 h-4 w-4" />Reject</Button>
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--border-color)] p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">Decision timeline</p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {(timeline.data ?? []).slice(0, 6).map((event) => (
                      <li key={`${event.event_type}-${event.created_at}`}>{event.event_type}: {event.message}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
