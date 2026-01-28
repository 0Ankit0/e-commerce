'use client';

import { useSubscription, usePaymentMethods, useTransactions } from '@/hooks/use-finances';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CreditCard, Plus, Calendar, DollarSign } from 'lucide-react';

export default function FinancesPage() {
  const { data: subscription, isLoading: loadingSubscription } = useSubscription();
  const { data: paymentMethods, isLoading: loadingPaymentMethods } = usePaymentMethods();
  const { data: transactions, isLoading: loadingTransactions } = useTransactions();

  const isLoading = loadingSubscription || loadingPaymentMethods || loadingTransactions;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing & Finances</h1>
        <p className="text-gray-500">Manage your subscription and payment methods</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Subscription
            </CardTitle>
          </CardHeader>
          <CardContent>
            {subscription ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Status</span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      subscription.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {subscription.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Current Period</span>
                  <span className="text-gray-900">
                    {new Date(subscription.current_period_start).toLocaleDateString()} -{' '}
                    {new Date(subscription.current_period_end).toLocaleDateString()}
                  </span>
                </div>
                <Button variant="outline" className="w-full">
                  Manage Subscription
                </Button>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">No active subscription</p>
                <Button>Subscribe Now</Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Payment Methods
            </CardTitle>
            <Button variant="outline" size="sm">
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </CardHeader>
          <CardContent>
            {paymentMethods && paymentMethods.length > 0 ? (
              <div className="space-y-3">
                {paymentMethods.map((method) => (
                  <div
                    key={method.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-gray-200"
                  >
                    <CreditCard className="h-5 w-5 text-gray-500" />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">
                        {method.card?.brand} •••• {method.card?.last4}
                      </p>
                      <p className="text-sm text-gray-500">
                        Expires {method.card?.exp_month}/{method.card?.exp_year}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <CreditCard className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No payment methods added</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Recent Transactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {transactions && transactions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b border-gray-200">
                    <th className="pb-3 font-medium text-gray-500">Date</th>
                    <th className="pb-3 font-medium text-gray-500">Description</th>
                    <th className="pb-3 font-medium text-gray-500">Amount</th>
                    <th className="pb-3 font-medium text-gray-500">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {/* Transactions would be mapped here */}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <DollarSign className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No transactions yet</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
