import type {
  InitiatePaymentRequest,
  InitiatePaymentResponse,
  PaymentProvider,
  PaymentStatus,
  VerifyPaymentRequest,
  VerifyPaymentResponse,
} from '@/types';
import type { PendingCheckoutPayment } from './checkout-payment';

export const CORE_CHECKOUT_METHODS = ['cod', 'wallet'] as const;
export const GATEWAY_CHECKOUT_METHODS = ['khalti', 'esewa', 'stripe', 'paypal', 'razorpay'] as const;

export type GatewayCheckoutMethod = (typeof GATEWAY_CHECKOUT_METHODS)[number];
export type CheckoutMethod = GatewayCheckoutMethod | (typeof CORE_CHECKOUT_METHODS)[number];

const CALLBACK_TIMEOUT_MS = 30 * 60 * 1000;
const PROCESSED_CALLBACK_KEYS = 'processed_checkout_callbacks';

export function isGatewayCheckoutMethod(method: string): method is GatewayCheckoutMethod {
  return GATEWAY_CHECKOUT_METHODS.includes(method as GatewayCheckoutMethod);
}

export function createPaymentInitiationPayload(input: {
  method: GatewayCheckoutMethod;
  total: number;
  callbackUrl: string;
  websiteUrl: string;
  purchaseOrderId: string;
  customerName?: string;
  customerEmail?: string;
  customerPhone?: string;
}): InitiatePaymentRequest {
  return {
    provider: input.method,
    amount: input.method === 'esewa' ? Math.round(input.total) : Math.round(input.total * 100),
    purchase_order_id: input.purchaseOrderId,
    purchase_order_name: `Checkout ${input.purchaseOrderId}`,
    return_url: input.callbackUrl,
    website_url: input.websiteUrl,
    customer_name: input.customerName,
    customer_email: input.customerEmail,
    customer_phone: input.customerPhone,
  };
}

export function extractGatewayHandoff(initiated: InitiatePaymentResponse):
  | { type: 'redirect'; url: string }
  | { type: 'form'; action: string; fields: Record<string, unknown> } {
  if (initiated.provider === 'esewa') {
    const payload = initiated.extra ?? {};
    const formAction = typeof payload.form_action === 'string' ? payload.form_action : null;
    const formFields =
      payload.form_fields && typeof payload.form_fields === 'object' && !Array.isArray(payload.form_fields)
        ? (payload.form_fields as Record<string, unknown>)
        : null;

    if (!formAction || !formFields) {
      throw new Error('The backend did not return the eSewa handoff form.');
    }

    return { type: 'form', action: formAction, fields: formFields };
  }

  if (!initiated.payment_url) {
    throw new Error(`The backend did not return a ${initiated.provider} payment URL.`);
  }

  return { type: 'redirect', url: initiated.payment_url };
}

function getParam(searchParams: URLSearchParams, keys: string[]) {
  for (const key of keys) {
    const value = searchParams.get(key);
    if (value) return value;
  }
  return undefined;
}

export function createVerifyPayload(input: {
  searchParams: URLSearchParams;
  pendingCheckout: PendingCheckoutPayment | null;
}): { provider: PaymentProvider; verifyPayload: VerifyPaymentRequest; missingFields: string[]; transactionId?: string } {
  const provider =
    (getParam(input.searchParams, ['provider']) as PaymentProvider | null) ??
    (isGatewayCheckoutMethod(input.pendingCheckout?.paymentMethod ?? '')
      ? input.pendingCheckout?.paymentMethod
      : null) ??
    'khalti';

  const queryTransactionId = getParam(input.searchParams, [
    'transaction_id',
    'transactionId',
    'txn_id',
    'payment_id',
    'paymentId',
    'tx_ref',
  ]);
  const transactionId = queryTransactionId ?? input.pendingCheckout?.transactionId;

  const verifyPayload: VerifyPaymentRequest = { provider };
  const missingFields: string[] = [];

  if (provider === 'khalti') {
    const pidx = getParam(input.searchParams, ['pidx', 'token']);
    if (!pidx) missingFields.push('pidx');
    else verifyPayload.pidx = pidx;
  }

  if (provider === 'esewa') {
    const data = getParam(input.searchParams, ['data']);
    const oid = getParam(input.searchParams, ['oid', 'purchase_order_id', 'order_id']);
    const refId = getParam(input.searchParams, ['refId', 'ref_id', 'reference_id']);
    if (data) verifyPayload.data = data;
    else if (oid && refId) {
      verifyPayload.oid = oid;
      verifyPayload.refId = refId;
    } else {
      missingFields.push('data or oid+refId');
    }
  }

  if (provider === 'razorpay') {
    const paymentId = getParam(input.searchParams, ['razorpay_payment_id', 'payment_id']);
    const orderId = getParam(input.searchParams, ['razorpay_order_id', 'order_id']);
    const signature = getParam(input.searchParams, ['razorpay_signature', 'signature']);
    if (!paymentId) missingFields.push('razorpay_payment_id');
    if (!orderId) missingFields.push('razorpay_order_id');
    if (!signature) missingFields.push('razorpay_signature');
    if (paymentId && orderId && signature) {
      verifyPayload.pidx = paymentId;
      verifyPayload.oid = orderId;
      verifyPayload.refId = signature;
    }
  }

  if ((provider === 'stripe' || provider === 'paypal') && !transactionId) {
    missingFields.push('transaction_id');
  }

  if (transactionId) {
    verifyPayload.transaction_id = transactionId;
  }

  return { provider, verifyPayload, missingFields, transactionId };
}

export function getPendingCheckoutState(pendingCheckout: PendingCheckoutPayment | null):
  | { ok: true }
  | { ok: false; reason: string } {
  if (!pendingCheckout) {
    return { ok: false, reason: 'No checkout session was found. Start checkout again.' };
  }

  const createdAt = Date.parse(pendingCheckout.createdAt);
  if (!Number.isFinite(createdAt)) {
    return { ok: false, reason: 'Checkout session is invalid. Start checkout again.' };
  }

  if (Date.now() - createdAt > CALLBACK_TIMEOUT_MS) {
    return { ok: false, reason: 'Checkout session expired before callback completed. Please place the order again.' };
  }

  return { ok: true };
}

function canUseSessionStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

export function hasProcessedCallback(key: string) {
  if (!canUseSessionStorage()) return false;
  const raw = window.sessionStorage.getItem(PROCESSED_CALLBACK_KEYS);
  if (!raw) return false;
  const values = raw.split(',').filter(Boolean);
  return values.includes(key);
}

export function markProcessedCallback(key: string) {
  if (!canUseSessionStorage()) return;
  const raw = window.sessionStorage.getItem(PROCESSED_CALLBACK_KEYS);
  const values = new Set((raw ?? '').split(',').filter(Boolean));
  values.add(key);
  window.sessionStorage.setItem(PROCESSED_CALLBACK_KEYS, Array.from(values).slice(-40).join(','));
}

export function toCallbackKey(provider: PaymentProvider, transactionId?: string) {
  return `${provider}:${transactionId ?? 'unknown'}`;
}

export function resolveCallbackOutcome(result: VerifyPaymentResponse): {
  state: 'success' | 'error' | 'refund-ready';
  message: string;
  clearPending: boolean;
} {
  if (result.status === 'completed') {
    if (result.extra?.refund_ready === true) {
      return { state: 'refund-ready', message: 'Payment completed. This transaction is marked refund-ready.', clearPending: false };
    }
    return { state: 'success', message: 'Payment completed successfully.', clearPending: false };
  }

  if (result.status === 'refunded') {
    return { state: 'refund-ready', message: 'Payment is already refunded or ready for refund follow-up.', clearPending: true };
  }

  if (result.status === 'cancelled') {
    return { state: 'error', message: 'Payment was cancelled. You can retry checkout.', clearPending: true };
  }

  if (result.status === 'failed') {
    return { state: 'error', message: 'Payment failed. Please try again or use another method.', clearPending: true };
  }

  return { state: 'error', message: `Payment status: ${result.status}. Please wait and retry verification.`, clearPending: false };
}

export function isTerminalStatus(status: PaymentStatus) {
  return status === 'completed' || status === 'failed' || status === 'cancelled' || status === 'refunded';
}
