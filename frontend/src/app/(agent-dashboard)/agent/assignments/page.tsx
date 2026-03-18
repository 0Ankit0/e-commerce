import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AgentAssignmentsPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Assigned deliveries</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Assignment and dispatch-focused layout for delivery agents.</p>
      </CardContent>
    </Card>
  );
}
