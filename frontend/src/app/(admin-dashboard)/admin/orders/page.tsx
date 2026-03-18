import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminOrdersPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Admin order oversight</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>View cross-platform order activity, intervene on order notes, and inspect status progression.</p>
      </CardContent>
    </Card>
  );
}
