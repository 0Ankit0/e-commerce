'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Users, CreditCard, Bell, Settings, Building2, FileText, Sparkles, User } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'Tenants', href: '/tenants', icon: Building2 },
  { name: 'AI Ideas', href: '/ai-ideas', icon: Sparkles },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Finances', href: '/finances', icon: CreditCard },
  { name: 'Notifications', href: '/notifications', icon: Bell },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-10 w-64 bg-white border-r border-gray-200">
      <div className="flex h-16 items-center justify-center border-b border-gray-200">
        <Link href="/dashboard" className="text-xl font-bold text-blue-600">
          E-Commerce
        </Link>
      </div>
      <nav className="flex flex-col gap-1 p-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
