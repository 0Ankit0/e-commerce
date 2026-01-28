'use client';

import { useSubscription, useCancelSubscription } from '@/hooks/use-finances';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar, AlertCircle, CheckCircle } from 'lucide-react';

interface SubscriptionCardProps {
  onManage?: () => void;
}

export function SubscriptionCard({ onManage }: SubscriptionCardProps) {
  const { data: subscription, isLoading } = useSubscription();
  const cancelSubscription = useCancelSubscription();

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/2" />
            <div className="h-4 bg-gray-200 rounded w-3/4" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!subscription) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Active Subscription</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500 mb-4">
            You don&apos;t have an active subscription. Subscribe to unlock all features.
          </p>
          <Button onClick={onManage}>View Plans</Button>
        </CardContent>
      </Card>
    );
  }

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    trialing: 'bg-blue-100 text-blue-800',
    past_due: 'bg-yellow-100 text-yellow-800',
    canceled: 'bg-red-100 text-red-800',
    unpaid: 'bg-red-100 text-red-800',
  };

  const StatusIcon = subscription.status === 'active' ? CheckCircle : AlertCircle;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Subscription</CardTitle>
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[subscription.status] || 'bg-gray-100 text-gray-800'}`}
          >
            {subscription.status}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 text-gray-600">
          <StatusIcon className="h-5 w-5" />
          <span>Your subscription is {subscription.status}</span>
        </div>

        <div className="flex items-center gap-2 text-gray-600">
          <Calendar className="h-5 w-5" />
          <span>
            Current period: {new Date(subscription.current_period_start).toLocaleDateString()} -{' '}
            {new Date(subscription.current_period_end).toLocaleDateString()}
          </span>
        </div>

        {subscription.trial_end && new Date(subscription.trial_end) > new Date() && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              Trial ends on {new Date(subscription.trial_end).toLocaleDateString()}
            </p>
          </div>
        )}
      </CardContent>
      <CardFooter className="flex gap-4">
        <Button variant="outline" onClick={onManage}>
          Manage Subscription
        </Button>
        {subscription.status === 'active' && (
          <Button
            variant="destructive"
            onClick={() => cancelSubscription.mutate()}
            isLoading={cancelSubscription.isPending}
          >
            Cancel
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
