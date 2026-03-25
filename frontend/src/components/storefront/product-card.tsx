import Link from 'next/link';
import { Heart, Star } from 'lucide-react';
import type { CatalogProduct } from '@/types';

interface ProductCardProps {
  product: CatalogProduct;
}

export function ProductCard({ product }: ProductCardProps) {
  const heroImage = product.images.find((image) => image.is_primary)?.url ?? product.images[0]?.url;

  return (
    <Link
      href={`/products/${product.id}`}
      className="group block overflow-hidden rounded-[28px] border border-[var(--border-color)] bg-white shadow-[0_18px_50px_rgba(25,30,45,0.06)] transition-all hover:-translate-y-1 hover:shadow-[0_22px_60px_rgba(25,30,45,0.12)]"
    >
      <div className="relative aspect-[4/3] overflow-hidden" style={{ background: `radial-gradient(circle at top, color-mix(in srgb, var(--accent) 28%, var(--surface-muted)), transparent 60%), var(--surface-muted)` }}>
        {heroImage ? (
          <img
            src={heroImage}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm uppercase tracking-[0.24em] text-[var(--text-muted)]">
            {product.category?.name ?? 'Product'}
          </div>
        )}
        <div className="absolute left-4 top-4 rounded-full bg-[color-mix(in_srgb,var(--surface)_82%,transparent)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--text-secondary)] backdrop-blur">
          {product.is_featured ? 'Featured' : product.brand?.name ?? 'Curated'}
        </div>
        <div className="absolute right-4 top-4 rounded-full bg-[color-mix(in_srgb,var(--foreground)_78%,transparent)] p-2 text-[var(--background)]">
          <Heart className="h-4 w-4" />
        </div>
      </div>
      <div className="p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">
              {product.category?.name ?? 'General'}
            </p>
            <h3 className="mt-2 font-[family:var(--font-display)] text-2xl leading-tight text-[var(--text-primary)]">
              {product.name}
            </h3>
          </div>
          <div className="flex items-center gap-1 rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-secondary)]">
            <Star className="h-3.5 w-3.5 fill-current" />
            {product.avg_rating.toFixed(1)}
          </div>
        </div>
        <p className="line-clamp-2 text-sm text-[var(--text-secondary)]">{product.short_description || product.description}</p>
        <div className="mt-5 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Starting at</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
              {product.min_selling_price ? `$${product.min_selling_price.toFixed(2)}` : 'Quote'}
            </p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${product.in_stock ? 'bg-[var(--success-soft)] text-emerald-700' : 'bg-[var(--danger-soft)] text-red-700'}`}>
            {product.in_stock ? 'Ready to ship' : 'Restocking'}
          </span>
        </div>
      </div>
    </Link>
  );
}
