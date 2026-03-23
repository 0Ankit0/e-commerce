'use client';

import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useVendorProducts } from '@/hooks/use-catalog';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency } from '@/lib/commerce-format';

export default function VendorProductsPage() {
  const { data, isLoading, isError, error, refetch } = useVendorProducts();

  if (isLoading) {
    return (
      <Card className="rounded-[32px]">
        <CardHeader>
          <CardTitle>Vendor products</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" role="status" aria-label="Loading vendor products">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-20 animate-pulse rounded-[22px] border border-[rgba(25,30,45,0.08)] bg-[#f7efe1]"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    const description =
      status === 401
        ? 'Sign in again to load your catalog.'
        : status === 403
          ? 'Your account does not currently have vendor catalog access.'
          : 'We could not load your live vendor inventory from the API.';

    return (
      <StorefrontState
        eyebrow="Vendor inventory"
        title="Inventory unavailable"
        description={description}
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  const products = data?.items ?? [];

  if (products.length === 0) {
    return (
      <StorefrontState
        eyebrow="Vendor inventory"
        title="No products yet"
        description="Your vendor account is connected, but there are no products in inventory yet. Add or import products to populate this dashboard."
      />
    );
  }

  return (
    <Card className="rounded-[32px]">
      <CardHeader>
        <CardTitle>Vendor products</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {products.map((product) => (
          <div key={product.id} className="flex items-center justify-between rounded-[22px] border border-[rgba(25,30,45,0.08)] p-4">
            <div>
              <p className="font-medium text-[#1d1b18]">{product.name}</p>
              <p className="text-sm text-[#6f6257]">{product.category?.name}</p>
            </div>
            <span className="text-sm font-semibold text-[#1d1b18]">
              {product.min_selling_price ? formatCurrency(product.min_selling_price) : 'Quote'}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
