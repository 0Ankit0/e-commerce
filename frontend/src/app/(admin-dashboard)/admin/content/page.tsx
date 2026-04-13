'use client';

import { useState } from 'react';
import { Plus, Image as ImageIcon, FileText, Pencil, Trash2, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type ContentType = 'banner' | 'page';

interface ContentItem {
  id: string;
  type: ContentType;
  title: string;
  target?: string;
  status: 'active' | 'draft';
}

const INITIAL_ITEMS: ContentItem[] = [
  { id: '1', type: 'banner', title: 'Summer Sale — 30% off sitewide', target: '/shop?sale=summer', status: 'active' },
  { id: '2', type: 'banner', title: 'New arrivals from top vendors', target: '/shop?sort=newest', status: 'draft' },
  { id: '3', type: 'page', title: 'About Us', target: '/about', status: 'active' },
  { id: '4', type: 'page', title: 'Shipping & Returns Policy', target: '/shipping', status: 'active' },
];

function AddContentModal({ onClose, onAdd }: { onClose: () => void; onAdd: (item: Omit<ContentItem, 'id'>) => void }) {
  const [type, setType] = useState<ContentType>('banner');
  const [title, setTitle] = useState('');
  const [target, setTarget] = useState('');
  const [status, setStatus] = useState<'active' | 'draft'>('draft');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onAdd({ type, title: title.trim(), target: target.trim() || undefined, status });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-[28px] border border-[var(--border-color)] bg-[var(--surface)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.16)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Add content item</h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Type</label>
            <div className="flex gap-3">
              {(['banner', 'page'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors ${
                    type === t
                      ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                      : 'border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'
                  }`}
                >
                  {t === 'banner' ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Title</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Enter a descriptive title" required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Target URL</label>
            <Input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="/shop or https://example.com" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as 'active' | 'draft')}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" type="button" onClick={onClose}>Cancel</Button>
            <Button type="submit">Add item</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminContentPage() {
  const [items, setItems] = useState<ContentItem[]>(INITIAL_ITEMS);
  const [showAdd, setShowAdd] = useState(false);
  const [typeFilter, setTypeFilter] = useState<'all' | ContentType>('all');

  const filtered = typeFilter === 'all' ? items : items.filter((item) => item.type === typeFilter);
  const bannerCount = items.filter((i) => i.type === 'banner').length;
  const pageCount = items.filter((i) => i.type === 'page').length;

  const handleAdd = (item: Omit<ContentItem, 'id'>) => {
    setItems((prev) => [...prev, { ...item, id: String(Date.now()) }]);
  };

  const handleDelete = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const toggleStatus = (id: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, status: item.status === 'active' ? 'draft' : 'active' } : item
      )
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Content Management</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
            Manage promotional banners and static pages surfaced in the public storefront.
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          Add content
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Total items', value: items.length },
          { label: 'Banners', value: bannerCount },
          { label: 'Static pages', value: pageCount },
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
              <CardTitle>Content items</CardTitle>
              <CardDescription className="mt-1">Click the status badge to toggle active / draft.</CardDescription>
            </div>
            <div className="flex rounded-xl border border-[var(--border-color)] bg-white p-1">
              {(['all', 'banner', 'page'] as const).map((f) => (
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
                  {f[0].toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <div className="px-6 py-14 text-center">
              <p className="text-sm font-medium text-[var(--text-primary)]">No items yet.</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">Click "Add content" to get started.</p>
            </div>
          ) : (
            <ul className="divide-y divide-[var(--border-color)]">
              {filtered.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-4 px-6 py-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
                      {item.type === 'banner' ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                      {item.target && (
                        <p className="mt-0.5 truncate text-xs text-[var(--text-muted)]">{item.target}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => toggleStatus(item.id)}
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold transition-colors ${
                        item.status === 'active'
                          ? 'bg-[var(--success-soft)] text-emerald-700'
                          : 'bg-[var(--surface-muted)] text-[var(--text-muted)]'
                      }`}
                    >
                      {item.status}
                    </button>
                    <Button variant="ghost" size="sm" className="px-2" aria-label="Edit item">
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="px-2 text-red-600 hover:bg-[var(--danger-soft)] hover:text-red-700"
                      onClick={() => handleDelete(item.id)}
                      aria-label="Delete item"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {showAdd && <AddContentModal onClose={() => setShowAdd(false)} onAdd={handleAdd} />}
    </div>
  );
}
