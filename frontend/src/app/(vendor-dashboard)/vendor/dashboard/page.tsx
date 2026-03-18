import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DollarSign, Package, Truck, Warehouse } from 'lucide-react';

const stats = [
  { label: 'Live SKUs', value: '148', icon: Package, color: 'bg-[#dff1e8] text-[#123f35]' },
  { label: 'Reserved stock', value: '37', icon: Warehouse, color: 'bg-[#f7efe1] text-[#c96d44]' },
  { label: 'Shipments waiting', value: '09', icon: Truck, color: 'bg-[#d9eafb] text-[#13324f]' },
  { label: 'Pending payout', value: '$4.8k', icon: DollarSign, color: 'bg-[#f0d6ef] text-[#7c2f74]' },
];

export default function VendorDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[#8b6e57]">Vendor desk</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[#1d1b18]">
          Run catalog, stock, shipments, and payouts from one surface.
        </h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="rounded-[28px]">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[#8b6e57]">{stat.label}</p>
                  <p className="mt-1 text-2xl font-semibold text-[#1d1b18]">{stat.value}</p>
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
              <div key={item} className="rounded-[22px] border border-[rgba(25,30,45,0.08)] p-4 text-sm text-[#54483f]">
                {item}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-[32px]">
          <CardHeader>
            <CardTitle>Operational overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-[#54483f]">
            <p>Vendor users only see catalog, inventory, order, shipment, and payout links in the sidebar.</p>
            <p>This dashboard is ready to attach live vendor metrics as those frontend data hooks are expanded.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
