'use client';

import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useVendorProducts } from '@/hooks/use-catalog';
import { StorefrontState } from '@/components/storefront/storefront-state';
import { formatCurrency } from '@/lib/commerce-format';
import { getRuntimeErrorState, isPaginatedPayload } from '@/lib/runtime-route';

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
              className="h-20 animate-pulse rounded-[22px] border border-[var(--border-color)] bg-[var(--surface-muted)]"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  const hasPartialPayload = data !== undefined && !isPaginatedPayload(data);

  if (isError || hasPartialPayload) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    const runtimeError = getRuntimeErrorState(error, 'Inventory unavailable');

    return (
      <StorefrontState
        eyebrow={status === 403 ? 'Vendor access blocked' : 'Vendor inventory'}
        title={hasPartialPayload ? 'Inventory payload incomplete' : runtimeError.title}
        description={
          hasPartialPayload
            ? 'Vendor inventory response is missing required fields. No hidden fallback list is rendered for this route.'
            : runtimeError.description
        }
        details={
          hasPartialPayload
            ? 'Payload validation failed: expected { items: [], total: number } from /vendor/products.'
            : runtimeError.details
        }
        actionLabel={runtimeError.actionLabel}
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
          <div key={product.id} className="flex items-center justify-between rounded-[22px] border border-[var(--border-color)] p-4">
            <div>
              <p className="font-medium text-[var(--text-primary)]">{product.name}</p>
              <p className="text-sm text-[var(--text-secondary)]">{product.category?.name}</p>
            </div>
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              {product.min_selling_price ? formatCurrency(product.min_selling_price) : 'Quote'}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
