'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Lock, CheckCircle } from 'lucide-react';
import apiClient from '@/lib/api-client';

const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;

export function ChangePasswordForm() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });

  const onSubmit = async (data: ChangePasswordFormData) => {
    setIsLoading(true);
    setError('');
    setSuccess(false);
    try {
      await apiClient.post('/auth/password-change/', {
        old_password: data.currentPassword,
        new_password: data.newPassword,
      });
      setSuccess(true);
      reset();
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError('Current password is incorrect.');
      } else {
        setError('Failed to change password. Please try again.');
      }
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="h-5 w-5" />
          Change Password
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 text-sm text-green-600 bg-green-50 rounded-lg flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Password changed successfully!
            </div>
          )}
          <Input
            id="currentPassword"
            type="password"
            label="Current Password"
            placeholder="Enter current password"
            {...register('currentPassword')}
            error={errors.currentPassword?.message}
          />
          <Input
            id="newPassword"
            type="password"
            label="New Password"
            placeholder="Minimum 8 characters"
            {...register('newPassword')}
            error={errors.newPassword?.message}
          />
          <Input
            id="confirmPassword"
            type="password"
            label="Confirm New Password"
            placeholder="Confirm new password"
            {...register('confirmPassword')}
            error={errors.confirmPassword?.message}
          />
          <Button type="submit" isLoading={isLoading}>
            Change Password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
