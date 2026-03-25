import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AgentHistoryPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Delivery history</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[var(--text-secondary)]">
        <p>Review completed deliveries, exception notes, and POD activity.</p>
      </CardContent>
    </Card>
  );
}
