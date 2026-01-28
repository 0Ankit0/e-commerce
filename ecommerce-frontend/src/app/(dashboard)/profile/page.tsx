'use client';

import { useAuthStore } from '@/store/auth-store';
import { EditProfileForm } from '@/components/auth/edit-profile-form';
import { ChangePasswordForm } from '@/components/auth/change-password-form';
import { AvatarForm } from '@/components/auth/avatar-form';
import { TwoFactorForm } from '@/components/auth/two-factor-form';

export default function ProfilePage() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile Settings</h1>
        <p className="text-muted-foreground text-gray-500">
          Manage your account settings and preferences.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-6">
          <AvatarForm />
          <EditProfileForm />
        </div>
        <div className="space-y-6">
          <ChangePasswordForm />
          <TwoFactorForm
            isEnabled={user?.otp_enabled}
            onStatusChange={(enabled) => {
              if (user) {
                useAuthStore.getState().setUser({ ...user, otp_enabled: enabled });
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
