'use client';

import { useState } from 'react';
import { Plus, BarChart3, Download, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type ReportType = 'sales' | 'users' | 'vendors' | 'inventory' | 'custom';

interface ReportItem {
  id: string;
  name: string;
  type: ReportType;
  period: string;
  createdAt: string;
  status: 'ready' | 'pending';
}

const INITIAL_REPORTS: ReportItem[] = [
  { id: '1', name: 'Q1 2025 Sales Summary', type: 'sales', period: 'Jan–Mar 2025', createdAt: '2025-04-01', status: 'ready' },
  { id: '2', name: 'March User Acquisition', type: 'users', period: 'Mar 2025', createdAt: '2025-04-01', status: 'ready' },
  { id: '3', name: 'Vendor Payout Report', type: 'vendors', period: 'Mar 2025', createdAt: '2025-03-31', status: 'ready' },
  { id: '4', name: 'Low Stock Alert Export', type: 'inventory', period: 'Current', createdAt: '2025-03-25', status: 'pending' },
];

const TYPE_LABELS: Record<ReportType, string> = {
  sales: 'Sales',
  users: 'Users',
  vendors: 'Vendors',
  inventory: 'Inventory',
  custom: 'Custom',
};

function AddReportModal({ onClose, onAdd }: { onClose: () => void; onAdd: (r: Omit<ReportItem, 'id' | 'createdAt' | 'status'>) => void }) {
  const [name, setName] = useState('');
  const [type, setType] = useState<ReportType>('sales');
  const [period, setPeriod] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onAdd({ name: name.trim(), type, period: period.trim() || 'Current' });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-[28px] border border-[var(--border-color)] bg-[var(--surface)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.16)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Schedule new report</h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></Button>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Report name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Q2 Sales Summary" required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Report type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as ReportType)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            >
              {(Object.entries(TYPE_LABELS) as [ReportType, string][]).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Period</label>
            <Input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="e.g. Apr–Jun 2025, Current" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" type="button" onClick={onClose}>Cancel</Button>
            <Button type="submit">Schedule report</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>(INITIAL_REPORTS);
  const [showAdd, setShowAdd] = useState(false);
  const [typeFilter, setTypeFilter] = useState<'all' | ReportType>('all');

  const filtered = typeFilter === 'all' ? reports : reports.filter((r) => r.type === typeFilter);

  const handleAdd = (r: Omit<ReportItem, 'id' | 'createdAt' | 'status'>) => {
    setReports((prev) => [...prev, { ...r, id: String(Date.now()), createdAt: new Date().toISOString().split('T')[0], status: 'pending' }]);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Reports & Exports</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
            Schedule CSV exports, manage reporting jobs, and review operational summaries.
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          Schedule report
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Total reports', value: reports.length },
          { label: 'Ready', value: reports.filter((r) => r.status === 'ready').length },
          { label: 'Pending', value: reports.filter((r) => r.status === 'pending').length },
        ].map((stat) => (
          <Card key={stat.label} className="rounded-[24px]">
            <CardContent className="pt-5">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">{stat.label}</p>
              <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="rounded-[28px]">
        <CardHeader className="border-b border-[var(--border-color)]">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Report history</CardTitle>
              <CardDescription className="mt-1">Download ready reports or check on pending exports.</CardDescription>
            </div>
            <div className="flex flex-wrap rounded-xl border border-[var(--border-color)] bg-white p-1">
              {(['all', ...Object.keys(TYPE_LABELS)] as ('all' | ReportType)[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setTypeFilter(f)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    typeFilter === f
                      ? 'bg-[var(--foreground)] text-[var(--background)]'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)]'
                  }`}
                >
                  {f === 'all' ? 'All' : TYPE_LABELS[f as ReportType]}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <div className="px-6 py-14 text-center">
              <p className="text-sm font-medium text-[var(--text-primary)]">No reports found.</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">Try a different filter or schedule a new report.</p>
            </div>
          ) : (
            <ul className="divide-y divide-[var(--border-color)]">
              {filtered.map((report) => (
                <li key={report.id} className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                      <BarChart3 className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{report.name}</p>
                      <p className="truncate text-xs text-[var(--text-muted)]">{TYPE_LABELS[report.type]} · {report.period} · Created {report.createdAt}</p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      report.status === 'ready' ? 'bg-[var(--success-soft)] text-emerald-700' : 'bg-[var(--warning-soft)] text-[var(--text-secondary)]'
                    }`}>
                      {report.status}
                    </span>
                    {report.status === 'ready' && (
                      <Button size="sm" variant="outline">
                        <Download className="mr-1.5 h-3.5 w-3.5" />
                        Download
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {showAdd && <AddReportModal onClose={() => setShowAdd(false)} onAdd={handleAdd} />}
    </div>
  );
}

