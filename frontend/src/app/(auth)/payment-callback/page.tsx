'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useVerifyPayment } from '@/hooks/use-finances';
import { useCreateOrder } from '@/hooks/use-commerce';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';
import type { PaymentProvider } from '@/types';
import { clearPendingCheckoutPayment, getPendingCheckoutPayment } from '@/lib/checkout-payment';

/**
 * Handles payment provider callbacks.
 *
 * Khalti redirect params: ?status=Completed&transaction_id=...&tidx=...&amount=...&mobile=...&purchase_order_id=...&purchase_order_name=...&pidx=...
 * eSewa redirect params:  ?data=BASE64_ENCODED_RESPONSE&provider=esewa
 * Generic:                ?provider=stripe|paypal|razorpay&transaction_id=...
 */
function PaymentCallbackInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const hasStartedRef = useRef(false);
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [redirectPath, setRedirectPath] = useState('/finances');

  const verifyPayment = useVerifyPayment();
  const createOrder = useCreateOrder();

  useEffect(() => {
    if (hasStartedRef.current) {
      return;
    }
    hasStartedRef.current = true;

    async function finalizePayment() {
      const provider = (searchParams.get('provider') || 'khalti') as PaymentProvider;
      const pidx =
        searchParams.get('pidx') ??
        searchParams.get('razorpay_payment_id') ??
        undefined;
      const data = searchParams.get('data') ?? undefined;
      const oid = searchParams.get('oid') ?? searchParams.get('razorpay_order_id') ?? undefined;
      const refId =
        searchParams.get('refId') ?? searchParams.get('razorpay_signature') ?? undefined;
      const pendingCheckout = getPendingCheckoutPayment();

      if (!pidx && !data) {
        setStatus('error');
        setMessage('Missing payment verification data in URL.');
        return;
      }

      try {
        const result = await verifyPayment.mutateAsync({
          provider,
          pidx,
          data,
          transaction_id: pendingCheckout?.transactionId,
          oid,
          refId,
        });

        if (result.status !== 'completed') {
          if (result.status === 'failed' || result.status === 'cancelled') {
            clearPendingCheckoutPayment();
          }
          setStatus('error');
          setMessage(`Payment status: ${result.status}. Please try again or contact support.`);
          return;
        }

        if (pendingCheckout && pendingCheckout.paymentMethod === provider) {
          try {
            const response = await createOrder.mutateAsync({
              addressId: pendingCheckout.addressId,
              paymentMethod: pendingCheckout.paymentMethod,
              paymentTransactionId: result.transaction_id,
              quoteFingerprint: pendingCheckout.quoteFingerprint,
              notes: pendingCheckout.notes,
            });
            const order = response.order as { id: string };
            clearPendingCheckoutPayment();
            setRedirectPath(`/orders/${order.id}`);
            setStatus('success');
            setMessage('Payment verified and your order has been placed successfully.');
            setTimeout(() => router.push(`/orders/${order.id}`), 2500);
            return;
          } catch {
            setStatus('error');
            setMessage(
              'Payment was verified, but the order could not be finalized automatically. Please open your orders or payments page and retry once.'
            );
            return;
          }
        }

        setStatus('success');
        setMessage('Payment completed successfully.');
        setTimeout(() => router.push('/finances'), 2500);
      } catch {
        setStatus('error');
        setMessage(
          'Payment verification failed. Please check your transactions or contact support.'
        );
      }
    }

    void finalizePayment();
  }, [createOrder, router, searchParams, verifyPayment]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Payment Verification</h1>

        {status === 'loading' && (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
            <p className="text-gray-500">Verifying your payment…</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <CheckCircle className="h-14 w-14 text-green-500 mx-auto" />
            <p className="text-gray-700 font-medium">{message}</p>
            <p className="text-sm text-gray-400">Redirecting to your next screen…</p>
            <Link href={redirectPath} className="text-sm text-blue-600 hover:underline">
              Continue
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <XCircle className="h-14 w-14 text-red-500 mx-auto" />
            <p className="text-gray-700">{message}</p>
            <div className="flex flex-col gap-2">
              <Link href="/finances" className="text-sm text-blue-600 hover:underline">
                View Payments
              </Link>
              <Link href="/dashboard" className="text-sm text-gray-400 hover:underline">
                Go to Dashboard
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PaymentCallbackPage() {
  return (
    <Suspense>
      <PaymentCallbackInner />
    </Suspense>
  );
}
