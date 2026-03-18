import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminContentPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Homepage banners and static pages</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Manage promotional banners and static pages surfaced in the public storefront.</p>
      </CardContent>
    </Card>
  );
}
