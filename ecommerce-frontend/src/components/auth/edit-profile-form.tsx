'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/store/auth-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { User, CheckCircle } from 'lucide-react';
import apiClient from '@/lib/api-client';

const editProfileSchema = z.object({
  first_name: z.string().max(50, 'First name is too long').optional(),
  last_name: z.string().max(50, 'Last name is too long').optional(),
});

type EditProfileFormData = z.infer<typeof editProfileSchema>;

export function EditProfileForm() {
  const { user, setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<EditProfileFormData>({
    resolver: zodResolver(editProfileSchema),
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
    },
  });

  useEffect(() => {
    if (user) {
      reset({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
      });
    }
  }, [user, reset]);

  const onSubmit = async (data: EditProfileFormData) => {
    setIsLoading(true);
    setError('');
    setSuccess(false);
    try {
      const response = await apiClient.patch('/users/me/', data);
      if (user) {
        setUser({ ...user, ...response.data });
      }
      setSuccess(true);
    } catch (err) {
      setError('Failed to update profile. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5" />
          Personal Information
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
              Profile updated successfully!
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              id="first_name"
              label="First Name"
              placeholder="Enter first name"
              {...register('first_name')}
              error={errors.first_name?.message}
            />
            <Input
              id="last_name"
              label="Last Name"
              placeholder="Enter last name"
              {...register('last_name')}
              error={errors.last_name?.message}
            />
          </div>
          <Button type="submit" isLoading={isLoading}>
            Update Profile
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
