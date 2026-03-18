import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminVendorsPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Vendor approvals and monitoring</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Review vendor onboarding, resubmissions, payout readiness, and operational health.</p>
      </CardContent>
    </Card>
  );
}
