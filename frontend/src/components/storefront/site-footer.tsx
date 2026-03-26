import Link from 'next/link';

export function SiteFooter() {
  return (
    <footer className="border-t border-[var(--border-color)] bg-[var(--foreground)] text-[var(--background)]">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1.4fr_1fr_1fr] lg:px-8">
        <div>
          <p className="font-[family:var(--font-display)] text-3xl">Northstar Market</p>
          <p className="mt-4 max-w-md text-sm opacity-70">
            A multi-vendor marketplace for curated retail, fast operations, and role-aware commerce tools.
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em] opacity-50">Storefront</p>
          <div className="mt-4 flex flex-col gap-3 text-sm opacity-75">
            <Link href="/shop">All products</Link>
            <Link href="/login">Sign in</Link>
            <Link href="/signup">Create account</Link>
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em] opacity-50">Portals</p>
          <div className="mt-4 flex flex-col gap-3 text-sm opacity-75">
            <Link href="/dashboard">Customer</Link>
            <Link href="/vendor/dashboard">Vendor</Link>
            <Link href="/admin/dashboard">Admin</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
