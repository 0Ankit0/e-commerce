'use client';

import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, Upload } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useSubmitKycPacket, useVendorKycHistory } from '@/hooks';

export default function VendorDashboardPage() {
  const history = useVendorKycHistory();
  const submitPacket = useSubmitKycPacket();
  const [form, setForm] = useState({
    gst_doc_number: '', gst_file_url: '', pan_doc_number: '', pan_file_url: '',
    bank_account_name: '', bank_account_number: '', bank_ifsc_code: '', bank_name: '',
  });

  const setField = (key: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-4xl text-[var(--text-primary)]">Onboarding progress & KYC resubmission</h1>
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
        <CardHeader><CardTitle>Recent KYC timeline</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {(history.data?.items ?? []).slice(0, 8).map((item) => (
              <li key={`${item.event_type}-${item.created_at}`}>{item.event_type} — {item.message}</li>
            ))}
          </ul>
          {history.data?.items?.length === 0 && <p className="text-sm text-[var(--text-muted)]">No events yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
