'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, Store } from 'lucide-react';
import { useAuthStore } from '@/store/auth-store';
import { useSystemCapabilities } from '@/hooks/use-system';
import {
  PORTAL_DEFINITIONS,
  type PortalKey,
  getUserPortals,
  getVisiblePortalNavigation,
} from '@/lib/portal';

interface PortalSidebarProps {
  portal: PortalKey;
}

export function PortalSidebar({ portal }: PortalSidebarProps) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const { data: capabilities } = useSystemCapabilities();

  const definition = PORTAL_DEFINITIONS[portal];
  const navigation = getVisiblePortalNavigation(portal, capabilities);
  const portals = getUserPortals(user).filter((item) => item !== portal);

  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-[rgba(25,30,45,0.08)] bg-[#fffaf3] lg:block">
      <div
        className={`border-b border-[rgba(25,30,45,0.08)] bg-gradient-to-br ${definition.accentClass} px-6 py-6 text-[#1d1b18]`}
      >
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[rgba(255,255,255,0.72)] shadow-[0_10px_30px_rgba(25,30,45,0.12)]">
            <Store className="h-5 w-5" />
          </div>
          <div>
            <p className="font-[family:var(--font-display)] text-xl leading-none">Northstar Market</p>
            <p className="mt-1 text-xs uppercase tracking-[0.28em] text-[rgba(29,27,24,0.62)]">
              {definition.label}
            </p>
          </div>
        </div>
        <p className="max-w-[16rem] text-sm text-[rgba(29,27,24,0.72)]">{definition.description}</p>
      </div>

      <div className="flex h-[calc(100%-123px)] flex-col overflow-y-auto px-4 py-5">
        <div>
          <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8b6e57]">
            Active Portal
          </div>
          <nav className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-2xl px-3 py-3 text-sm transition-all ${
                    isActive
                      ? 'bg-[#1d1b18] text-white shadow-[0_10px_30px_rgba(29,27,24,0.18)]'
                      : 'text-[#3e352d] hover:bg-[rgba(29,27,24,0.06)]'
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-6 rounded-[28px] border border-[rgba(25,30,45,0.08)] bg-white p-4 shadow-[0_18px_50px_rgba(25,30,45,0.06)]">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8b6e57]">
            Public Store
          </div>
          <Link
            href="/"
            className="flex items-center justify-between rounded-2xl bg-[#f7efe1] px-4 py-3 text-sm font-medium text-[#43372e] transition-transform hover:-translate-y-0.5"
          >
            Browse storefront
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>

        {portals.length > 0 ? (
          <div className="mt-6">
            <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8b6e57]">
              Other Portals
            </div>
            <div className="space-y-2">
              {portals.map((item) => {
                const portalDef = PORTAL_DEFINITIONS[item];
                return (
                  <Link
                    key={item}
                    href={portalDef.home}
                    className="block rounded-2xl border border-[rgba(25,30,45,0.08)] bg-white px-4 py-3 shadow-[0_14px_40px_rgba(25,30,45,0.05)] transition-transform hover:-translate-y-0.5"
                  >
                    <p className="font-medium text-[#1d1b18]">{portalDef.label}</p>
                    <p className="mt-1 text-xs text-[#7b6657]">{portalDef.description}</p>
                  </Link>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
