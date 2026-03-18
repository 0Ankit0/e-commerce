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
      className="group block overflow-hidden rounded-[28px] border border-[rgba(25,30,45,0.08)] bg-white shadow-[0_18px_50px_rgba(25,30,45,0.06)] transition-all hover:-translate-y-1 hover:shadow-[0_22px_60px_rgba(25,30,45,0.12)]"
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-[radial-gradient(circle_at_top,#f4d2a8,transparent_60%),linear-gradient(135deg,#fbf6ef,#efe3d0)]">
        {heroImage ? (
          <img
            src={heroImage}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm uppercase tracking-[0.24em] text-[#8b6e57]">
            {product.category?.name ?? 'Product'}
          </div>
        )}
        <div className="absolute left-4 top-4 rounded-full bg-[rgba(255,255,255,0.82)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b5648] backdrop-blur">
          {product.is_featured ? 'Featured' : product.brand?.name ?? 'Curated'}
        </div>
        <div className="absolute right-4 top-4 rounded-full bg-[rgba(29,27,24,0.78)] p-2 text-white">
          <Heart className="h-4 w-4" />
        </div>
      </div>
      <div className="p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-[#9b806d]">
              {product.category?.name ?? 'General'}
            </p>
            <h3 className="mt-2 font-[family:var(--font-display)] text-2xl leading-tight text-[#1d1b18]">
              {product.name}
            </h3>
          </div>
          <div className="flex items-center gap-1 rounded-full bg-[#f7efe1] px-3 py-1 text-xs font-semibold text-[#6b5648]">
            <Star className="h-3.5 w-3.5 fill-current" />
            {product.avg_rating.toFixed(1)}
          </div>
        </div>
        <p className="line-clamp-2 text-sm text-[#6f6257]">{product.short_description || product.description}</p>
        <div className="mt-5 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#9b806d]">Starting at</p>
            <p className="mt-1 text-2xl font-semibold text-[#1d1b18]">
              {product.min_selling_price ? `$${product.min_selling_price.toFixed(2)}` : 'Quote'}
            </p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${product.in_stock ? 'bg-[#dff1e8] text-[#1a6f4c]' : 'bg-[#f7dfdf] text-[#a34040]'}`}>
            {product.in_stock ? 'Ready to ship' : 'Restocking'}
          </span>
        </div>
      </div>
    </Link>
  );
}
