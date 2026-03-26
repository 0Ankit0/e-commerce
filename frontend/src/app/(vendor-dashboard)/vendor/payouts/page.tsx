import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function VendorPayoutsPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Payout requests</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[var(--text-secondary)]">
        <p>Review payout history, submit payout requests, and watch approval or batch status updates.</p>
      </CardContent>
    </Card>
  );
}
