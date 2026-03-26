'use client';

import { useState } from 'react';
import { Plus, Package, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type ProductStatus = 'approved' | 'pending' | 'rejected';

interface CatalogProduct {
  id: string;
  name: string;
  vendor: string;
  category: string;
  price: string;
  status: ProductStatus;
}

const INITIAL_PRODUCTS: CatalogProduct[] = [
  { id: '1', name: 'Handcrafted Ceramic Mug', vendor: 'Artisan Crafts Co.', category: 'Home & Kitchen', price: '$28.00', status: 'approved' },
  { id: '2', name: 'Wireless Earbuds Pro', vendor: 'Tech Gadgets Ltd.', category: 'Electronics', price: '$79.99', status: 'pending' },
  { id: '3', name: 'Organic Bamboo Cutting Board', vendor: 'Green Living Store', category: 'Kitchen', price: '$34.50', status: 'approved' },
  { id: '4', name: '1980s Denim Jacket', vendor: 'Vintage Finds', category: 'Clothing', price: '$120.00', status: 'pending' },
  { id: '5', name: 'Scented Soy Candle Set', vendor: 'Artisan Crafts Co.', category: 'Home', price: '$45.00', status: 'rejected' },
];

const STATUS_STYLES: Record<ProductStatus, string> = {
  approved: 'bg-[var(--success-soft)] text-emerald-700',
  pending: 'bg-[var(--warning-soft)] text-[var(--text-secondary)]',
  rejected: 'bg-[var(--danger-soft)] text-red-700',
};

function AddProductModal({ onClose, onAdd }: { onClose: () => void; onAdd: (p: Omit<CatalogProduct, 'id'>) => void }) {
  const [name, setName] = useState('');
  const [vendor, setVendor] = useState('');
  const [category, setCategory] = useState('');
  const [price, setPrice] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onAdd({ name: name.trim(), vendor: vendor.trim() || 'Unknown', category: category.trim() || 'General', price: price.trim() || '$0.00', status: 'pending' });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-[28px] border border-[var(--border-color)] bg-[var(--surface)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.16)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Add catalog product</h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></Button>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Product name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Handcrafted Ceramic Mug" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Vendor</label>
              <Input value={vendor} onChange={(e) => setVendor(e.target.value)} placeholder="Vendor name" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Category</label>
              <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Electronics" />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Price</label>
            <Input value={price} onChange={(e) => setPrice(e.target.value)} placeholder="$0.00" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" type="button" onClick={onClose}>Cancel</Button>
            <Button type="submit">Add product</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminCatalogPage() {
  const [products, setProducts] = useState<CatalogProduct[]>(INITIAL_PRODUCTS);
  const [showAdd, setShowAdd] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'all' | ProductStatus>('all');

  const filtered = statusFilter === 'all' ? products : products.filter((p) => p.status === statusFilter);

  const handleAdd = (p: Omit<CatalogProduct, 'id'>) => {
    setProducts((prev) => [...prev, { ...p, id: String(Date.now()) }]);
  };

  const setStatus = (id: string, status: ProductStatus) => {
    setProducts((prev) => prev.map((p) => (p.id === id ? { ...p, status } : p)));
  };

  const pendingCount = products.filter((p) => p.status === 'pending').length;
  const approvedCount = products.filter((p) => p.status === 'approved').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Admin Console</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">Catalog Moderation</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
            Approve products, inspect category and brand structure, and moderate the public catalog.
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          Add product
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Total products', value: products.length },
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
              <CardTitle>Product queue</CardTitle>
              <CardDescription className="mt-1">Review and approve or reject submitted products.</CardDescription>
            </div>
            <div className="flex rounded-xl border border-[var(--border-color)] bg-white p-1">
              {(['all', 'pending', 'approved', 'rejected'] as const).map((f) => (
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
              <p className="text-sm font-medium text-[var(--text-primary)]">No products found.</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">Try a different filter or add a product.</p>
            </div>
          ) : (
            <ul className="divide-y divide-[var(--border-color)]">
              {filtered.map((product) => (
                <li key={product.id} className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--surface-muted)] text-[var(--text-muted)]">
                      <Package className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{product.name}</p>
                      <p className="truncate text-xs text-[var(--text-muted)]">{product.vendor} · {product.category} · {product.price}</p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[product.status]}`}>
                      {product.status}
                    </span>
                    {product.status === 'pending' && (
                      <>
                        <Button size="sm" onClick={() => setStatus(product.id, 'approved')}>
                          <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                          Approve
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setStatus(product.id, 'rejected')}>
                          <AlertCircle className="mr-1.5 h-3.5 w-3.5" />
                          Reject
                        </Button>
                      </>
                    )}
                    {product.status === 'rejected' && (
                      <Button size="sm" variant="outline" onClick={() => setStatus(product.id, 'pending')}>Re-review</Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {showAdd && <AddProductModal onClose={() => setShowAdd(false)} onAdd={handleAdd} />}
    </div>
  );
}

