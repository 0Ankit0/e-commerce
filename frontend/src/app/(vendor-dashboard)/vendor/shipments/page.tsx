import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function VendorShipmentsPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Shipping labels and shipments</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Generate stable shipping-label artifacts, monitor shipment status, and handle pickup coordination.</p>
      </CardContent>
    </Card>
  );
}
