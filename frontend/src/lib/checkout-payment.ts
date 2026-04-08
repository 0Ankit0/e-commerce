'use client';

import type { PaymentProvider } from '@/types';

const PENDING_CHECKOUT_PAYMENT_KEY = 'pending_checkout_payment';

export interface PendingCheckoutPayment {
  addressId: string;
  paymentMethod: Extract<PaymentProvider, 'khalti' | 'esewa' | 'razorpay' | 'stripe' | 'paypal'>;
  quoteFingerprint: string;
  notes: string;
  transactionId: string;
  purchaseOrderId: string;
  createdAt: string;
}

function hasSessionStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

export function buildPaymentCallbackUrl(
  provider: Extract<PaymentProvider, 'khalti' | 'esewa' | 'razorpay' | 'stripe' | 'paypal'>
) {
  if (typeof window === 'undefined') {
    return '';
  }
  return `${window.location.origin}/payment-callback?provider=${provider}`;
}

export function savePendingCheckoutPayment(payload: PendingCheckoutPayment) {
  if (!hasSessionStorage()) {
    return;
  }
  window.sessionStorage.setItem(PENDING_CHECKOUT_PAYMENT_KEY, JSON.stringify(payload));
}

export function getPendingCheckoutPayment(): PendingCheckoutPayment | null {
  if (!hasSessionStorage()) {
    return null;
  }

  const raw = window.sessionStorage.getItem(PENDING_CHECKOUT_PAYMENT_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as PendingCheckoutPayment;
  } catch {
    window.sessionStorage.removeItem(PENDING_CHECKOUT_PAYMENT_KEY);
    return null;
  }
}

export function clearPendingCheckoutPayment() {
  if (!hasSessionStorage()) {
    return;
  }
  window.sessionStorage.removeItem(PENDING_CHECKOUT_PAYMENT_KEY);
}

export function submitEsewaPaymentForm(action: string, fields: Record<string, unknown>) {
  if (typeof document === 'undefined') {
    throw new Error('Payment handoff is only available in the browser.');
  }

  const form = document.createElement('form');
  form.method = 'POST';
  form.action = action;
  form.style.display = 'none';

  Object.entries(fields).forEach(([key, value]) => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = key;
    input.value = value == null ? '' : String(value);
    form.appendChild(input);
  });

  document.body.appendChild(form);
  form.submit();
}
