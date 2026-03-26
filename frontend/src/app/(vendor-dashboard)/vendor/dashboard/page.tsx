import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DollarSign, Package, Truck, Warehouse } from 'lucide-react';

const stats = [
  { label: 'Live SKUs', value: '148', icon: Package, color: 'bg-[var(--success-soft)] text-emerald-800' },
  { label: 'Reserved stock', value: '37', icon: Warehouse, color: 'bg-[var(--surface-muted)] text-[var(--accent)]' },
  { label: 'Shipments waiting', value: '09', icon: Truck, color: 'bg-[var(--accent-soft)] text-[var(--accent)]' },
  { label: 'Pending payout', value: '$4.8k', icon: DollarSign, color: 'bg-[var(--warning-soft)] text-[var(--text-secondary)]' },
];

export default function VendorDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[var(--text-primary)]">
          Run catalog, stock, shipments, and payouts from one surface.
        </h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="rounded-[28px]">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[var(--text-muted)]">{stat.label}</p>
                  <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">{stat.value}</p>
                </div>
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${stat.color}`}>
                  <stat.icon className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[32px]">
          <CardHeader>
            <CardTitle>Today&apos;s focus</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {['Approve pricing updates', 'Generate shipping labels for packed orders', 'Review low-stock alerts', 'Check payout request approvals'].map((item) => (
              <div key={item} className="rounded-[22px] border border-[var(--border-color)] p-4 text-sm text-[var(--text-secondary)]">
                {item}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-[32px]">
          <CardHeader>
            <CardTitle>Operational overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-[var(--text-secondary)]">
            <p>Vendor users only see catalog, inventory, order, shipment, and payout links in the sidebar.</p>
            <p>This dashboard is ready to attach live vendor metrics as those frontend data hooks are expanded.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
