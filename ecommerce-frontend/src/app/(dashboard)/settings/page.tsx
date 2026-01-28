'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useUserProfile, useUpdateProfile, useChangePassword } from '@/hooks/use-users';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { User, Lock, Bell, Shield } from 'lucide-react';

const profileSchema = z.object({
  first_name: z.string().optional(),
  last_name: z.string().optional(),
});

const passwordSchema = z
  .object({
    old_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'New password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

type ProfileFormData = z.infer<typeof profileSchema>;
type PasswordFormData = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { data: profile, isLoading } = useUserProfile();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const [activeTab, setActiveTab] = useState('profile');

  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    values: {
      first_name: profile?.first_name || '',
      last_name: profile?.last_name || '',
    },
  });

  const passwordForm = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const handleProfileUpdate = async (data: ProfileFormData) => {
    await updateProfile.mutateAsync(data);
  };

  const handlePasswordChange = async (data: PasswordFormData) => {
    await changePassword.mutateAsync({
      old_password: data.old_password,
      new_password: data.new_password,
    });
    passwordForm.reset();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy', icon: Shield },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Manage your account settings</p>
      </div>

      <div className="flex gap-6">
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1">
          {activeTab === 'profile' && (
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
              </CardHeader>
              <CardContent>
                <form
                  onSubmit={profileForm.handleSubmit(handleProfileUpdate)}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="First Name"
                      {...profileForm.register('first_name')}
                      error={profileForm.formState.errors.first_name?.message}
                    />
                    <Input
                      label="Last Name"
                      {...profileForm.register('last_name')}
                      error={profileForm.formState.errors.last_name?.message}
                    />
                  </div>
                  <Button type="submit" isLoading={updateProfile.isPending}>
                    Save Changes
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'security' && (
            <Card>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
              </CardHeader>
              <CardContent>
                <form
                  onSubmit={passwordForm.handleSubmit(handlePasswordChange)}
                  className="space-y-4"
                >
                  <Input
                    type="password"
                    label="Current Password"
                    {...passwordForm.register('old_password')}
                    error={passwordForm.formState.errors.old_password?.message}
                  />
                  <Input
                    type="password"
                    label="New Password"
                    {...passwordForm.register('new_password')}
                    error={passwordForm.formState.errors.new_password?.message}
                  />
                  <Input
                    type="password"
                    label="Confirm New Password"
                    {...passwordForm.register('confirm_password')}
                    error={passwordForm.formState.errors.confirm_password?.message}
                  />
                  <Button type="submit" isLoading={changePassword.isPending}>
                    Update Password
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Email Notifications</p>
                      <p className="text-sm text-gray-500">
                        Receive email updates about your account
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      className="h-5 w-5 rounded border-gray-300"
                      defaultChecked
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Push Notifications</p>
                      <p className="text-sm text-gray-500">
                        Receive push notifications in your browser
                      </p>
                    </div>
                    <input type="checkbox" className="h-5 w-5 rounded border-gray-300" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'privacy' && (
            <Card>
              <CardHeader>
                <CardTitle>Privacy Settings</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Profile Visibility</p>
                      <p className="text-sm text-gray-500">Control who can see your profile</p>
                    </div>
                    <select className="rounded-lg border border-gray-300 px-3 py-2">
                      <option>Public</option>
                      <option>Private</option>
                      <option>Team Only</option>
                    </select>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
