'use client';

import { useState } from 'react';
import { Plus, Store, CheckCircle2, XCircle, Clock, X, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type VendorStatus = 'submitted' | 'under_review' | 'resubmission_required' | 'approved' | 'rejected';

interface VendorItem {
  id: string;
  name: string;
  email: string;
  category: string;
  status: VendorStatus;
  submittedAt: string;
  missingDocs: string[];
  reviewOutcome?: string;
}

const INITIAL_VENDORS: VendorItem[] = [
  { id: '1', name: 'Artisan Crafts Co.', email: 'hello@artisancrafts.com', category: 'Handmade', status: 'under_review', submittedAt: '2025-03-20', missingDocs: [] },
  { id: '2', name: 'Tech Gadgets Ltd.', email: 'vendor@techgadgets.io', category: 'Electronics', status: 'approved', submittedAt: '2025-03-15', missingDocs: [], reviewOutcome: 'All KYC checks passed.' },
  { id: '3', name: 'Green Living Store', email: 'info@greenliving.shop', category: 'Eco Products', status: 'resubmission_required', submittedAt: '2025-03-22', missingDocs: ['pan'], reviewOutcome: 'PAN image unreadable.' },
  { id: '4', name: 'Vintage Finds', email: 'shop@vintagefinds.com', category: 'Vintage', status: 'rejected', submittedAt: '2025-03-10', missingDocs: ['gst', 'bank'], reviewOutcome: 'Document mismatch after retries.' },
];

const STATUS_ICONS: Record<VendorStatus, React.ReactNode> = {
  submitted: <Clock className="h-4 w-4" />,
  under_review: <Clock className="h-4 w-4" />,
  resubmission_required: <AlertTriangle className="h-4 w-4" />,
  approved: <CheckCircle2 className="h-4 w-4" />,
  rejected: <XCircle className="h-4 w-4" />,
};

const STATUS_STYLES: Record<VendorStatus, string> = {
  submitted: 'bg-[var(--warning-soft)] text-[var(--text-secondary)]',
  under_review: 'bg-[var(--warning-soft)] text-[var(--text-secondary)]',
  resubmission_required: 'bg-amber-100 text-amber-700',
  approved: 'bg-[var(--success-soft)] text-emerald-700',
  rejected: 'bg-[var(--danger-soft)] text-red-700',
};

function AddVendorModal({ onClose, onAdd }: { onClose: () => void; onAdd: (v: Omit<VendorItem, 'id' | 'submittedAt'>) => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [category, setCategory] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    onAdd({ name: name.trim(), email: email.trim(), category: category.trim() || 'General', status: 'submitted', missingDocs: ['gst', 'pan', 'bank'] });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-[28px] border border-[var(--border-color)] bg-[var(--surface)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.16)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Invite vendor</h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Business name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Artisan Crafts Co." required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Contact email</label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vendor@example.com" required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Category</label>
            <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Electronics, Handmade" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" type="button" onClick={onClose}>Cancel</Button>
            <Button type="submit">Send invite</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminVendorsPage() {
  const [vendors, setVendors] = useState<VendorItem[]>(INITIAL_VENDORS);
  const [showAdd, setShowAdd] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'all' | VendorStatus>('all');

  const filtered = statusFilter === 'all' ? vendors : vendors.filter((v) => v.status === statusFilter);

  const handleAdd = (v: Omit<VendorItem, 'id' | 'submittedAt'>) => {
    setVendors((prev) => [...prev, { ...v, id: String(Date.now()), submittedAt: new Date().toISOString().split('T')[0] }]);
  };

  const setStatus = (id: string, status: VendorStatus) => {
    setVendors((prev) => prev.map((v) => (v.id === id ? { ...v, status } : v)));
  };

  const pendingCount = vendors.filter((v) => ['submitted', 'under_review', 'resubmission_required'].includes(v.status)).length;
  const approvedCount = vendors.filter((v) => v.status === 'approved').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Vendor Management</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
            Review vendor onboarding, resubmissions, payout readiness, and operational health.
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          Invite vendor
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Total vendors', value: vendors.length },
          { label: 'Pending review', value: pendingCount },
          { label: 'Approved', value: approvedCount },
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
              <CardTitle>Vendor roster</CardTitle>
              <CardDescription className="mt-1">Approve or reject vendor applications.</CardDescription>
            </div>
            <div className="flex rounded-xl border border-[var(--border-color)] bg-white p-1">
              {(['all', 'submitted', 'under_review', 'resubmission_required', 'approved', 'rejected'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setStatusFilter(f)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    statusFilter === f
                      ? 'bg-[var(--foreground)] text-[var(--background)]'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)]'
                  }`}
                >
                  {f[0].toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <div className="px-6 py-14 text-center">
              <p className="text-sm font-medium text-[var(--text-primary)]">No vendors found.</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">Try a different filter or invite a new vendor.</p>
            </div>
          ) : (
            <ul className="divide-y divide-[var(--border-color)]">
              {filtered.map((vendor) => (
                <li key={vendor.id} className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                      <Store className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{vendor.name}</p>
                      <p className="truncate text-xs text-[var(--text-muted)]">{vendor.email} · {vendor.category}</p>
                      {vendor.missingDocs.length > 0 && (
                        <p className="truncate text-[11px] text-amber-700">Missing: {vendor.missingDocs.join(', ')}</p>
                      )}
                      {vendor.reviewOutcome && <p className="truncate text-[11px] text-[var(--text-muted)]">{vendor.reviewOutcome}</p>}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[vendor.status]}`}>
                      {STATUS_ICONS[vendor.status]}
                      {vendor.status}
                    </span>
                    {(vendor.status === 'submitted' || vendor.status === 'under_review' || vendor.status === 'resubmission_required') && (
                      <>
                        <Button size="sm" onClick={() => setStatus(vendor.id, 'approved')}>Approve</Button>
                        <Button size="sm" variant="outline" onClick={() => setStatus(vendor.id, 'rejected')}>Reject</Button>
                      </>
                    )}
                    {vendor.status === 'rejected' && (
                      <Button size="sm" variant="outline" onClick={() => setStatus(vendor.id, 'under_review')}>Re-review</Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {showAdd && <AddVendorModal onClose={() => setShowAdd(false)} onAdd={handleAdd} />}
    </div>
  );
}
