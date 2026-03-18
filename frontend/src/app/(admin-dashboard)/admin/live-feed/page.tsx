import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const events = [
  'Order paid and confirmed',
  'Shipment label generated',
  'Return approved and reverse pickup assigned',
  'Vendor payout request approved',
];

export default function AdminLiveFeedPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Live operations feed</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {events.map((event) => (
          <div key={event} className="rounded-[22px] border border-[rgba(25,30,45,0.08)] p-4 text-sm text-[#54483f]">
            {event}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
