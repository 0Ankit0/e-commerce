'use client';

import { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, Upload } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatCurrency, formatDateTimeLabel, titleCaseStatus } from '@/lib/commerce-format';
import {
  useSubmitKycPacket,
  useVendorAnalytics,
  useVendorKycHistory,
  useVendorPayoutRequests,
  useVendorTimeline,
} from '@/hooks/use-vendors';

export default function VendorDashboardPage() {
  const history = useVendorKycHistory();
  const analytics = useVendorAnalytics();
  const timeline = useVendorTimeline();
  const payoutRequests = useVendorPayoutRequests();
  const submitPacket = useSubmitKycPacket();
  const [form, setForm] = useState({
    gst_doc_number: '', gst_file_url: '', pan_doc_number: '', pan_file_url: '',
    bank_account_name: '', bank_account_number: '', bank_ifsc_code: '', bank_name: '',
  });

  const setField = (key: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [key]: value }));
  const summaryCards = useMemo(
    () => [
      { label: 'Orders', value: analytics.data?.analytics.orders ?? 0 },
      { label: 'Net revenue', value: formatCurrency(analytics.data?.analytics.net_revenue) },
      { label: 'Products', value: analytics.data?.analytics.product_count ?? 0 },
      { label: 'Rating', value: analytics.data?.analytics.rating ?? 0 },
    ],
    [analytics.data]
  );

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Onboarding progress & KYC resubmission</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((item) => (
          <Card key={item.label} className="rounded-[24px]">
            <CardContent className="pt-5">
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{item.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>KYC step status</CardTitle></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          {Object.entries(history.data?.steps ?? { gst: 'pending', pan: 'pending', bank: 'pending' }).map(([step, status]) => (
            <div key={step} className="rounded-xl border border-[var(--border-color)] p-3">
              <p className="text-xs uppercase text-[var(--text-muted)]">{step}</p>
              <p className="mt-1 flex items-center gap-2 text-sm font-semibold">
                {status === 'complete' ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : status === 'submitted' ? <Clock className="h-4 w-4 text-amber-600" /> : <AlertTriangle className="h-4 w-4 text-red-600" />}
                {status}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Secure packet resubmission</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {Object.keys(form).map((key) => (
            <Input key={key} value={form[key as keyof typeof form]} onChange={(e) => setField(key as keyof typeof form, e.target.value)} placeholder={key} />
          ))}
          <Button onClick={() => submitPacket.mutate(form)}><Upload className="mr-2 h-4 w-4" />Submit KYC packet</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Payout readiness</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-[var(--text-secondary)]">
            Current vendor status: <strong className="text-[var(--text-primary)]">{titleCaseStatus(analytics.data?.vendor.status ?? 'pending')}</strong> ·
            KYC {titleCaseStatus(history.data?.kyc_status ?? 'pending')}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(payoutRequests.data?.items ?? []).slice(0, 4).map((request) => (
              <div key={request.id} className="rounded-xl border border-[var(--border-color)] p-3">
                <p className="font-medium text-[var(--text-primary)]">{formatCurrency(request.amount)}</p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">{titleCaseStatus(request.status)} · {formatDateTimeLabel(request.created_at)}</p>
              </div>
            ))}
          </div>
          {(payoutRequests.data?.items ?? []).length === 0 && <p className="text-[var(--text-muted)]">No payout requests submitted yet.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Recent vendor timeline</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {(timeline.data?.items ?? history.data?.items ?? []).slice(0, 8).map((item) => (
              <li key={`${item.event_type}-${item.created_at}`}>{item.event_type} — {item.message}</li>
            ))}
          </ul>
          {(timeline.data?.items?.length ?? history.data?.items?.length ?? 0) === 0 && <p className="text-sm text-[var(--text-muted)]">No events yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
