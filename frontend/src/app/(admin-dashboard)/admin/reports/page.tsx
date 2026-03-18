import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminReportsPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Reports and exports</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Use this area for CSV exports, scheduled reporting jobs, and operational summaries.</p>
      </CardContent>
    </Card>
  );
}
