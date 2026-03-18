import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function VendorInventoryPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Inventory console</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Track on-hand stock, reservations for unpaid orders, and low-stock alerts from this inventory view.</p>
        <p>The backend already supports warehouse-aware stock and reservation-safe checkout.</p>
      </CardContent>
    </Card>
  );
}
