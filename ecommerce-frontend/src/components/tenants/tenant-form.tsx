'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateTenant, useUpdateTenant } from '@/hooks/use-tenants';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { Tenant } from '@/types';

const tenantSchema = z.object({
  name: z.string().min(1, 'Organization name is required').max(100),
  type: z.enum(['organization', 'individual']),
});

type TenantFormData = z.infer<typeof tenantSchema>;

interface TenantFormProps {
  tenant?: Tenant;
  onSuccess?: (tenant: Tenant) => void;
  onCancel?: () => void;
}

export function TenantForm({ tenant, onSuccess, onCancel }: TenantFormProps) {
  const createTenant = useCreateTenant();
  const updateTenant = useUpdateTenant();
  const isEditing = !!tenant;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TenantFormData>({
    resolver: zodResolver(tenantSchema),
    defaultValues: {
      name: tenant?.name || '',
      type: tenant?.type || 'organization',
    },
  });

  const onSubmit = async (data: TenantFormData) => {
    try {
      let result: Tenant;
      if (isEditing) {
        result = await updateTenant.mutateAsync({ id: tenant.id, data });
      } else {
        result = await createTenant.mutateAsync(data);
      }
      onSuccess?.(result);
    } catch (error) {
      console.error('Error saving tenant:', error);
    }
  };

  const isLoading = createTenant.isPending || updateTenant.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEditing ? 'Edit Organization' : 'Create Organization'}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Organization Name"
            {...register('name')}
            error={errors.name?.message}
            placeholder="Enter organization name"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Organization Type
            </label>
            <select
              {...register('type')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="organization">Organization</option>
              <option value="individual">Individual</option>
            </select>
            {errors.type && <p className="mt-1 text-sm text-red-600">{errors.type.message}</p>}
          </div>

          <div className="flex gap-4">
            <Button type="submit" isLoading={isLoading}>
              {isEditing ? 'Save Changes' : 'Create Organization'}
            </Button>
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
