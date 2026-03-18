import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function VendorOrdersPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Vendor orders</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Process accepted orders, packing, shipping progression, and return-aware order timelines here.</p>
      </CardContent>
    </Card>
  );
}
