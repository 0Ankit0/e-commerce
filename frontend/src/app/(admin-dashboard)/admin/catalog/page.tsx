import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminCatalogPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Catalog moderation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-[#54483f]">
        <p>Approve products, inspect category and brand structure, and moderate the public catalog.</p>
      </CardContent>
    </Card>
  );
}
