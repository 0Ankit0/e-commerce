'use client';

import { useState } from 'react';
import { useTenants, useCreateTenant, useSwitchTenant } from '@/hooks/use-tenants';
import { useAuthStore } from '@/store/auth-store';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Building2, Plus, Check } from 'lucide-react';

export default function TenantsPage() {
  const { data, isLoading } = useTenants();
  const createTenant = useCreateTenant();
  const switchTenant = useSwitchTenant();
  const { tenant: currentTenant } = useAuthStore();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTenantName, setNewTenantName] = useState('');

  const handleCreateTenant = async () => {
    if (!newTenantName.trim()) return;
    await createTenant.mutateAsync({ name: newTenantName, type: 'organization' });
    setNewTenantName('');
    setShowCreateForm(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const tenants = data?.results || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Organizations</h1>
          <p className="text-gray-500">Manage your organizations and teams</p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Organization
        </Button>
      </div>

      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create Organization</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Input
                placeholder="Organization name"
                value={newTenantName}
                onChange={(e) => setNewTenantName(e.target.value)}
              />
              <Button onClick={handleCreateTenant} isLoading={createTenant.isPending}>
                Create
              </Button>
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tenants.map((tenant) => (
          <Card
            key={tenant.id}
            className={`cursor-pointer transition-all ${
              currentTenant?.id === tenant.id ? 'ring-2 ring-blue-500' : 'hover:border-blue-500'
            }`}
            onClick={() => switchTenant.mutate(tenant)}
          >
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Building2 className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{tenant.name}</p>
                    <p className="text-sm text-gray-500 capitalize">{tenant.type}</p>
                  </div>
                </div>
                {currentTenant?.id === tenant.id && (
                  <div className="h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
