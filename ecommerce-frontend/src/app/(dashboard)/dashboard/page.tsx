'use client';

import { useAuthStore } from '@/store/auth-store';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Users, CreditCard, Bell, TrendingUp } from 'lucide-react';

const stats = [
  { name: 'Total Users', value: '1,234', icon: Users, change: '+12%', trend: 'up' },
  { name: 'Revenue', value: '$45,678', icon: CreditCard, change: '+8%', trend: 'up' },
  { name: 'Notifications', value: '23', icon: Bell, change: '+5', trend: 'up' },
  { name: 'Growth', value: '34%', icon: TrendingUp, change: '+2%', trend: 'up' },
];

export default function DashboardPage() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">
          Welcome back{user?.first_name ? `, ${user.first_name}` : ''}!
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{stat.name}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
                <div className="h-12 w-12 rounded-lg bg-blue-50 flex items-center justify-center">
                  <stat.icon className="h-6 w-6 text-blue-600" />
                </div>
              </div>
              <p className="mt-2 text-sm text-green-600">{stat.change} from last month</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50">
                  <div className="h-10 w-10 rounded-full bg-gray-100" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Activity {i}</p>
                    <p className="text-sm text-gray-500">Description of activity</p>
                  </div>
                  <span className="text-xs text-gray-400">2h ago</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <button className="p-4 rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-colors text-left">
                <Users className="h-6 w-6 text-blue-600 mb-2" />
                <p className="font-medium text-gray-900">Manage Users</p>
                <p className="text-sm text-gray-500">View and edit users</p>
              </button>
              <button className="p-4 rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-colors text-left">
                <CreditCard className="h-6 w-6 text-blue-600 mb-2" />
                <p className="font-medium text-gray-900">Billing</p>
                <p className="text-sm text-gray-500">Manage subscriptions</p>
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
