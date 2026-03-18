'use client';

import { ProtectedRoute } from '@/components/auth/protected-route';
import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';

export default function UserDashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="dashboard-stage min-h-screen">
        <Sidebar />
        <Header />
        <main className="px-4 pb-8 pt-20 lg:ml-72 lg:px-8">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
