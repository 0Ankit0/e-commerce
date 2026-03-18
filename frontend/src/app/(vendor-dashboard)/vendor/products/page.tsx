import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { mockProducts } from '@/lib/mock-commerce';

export default function VendorProductsPage() {
  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Vendor products</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {mockProducts.map((product) => (
          <div key={product.id} className="flex items-center justify-between rounded-[22px] border border-[rgba(25,30,45,0.08)] p-4">
            <div>
              <p className="font-medium text-[#1d1b18]">{product.name}</p>
              <p className="text-sm text-[#6f6257]">{product.category?.name}</p>
            </div>
            <span className="text-sm font-semibold text-[#1d1b18]">
              {product.min_selling_price ? `$${product.min_selling_price.toFixed(2)}` : 'Quote'}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
