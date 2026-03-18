import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AgentDashboardPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Delivery overview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-[#54483f]">
          <p>See assigned deliveries, update status, capture proof of delivery, and report exceptions.</p>
        </CardContent>
      </Card>
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Today&apos;s route</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-[#54483f]">
          <p>The backend supports event-based tracking and delivery exceptions. Advanced live GPS route streaming remains future work.</p>
        </CardContent>
      </Card>
    </div>
  );
}
