'use client';

import { RoleRoute } from '@/components/auth/role-route';
import { Header } from '@/components/layout/header';
import { PortalSidebar } from '@/components/layout/portal-sidebar';

export default function AgentDashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleRoute portal="agent">
      <div className="dashboard-stage min-h-screen">
        <PortalSidebar portal="agent" />
        <Header />
        <main className="px-4 pb-8 pt-20 lg:ml-72 lg:px-8">{children}</main>
      </div>
    </RoleRoute>
  );
}
