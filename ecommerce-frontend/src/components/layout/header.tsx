'use client';

import { Bell, User, LogOut } from 'lucide-react';
import { useAuth } from '@/hooks/use-auth';
import { useAuthStore } from '@/store/auth-store';
import { Button } from '@/components/ui/button';

import { LanguageSwitcher } from './language-switcher';

export function Header() {
  const { logout } = useAuth();
  const { user, tenant } = useAuthStore();

  return (
    <header className="fixed top-0 left-64 right-0 z-10 h-16 bg-white border-b border-gray-200">
      <div className="flex h-full items-center justify-between px-6">
        <div className="flex items-center gap-2">
          {tenant && (
            <span className="text-sm text-gray-500">
              Organization: <span className="font-medium text-gray-900">{tenant.name}</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <LanguageSwitcher />
          <button className="relative p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full" />
          </button>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                <User className="h-4 w-4 text-blue-600" />
              </div>
              <span className="text-sm font-medium text-gray-700">{user?.email || 'User'}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
