import type { LucideIcon } from 'lucide-react';
import {
  Bell,
  BarChart3,
  Boxes,
  ClipboardList,
  CreditCard,
  Gauge,
  Heart,
  LayoutDashboard,
  PanelsTopLeft,
  Radar,
  Receipt,
  ScrollText,
  Settings,
  Shield,
  ShoppingBag,
  ShoppingCart,
  Truck,
  Users,
  Warehouse,
} from 'lucide-react';
import type { CapabilitySummary, User } from '@/types';

export type PortalKey = 'customer' | 'vendor' | 'agent' | 'admin';

export interface PortalNavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  feature?: string;
}

export interface PortalDefinition {
  key: PortalKey;
  label: string;
  description: string;
  home: string;
  accentClass: string;
  navigation: PortalNavItem[];
}

function normalizeRole(role: string) {
  return role.toLowerCase().trim();
}

export function getUserPortals(user: User | null | undefined): PortalKey[] {
  if (!user) return [];

  const normalizedRoles = new Set((user.roles ?? []).map(normalizeRole));
  const portals: PortalKey[] = ['customer'];

  if (normalizedRoles.has('vendor') || normalizedRoles.has('merchant') || normalizedRoles.has('seller')) {
    portals.push('vendor');
  }

  if (
    normalizedRoles.has('agent') ||
    normalizedRoles.has('delivery_agent') ||
    normalizedRoles.has('logistics_agent') ||
    normalizedRoles.has('hub_operator')
  ) {
    portals.push('agent');
  }

  if (user.is_superuser || normalizedRoles.has('admin') || normalizedRoles.has('superuser')) {
    portals.push('admin');
  }

  return Array.from(new Set(portals));
}

export function canAccessPortal(user: User | null | undefined, portal: PortalKey) {
  return getUserPortals(user).includes(portal);
}

export function getDefaultPortalPath(user: User | null | undefined) {
  const portals = getUserPortals(user);
  if (portals.includes('admin')) return '/admin/dashboard';
  if (portals.includes('vendor')) return '/vendor/dashboard';
  if (portals.includes('agent')) return '/agent/dashboard';
  return '/dashboard';
}

export function getPortalFromPath(pathname: string): PortalKey {
  if (pathname.startsWith('/admin')) return 'admin';
  if (pathname.startsWith('/vendor')) return 'vendor';
  if (pathname.startsWith('/agent')) return 'agent';
  return 'customer';
}

export const PORTAL_DEFINITIONS: Record<PortalKey, PortalDefinition> = {
  customer: {
    key: 'customer',
    label: 'Customer Space',
    description: 'Orders, saves, and account activity',
    home: '/dashboard',
    accentClass: 'from-[#c96d44] via-[#f4d2a8] to-[#f7efe1]',
    navigation: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Cart', href: '/cart', icon: ShoppingCart },
      { label: 'My Orders', href: '/orders', icon: Receipt },
      { label: 'Wishlist', href: '/wishlist', icon: Heart },
      { label: 'Notifications', href: '/notifications', icon: Bell, feature: 'notifications' },
      { label: 'Profile', href: '/profile', icon: Users },
      { label: 'Settings', href: '/settings', icon: Settings },
    ],
  },
  vendor: {
    key: 'vendor',
    label: 'Vendor Desk',
    description: 'Catalog, fulfillment, and payouts',
    home: '/vendor/dashboard',
    accentClass: 'from-[#123f35] via-[#2a7a68] to-[#d9f3eb]',
    navigation: [
      { label: 'Overview', href: '/vendor/dashboard', icon: Gauge },
      { label: 'Products', href: '/vendor/products', icon: PanelsTopLeft },
      { label: 'Inventory', href: '/vendor/inventory', icon: Warehouse },
      { label: 'Orders', href: '/vendor/orders', icon: ClipboardList },
      { label: 'Shipments', href: '/vendor/shipments', icon: Truck },
      { label: 'Payouts', href: '/vendor/payouts', icon: CreditCard },
    ],
  },
  agent: {
    key: 'agent',
    label: 'Agent Console',
    description: 'Assignments, routes, and proof of delivery',
    home: '/agent/dashboard',
    accentClass: 'from-[#13324f] via-[#316fa5] to-[#d9eafb]',
    navigation: [
      { label: 'Overview', href: '/agent/dashboard', icon: Gauge },
      { label: 'Assignments', href: '/agent/assignments', icon: Truck },
      { label: 'Delivery History', href: '/agent/history', icon: ScrollText },
    ],
  },
  admin: {
    key: 'admin',
    label: 'Admin Control',
    description: 'Operations, moderation, and reporting',
    home: '/admin/dashboard',
    accentClass: 'from-[#3c123f] via-[#7c2f74] to-[#f0d6ef]',
    navigation: [
      { label: 'Overview', href: '/admin/dashboard', icon: LayoutDashboard },
      { label: 'Orders', href: '/admin/orders', icon: Receipt },
      { label: 'Line-haul Planner', href: '/admin/line-haul-planner', icon: Truck },
      { label: 'Hub Ops', href: '/admin/hub-operations', icon: Warehouse },
      { label: 'Branch Ops', href: '/admin/branch-operations', icon: Users },
      { label: 'Branch KPI', href: '/admin/branch-dashboard', icon: BarChart3 },
      { label: 'Vendors', href: '/admin/vendors', icon: Users },
      { label: 'Catalog Review', href: '/admin/catalog', icon: Boxes },
      { label: 'Live Feed', href: '/admin/live-feed', icon: Radar },
      { label: 'Reports', href: '/admin/reports', icon: ScrollText },
      { label: 'Content', href: '/admin/content', icon: ShoppingBag },
      { label: 'Security', href: '/admin/security-review', icon: Shield },
      { label: 'Comm Quotas', href: '/admin/communications-quotas', icon: Bell },
      { label: 'Delivery Analytics', href: '/admin/communications-delivery', icon: Bell },
      { label: 'Notification Analytics', href: '/admin/notification-analytics', icon: BarChart3 },
    ],
  },
};

export function getVisiblePortalNavigation(
  portal: PortalKey,
  capabilities?: CapabilitySummary | undefined
) {
  return PORTAL_DEFINITIONS[portal].navigation.filter((item) => {
    if (!item.feature) return true;
    return capabilities?.modules[item.feature] !== false;
  });
}
