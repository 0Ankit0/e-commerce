import { describe, expect, it } from 'vitest';
import type { VerifyPaymentResponse } from '@/types';
import {
  createPaymentInitiationPayload,
  createVerifyPayload,
  getPendingCheckoutState,
  isGatewayCheckoutMethod,
  resolveCallbackOutcome,
} from './checkout-orchestration';

const providers = ['khalti', 'esewa', 'stripe', 'paypal', 'razorpay'] as const;

describe('checkout orchestration', () => {
  it('keeps a gateway detector aligned with supported providers', () => {
    for (const provider of providers) {
      expect(isGatewayCheckoutMethod(provider)).toBe(true);
    }
    expect(isGatewayCheckoutMethod('wallet')).toBe(false);
    expect(isGatewayCheckoutMethod('cod')).toBe(false);
  });

  it('builds payment initiation payloads in one normalized contract', () => {
    const stripe = createPaymentInitiationPayload({
      method: 'stripe',
      total: 123.45,
      callbackUrl: 'https://shop.test/payment-callback?provider=stripe',
      websiteUrl: 'https://shop.test',
      purchaseOrderId: 'CHK-1',
    });
    expect(stripe.amount).toBe(12345);

    const esewa = createPaymentInitiationPayload({
      method: 'esewa',
      total: 123.45,
      callbackUrl: 'https://shop.test/payment-callback?provider=esewa',
      websiteUrl: 'https://shop.test',
      purchaseOrderId: 'CHK-2',
    });
    expect(esewa.amount).toBe(123);
  });

  it('parses callback params with provider-specific fallbacks', () => {
    const esewaParams = new URLSearchParams('provider=esewa&oid=ord-1&ref_id=ref-1&transactionId=tx-1');
    const esewaPayload = createVerifyPayload({
      searchParams: esewaParams,
      pendingCheckout: null,
    });
    expect(esewaPayload.missingFields).toEqual([]);
    expect(esewaPayload.verifyPayload).toMatchObject({ provider: 'esewa', oid: 'ord-1', refId: 'ref-1', transaction_id: 'tx-1' });

    const razorpayParams = new URLSearchParams('provider=razorpay&payment_id=pay-1&order_id=ord-1&signature=sig-1');
    const razorpayPayload = createVerifyPayload({ searchParams: razorpayParams, pendingCheckout: null });
    expect(razorpayPayload.missingFields).toEqual([]);
    expect(razorpayPayload.verifyPayload).toMatchObject({ provider: 'razorpay', pidx: 'pay-1', oid: 'ord-1', refId: 'sig-1' });
  });

  it('flags missing callback fields', () => {
    const payload = createVerifyPayload({
      searchParams: new URLSearchParams('provider=paypal'),
      pendingCheckout: null,
    });
    expect(payload.missingFields).toContain('transaction_id');
  });

  it('rejects timed out checkout sessions', () => {
    const stale = getPendingCheckoutState({
      addressId: 'addr',
      paymentMethod: 'stripe',
      quoteFingerprint: 'q1',
      notes: '',
      transactionId: 'tx',
      purchaseOrderId: 'ord',
      createdAt: '2020-01-01T00:00:00.000Z',
    });
    expect(stale.ok).toBe(false);
  });

  it('covers success/failure/cancel/refund-ready outcomes for every provider', () => {
    const statuses: VerifyPaymentResponse['status'][] = ['completed', 'failed', 'cancelled', 'refunded'];

    for (const provider of providers) {
      for (const status of statuses) {
        const outcome = resolveCallbackOutcome({
          transaction_id: `${provider}-${status}`,
          provider,
          status,
        });

        if (status === 'completed') {
          expect(outcome.state).toBe('success');
        }
        if (status === 'failed' || status === 'cancelled') {
          expect(outcome.state).toBe('error');
        }
        if (status === 'refunded') {
          expect(outcome.state).toBe('refund-ready');
        }
      }
    }

    for (const provider of providers) {
      const outcome = resolveCallbackOutcome({
        transaction_id: `${provider}-ready`,
        provider,
        status: 'completed',
        extra: { refund_ready: true },
      });
      expect(outcome.state).toBe('refund-ready');
    }
  });
});
