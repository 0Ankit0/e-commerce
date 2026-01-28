'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreatePaymentIntent, useCreateSetupIntent } from '@/hooks/use-finances';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CreditCard, Lock } from 'lucide-react';

const paymentSchema = z.object({
  amount: z.number().min(1, 'Amount must be at least 1'),
  currency: z.string(),
});

type PaymentFormData = {
  amount: number;
  currency: string;
};

interface StripePaymentFormProps {
  mode: 'payment' | 'setup';
  amount?: number;
  onSuccess?: (result: { clientSecret: string }) => void;
  onError?: (error: Error) => void;
}

export function StripePaymentForm({
  mode = 'payment',
  amount,
  onSuccess,
  onError,
}: StripePaymentFormProps) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const createPaymentIntent = useCreatePaymentIntent();
  const createSetupIntent = useCreateSetupIntent();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: { amount: amount || 0, currency: 'usd' },
  });

  const onSubmit = async (data: PaymentFormData) => {
    try {
      if (mode === 'payment') {
        const result = await createPaymentIntent.mutateAsync({
          amount: data.amount * 100, // Convert to cents
          currency: data.currency,
        });
        setClientSecret(result.client_secret);
        onSuccess?.({ clientSecret: result.client_secret });
      } else {
        const result = await createSetupIntent.mutateAsync();
        setClientSecret(result.client_secret);
        onSuccess?.({ clientSecret: result.client_secret });
      }
    } catch (error) {
      onError?.(error as Error);
    }
  };

  const isLoading = createPaymentIntent.isPending || createSetupIntent.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="h-5 w-5" />
          {mode === 'payment' ? 'Make Payment' : 'Add Payment Method'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!clientSecret ? (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {mode === 'payment' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  {...register('amount', { valueAsNumber: true })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
                {errors.amount && (
                  <p className="mt-1 text-sm text-red-600">{errors.amount.message}</p>
                )}
              </div>
            )}

            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600 flex items-center gap-2">
                <Lock className="h-4 w-4" />
                Your payment information is secure and encrypted.
              </p>
            </div>

            <Button type="submit" className="w-full" isLoading={isLoading}>
              {mode === 'payment' ? 'Continue to Payment' : 'Add Payment Method'}
            </Button>
          </form>
        ) : (
          <div className="text-center py-8">
            <p className="text-green-600 mb-4">Payment intent created!</p>
            <p className="text-sm text-gray-500">
              Client secret ready for Stripe Elements integration.
            </p>
            {/* Stripe Elements would be mounted here */}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
