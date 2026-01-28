'use client';

import { useTenantMemberships } from '@/hooks/use-tenants';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, Crown, Shield, User, MoreVertical } from 'lucide-react';
import type { TenantMembership } from '@/types';

interface TenantMembersListProps {
  tenantId: string;
  onInvite?: () => void;
}

const roleIcons: Record<string, typeof Crown> = {
  owner: Crown,
  admin: Shield,
  member: User,
};

const roleColors: Record<string, string> = {
  owner: 'text-yellow-600 bg-yellow-50',
  admin: 'text-blue-600 bg-blue-50',
  member: 'text-gray-600 bg-gray-50',
};

export function TenantMembersList({ tenantId, onInvite }: TenantMembersListProps) {
  const { data: memberships, isLoading } = useTenantMemberships(tenantId);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="h-10 w-10 bg-gray-200 rounded-full" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-1/4" />
                  <div className="h-3 bg-gray-200 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          Team Members
        </CardTitle>
        {onInvite && (
          <Button size="sm" onClick={onInvite}>
            Invite Member
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {!memberships || memberships.length === 0 ? (
          <div className="text-center py-8">
            <Users className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No team members yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {memberships.map((membership) => {
              const RoleIcon = roleIcons[membership.role] || User;
              return (
                <div
                  key={membership.id}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <User className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">User #{membership.user_id}</p>
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${roleColors[membership.role]}`}
                        >
                          <RoleIcon className="h-3 w-3" />
                          {membership.role}
                        </span>
                        {!membership.invitation_accepted && (
                          <span className="text-xs text-yellow-600">Pending</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
