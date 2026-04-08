'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, ShieldCheck } from 'lucide-react';
import { useInitiatePayment, usePaymentProviders } from '@/hooks/use-finances';
import {
  useAddressAutocomplete,
  useAddresses,
  useApiErrorMessage,
  useCheckoutQuote,
  useCreateAddress,
  useCreateOrder,
  useSetDefaultAddress,
} from '@/hooks/use-commerce';
import type { PaymentProvider } from '@/types';
import { formatCurrency, titleCaseStatus } from '@/lib/commerce-format';
import {
  buildPaymentCallbackUrl,
  clearPendingCheckoutPayment,
  getPendingCheckoutPayment,
  savePendingCheckoutPayment,
  submitEsewaPaymentForm,
} from '@/lib/checkout-payment';
import {
  createPaymentInitiationPayload,
  extractGatewayHandoff,
  isGatewayCheckoutMethod,
} from '@/lib/checkout-orchestration';
import { useAuthStore } from '@/store/auth-store';

const CORE_PAYMENT_METHODS = [
  { value: 'cod', label: 'Cash on delivery', help: 'Best for quick checkout on the web.' },
  { value: 'wallet', label: 'Wallet', help: 'Uses your in-platform balance if available.' },
];

const SUPPORTED_GATEWAY_PROVIDERS = ['khalti', 'esewa', 'razorpay', 'stripe', 'paypal'] as const;
type SupportedGatewayProvider = (typeof SUPPORTED_GATEWAY_PROVIDERS)[number];

const REDIRECT_GATEWAY_LABELS: Record<Exclude<SupportedGatewayProvider, 'esewa'>, string> = {
  khalti: 'Khalti',
  razorpay: 'Razorpay',
  stripe: 'Stripe',
  paypal: 'PayPal',
};

const GATEWAY_PAYMENT_METHODS: Record<SupportedGatewayProvider, { value: PaymentProvider; label: string; help: string }> = {
  khalti: {
    value: 'khalti',
    label: 'Khalti',
    help: 'Shown only when Khalti is enabled in the backend.',
  },
  esewa: {
    value: 'esewa',
    label: 'eSewa',
    help: 'Shown only when eSewa is enabled in the backend.',
  },
  razorpay: {
    value: 'razorpay',
    label: 'Razorpay',
    help: 'Shown only when Razorpay is enabled in the backend.',
  },
  stripe: {
    value: 'stripe',
    label: 'Stripe',
    help: 'Shown only when Stripe is enabled in the backend.',
  },
  paypal: {
    value: 'paypal',
    label: 'PayPal',
    help: 'Shown only when PayPal is enabled in the backend.',
  },
};

function isSupportedGatewayProvider(provider: string): provider is SupportedGatewayProvider {
  return SUPPORTED_GATEWAY_PROVIDERS.includes(provider as SupportedGatewayProvider);
}

export default function CheckoutPage() {
  const router = useRouter();
  const { getErrorMessage } = useApiErrorMessage();
  const user = useAuthStore((state) => state.user);
  const [paymentMethod, setPaymentMethod] = useState('cod');
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [selectedAddressId, setSelectedAddressId] = useState('');
  const [addressSearch, setAddressSearch] = useState('');
  const [formState, setFormState] = useState({
    name: '',
    phone: '',
    line1: '',
    line2: '',
    city: '',
    state: '',
    pincode: '',
    country: 'Nepal',
    landmark: '',
    type: 'home',
  });
  const { data: addressesData } = useAddresses();
  const { data: enabledProviders } = usePaymentProviders();
  const { data: suggestions } = useAddressAutocomplete(addressSearch, true);
  const createAddress = useCreateAddress();
  const setDefaultAddress = useSetDefaultAddress();
  const createOrder = useCreateOrder();
  const initiatePayment = useInitiatePayment();
  const addresses = useMemo(() => addressesData?.items ?? [], [addressesData?.items]);
  const enabledGatewayMethods = useMemo(
    () =>
      (enabledProviders ?? [])
        .filter(isSupportedGatewayProvider)
        .map((provider) => GATEWAY_PAYMENT_METHODS[provider]),
    [enabledProviders]
  );
  const paymentMethods = useMemo(
    () => [...CORE_PAYMENT_METHODS, ...enabledGatewayMethods],
    [enabledGatewayMethods]
  );

  const effectiveAddressId =
    selectedAddressId ||
    addresses.find((address) => address.is_default)?.id ||
    addresses[0]?.id ||
    '';
  const quoteQuery = useCheckoutQuote({
    addressId: effectiveAddressId,
    paymentMethod,
  });

  useEffect(() => {
    if (!selectedAddressId && addresses.length > 0) {
      const fallbackId =
        addresses.find((address) => address.is_default)?.id ?? addresses[0]?.id ?? '';
      if (fallbackId) {
        setSelectedAddressId(fallbackId);
      }
    }
  }, [addresses, selectedAddressId]);

  useEffect(() => {
    const visibleMethods = new Set(paymentMethods.map((method) => method.value));
    if (!visibleMethods.has(paymentMethod)) {
      setPaymentMethod('cod');
    }
  }, [paymentMethod, paymentMethods]);

  useEffect(() => {
    const pending = getPendingCheckoutPayment();
    if (!pending) return;
    setMessage(
      `You have a pending ${pending.paymentMethod.toUpperCase()} payment. If you closed the provider tab, finish callback verification or retry checkout.`
    );
  }, []);

  async function handleCreateAddress(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      const address = await createAddress.mutateAsync({
        ...formState,
        isDefault: addresses.length === 0,
      });
      setSelectedAddressId(address.id);
      setMessage('Address saved. Shipping quote refreshed for checkout.');
      setFormState({
        name: '',
        phone: '',
        line1: '',
        line2: '',
        city: '',
        state: '',
        pincode: '',
        country: 'Nepal',
        landmark: '',
        type: 'home',
      });
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  }

  async function handlePlaceOrder() {
    if (!effectiveAddressId || !quoteQuery.data?.fingerprint) {
      setMessage('Choose a delivery address first so the backend can compute a fresh quote.');
      return;
    }

    if (!quoteQuery.data.shipping.serviceable) {
      setMessage(
        'This address is not currently serviceable. Pick another address before placing the order.'
      );
      return;
    }

    try {
      if (isGatewayCheckoutMethod(paymentMethod) && isSupportedGatewayProvider(paymentMethod)) {
        const gatewayProvider = paymentMethod;
        const purchaseOrderId = `CHK-${Date.now()}`;
        const customerName =
          [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim() ||
          user?.username ||
          undefined;
        const callbackUrl = buildPaymentCallbackUrl(gatewayProvider);
        const initiated = await initiatePayment.mutateAsync(
          createPaymentInitiationPayload({
            method: gatewayProvider,
            total: quoteQuery.data.total,
            callbackUrl,
            websiteUrl: window.location.origin,
            purchaseOrderId,
            customerName,
            customerEmail: user?.email,
            customerPhone: user?.phone,
          })
        );

        savePendingCheckoutPayment({
          addressId: effectiveAddressId,
          paymentMethod: gatewayProvider,
          quoteFingerprint: quoteQuery.data.fingerprint,
          notes,
          transactionId: initiated.transaction_id,
          purchaseOrderId,
          createdAt: new Date().toISOString(),
        });

        let handoff: ReturnType<typeof extractGatewayHandoff>;
        try {
          handoff = extractGatewayHandoff(initiated);
        } catch (error) {
          clearPendingCheckoutPayment();
          throw error;
        }

        if (handoff.type === 'form') {
          setMessage('Redirecting to eSewa to complete payment...');
          submitEsewaPaymentForm(handoff.action, handoff.fields);
          return;
        }

        const providerLabel = REDIRECT_GATEWAY_LABELS[gatewayProvider as Exclude<SupportedGatewayProvider, 'esewa'>] ?? gatewayProvider;
        setMessage(`Redirecting to ${providerLabel} to complete payment...`);
        window.location.assign(handoff.url);
        return;
      }

      const response = await createOrder.mutateAsync({
        addressId: effectiveAddressId,
        paymentMethod,
        quoteFingerprint: quoteQuery.data.fingerprint,
        notes,
      });
      const order = response.order as { id: string };
      router.push(`/orders/${order.id}`);
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.26em] text-[var(--text-muted)]">Checkout</p>
        <h1 className="mt-3 font-[family:var(--font-display)] text-5xl text-[var(--text-primary)]">
          Move from cart to confirmed order.
        </h1>
      </div>

      {message ? (
        <div className="rounded-[24px] border border-[var(--border-color)] bg-[var(--warning-soft)] px-5 py-4 text-sm text-[var(--text-secondary)]">
          {message}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6">
          <section className="rounded-[32px] border border-[var(--border-color)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <div className="flex items-center gap-3">
              <MapPin className="h-5 w-5 text-[var(--accent)]" />
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">
                  Delivery address
                </p>
                <p className="text-lg font-medium text-[var(--text-primary)]">
                  Pick a saved address or add a new one.
                </p>
              </div>
            </div>
            <div className="mt-5 grid gap-3">
              {addresses.map((address) => (
                <label
                  key={address.id}
                  className={`rounded-[24px] border p-4 transition-colors ${
                    effectiveAddressId === address.id
                      ? 'border-[var(--foreground)] bg-[var(--background)]'
                      : 'border-[var(--border-color)] bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex gap-3">
                      <input
                        type="radio"
                        checked={effectiveAddressId === address.id}
                        onChange={() => setSelectedAddressId(address.id)}
                        className="mt-1"
                      />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">{address.name}</p>
                        <p className="mt-1 text-sm text-[var(--text-secondary)]">
                          {address.line1}, {address.city}, {address.state} {address.pincode}
                        </p>
                        <p className="mt-1 text-xs text-[var(--text-muted)]">
                          {address.phone} · {address.type}
                        </p>
                      </div>
                    </div>
                    {!address.is_default ? (
                      <button
                        type="button"
                        onClick={() => setDefaultAddress.mutate(address.id)}
                        className="rounded-full border border-[var(--border-color)] px-3 py-2 text-xs font-semibold text-[var(--text-secondary)]"
                      >
                        Make default
                      </button>
                    ) : (
                      <span className="rounded-full bg-[var(--success-soft)] px-3 py-2 text-xs font-semibold text-emerald-700">
                        Default
                      </span>
                    )}
                  </div>
                </label>
              ))}
            </div>

            <form
              onSubmit={handleCreateAddress}
              className="mt-6 space-y-4 rounded-[28px] bg-[var(--background)] p-5"
            >
              <div className="grid gap-4 md:grid-cols-2">
                <input
                  value={addressSearch}
                  onChange={(event) => setAddressSearch(event.target.value)}
                  placeholder="Search saved or map suggestions"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none md:col-span-2"
                />
                {suggestions?.slice(0, 3).map((suggestion) => (
                  <button
                    key={`${suggestion.source}-${suggestion.label}`}
                    type="button"
                    onClick={() =>
                      setFormState((current) => ({
                        ...current,
                        line1: suggestion.line1,
                        line2: suggestion.line2,
                        city: suggestion.city,
                        state: suggestion.state,
                        country: suggestion.country || current.country,
                        pincode: suggestion.pincode,
                      }))
                    }
                    className="rounded-[22px] border border-[var(--border-color)] bg-white px-4 py-3 text-left text-sm text-[var(--text-secondary)]"
                  >
                    {suggestion.label}
                  </button>
                ))}
                <input
                  value={formState.name}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="Full name"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
                />
                <input
                  value={formState.phone}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, phone: event.target.value }))
                  }
                  placeholder="Phone number"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
                />
                <input
                  value={formState.line1}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, line1: event.target.value }))
                  }
                  placeholder="Address line 1"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none md:col-span-2"
                />
                <input
                  value={formState.line2}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, line2: event.target.value }))
                  }
                  placeholder="Address line 2"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none md:col-span-2"
                />
                <input
                  value={formState.city}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, city: event.target.value }))
                  }
                  placeholder="City"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
                />
                <input
                  value={formState.state}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, state: event.target.value }))
                  }
                  placeholder="State"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
                />
                <input
                  value={formState.pincode}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, pincode: event.target.value }))
                  }
                  placeholder="Postal code"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
                />
                <input
                  value={formState.landmark}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, landmark: event.target.value }))
                  }
                  placeholder="Landmark"
                  className="rounded-full border border-[var(--border-color)] bg-white px-4 py-3 text-sm outline-none"
                />
              </div>
              <button
                type="submit"
                className="rounded-full bg-[var(--foreground)] px-5 py-3 text-sm font-semibold text-[var(--background)]"
              >
                Save address
              </button>
            </form>
          </section>

          <section className="rounded-[32px] border border-[var(--border-color)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">Payment method</p>
            <div className="mt-4 grid gap-3">
              {paymentMethods.map((method) => (
                <label
                  key={method.value}
                  className={`rounded-[24px] border p-4 ${
                    paymentMethod === method.value
                      ? 'border-[var(--foreground)] bg-[var(--background)]'
                      : 'border-[var(--border-color)] bg-white'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="radio"
                      checked={paymentMethod === method.value}
                      onChange={() => setPaymentMethod(method.value)}
                      className="mt-1"
                    />
                    <div>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{method.label}</p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">{method.help}</p>
                    </div>
                  </div>
                </label>
              ))}
              {enabledGatewayMethods.length === 0 ? (
                <div className="rounded-[22px] border border-dashed border-[rgba(25,30,45,0.12)] bg-[var(--background)] px-4 py-3 text-xs text-[var(--text-secondary)]">
                  No online gateway is enabled by the backend right now, so checkout only shows COD
                  and wallet.
                </div>
              ) : null}
            </div>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Delivery notes"
              rows={4}
              className="mt-4 w-full rounded-[24px] border border-[var(--border-color)] bg-[var(--background)] px-4 py-3 text-sm outline-none"
            />
          </section>
        </div>

        <div className="space-y-4">
          <div className="rounded-[32px] border border-[var(--border-color)] bg-white p-6 shadow-[0_16px_45px_rgba(25,30,45,0.05)]">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-emerald-700" />
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">Quote status</p>
                <p className="text-lg font-medium text-[var(--text-primary)]">Server-calculated totals</p>
              </div>
            </div>

            {quoteQuery.data ? (
              <div className="mt-6 space-y-4">
                <div className="rounded-[24px] bg-[var(--background)] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">
                    Serviceability
                  </p>
                  <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">
                    {quoteQuery.data.shipping.serviceable
                      ? 'Address is serviceable.'
                      : 'Address is not serviceable.'}
                  </p>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Zone {quoteQuery.data.shipping.zone_code ?? 'N/A'} · shipping option{' '}
                    {quoteQuery.data.shipping.shipping_option ?? 'default'}
                  </p>
                </div>
                <div className="space-y-3 text-sm text-[var(--text-secondary)]">
                  <div className="flex items-center justify-between">
                    <span>Cart subtotal</span>
                    <span className="font-medium text-[var(--text-primary)]">
                      {formatCurrency(quoteQuery.data.cart.subtotal)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Discount</span>
                    <span className="font-medium text-[var(--text-primary)]">
                      - {formatCurrency(quoteQuery.data.cart.discount)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Shipping</span>
                    <span className="font-medium text-[var(--text-primary)]">
                      {formatCurrency(quoteQuery.data.shipping.shipping_rate)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Tax ({Math.round(quoteQuery.data.tax_rate * 100)}%)</span>
                    <span className="font-medium text-[var(--text-primary)]">
                      {formatCurrency(quoteQuery.data.tax)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-t border-[var(--border-color)] pt-3 text-base">
                    <span className="font-medium text-[var(--text-primary)]">Total</span>
                    <span className="font-semibold text-[var(--text-primary)]">
                      {formatCurrency(quoteQuery.data.total)}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handlePlaceOrder}
                  disabled={createOrder.isPending || initiatePayment.isPending}
                  className="inline-flex w-full items-center justify-center rounded-full bg-[var(--foreground)] px-5 py-3 text-sm font-semibold text-[var(--background)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {createOrder.isPending
                    ? 'Placing order...'
                    : initiatePayment.isPending
                      ? `Redirecting to ${titleCaseStatus(paymentMethod)}...`
                      : 'Place order'}
                </button>
              </div>
            ) : (
              <div className="mt-6 rounded-[24px] bg-[var(--background)] p-5 text-sm text-[var(--text-secondary)]">
                Choose a saved address to fetch the backend checkout quote.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
