'use client';

import { RoleRoute } from '@/components/auth/role-route';
import { AdminSidebar } from '@/components/layout/admin-sidebar';
import { Header } from '@/components/layout/header';

export default function AdminDashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleRoute portal="admin">
      <div className="dashboard-stage min-h-screen">
        <AdminSidebar />
        <Header />
        <main className="px-4 pb-8 pt-20 lg:ml-72 lg:px-8">{children}</main>
      </div>
    </RoleRoute>
  );
}
