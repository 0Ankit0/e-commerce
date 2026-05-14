import { act, type ReactElement, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import UserDashboardPage from './(user-dashboard)/dashboard/page';
import AdminDashboardPage from './(admin-dashboard)/admin/dashboard/page';
import VerifyEmailPage from './(auth)/verify-email/page';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const useOrdersMock = vi.fn();
const useWishlistMock = vi.fn();
const useCartMock = vi.fn();
const useNotificationsMock = vi.fn();
const useCatalogRecommendationsMock = vi.fn();
const useAuthStoreMock = vi.fn();
const useListUsersMock = vi.fn();
const useVendorProductsMock = vi.fn();
const useSearchParamsMock = vi.fn();
const useRouterPushMock = vi.fn();
const useVerifyEmailMock = vi.fn();
const useResendVerificationMock = vi.fn();

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: ReactNode }) => <a href={href} {...props}>{children}</a>,
}));

vi.mock('next/navigation', () => ({
  useSearchParams: () => useSearchParamsMock(),
  useRouter: () => ({ push: useRouterPushMock }),
}));

vi.mock('@/hooks/use-orders', () => ({ useOrders: (...args: unknown[]) => useOrdersMock(...args) }));
vi.mock('@/hooks/use-commerce', () => ({
  useWishlist: (...args: unknown[]) => useWishlistMock(...args),
  useCart: (...args: unknown[]) => useCartMock(...args),
}));
vi.mock('@/hooks/use-notifications', () => ({ useNotifications: (...args: unknown[]) => useNotificationsMock(...args) }));
vi.mock('@/hooks/use-catalog', () => ({
  useCatalogRecommendations: (...args: unknown[]) => useCatalogRecommendationsMock(...args),
  useVendorProducts: (...args: unknown[]) => useVendorProductsMock(...args),
}));
vi.mock('@/hooks/use-users', () => ({ useListUsers: (...args: unknown[]) => useListUsersMock(...args) }));
vi.mock('@/store/auth-store', () => ({ useAuthStore: () => useAuthStoreMock() }));
vi.mock('@/hooks/use-auth', () => ({
  useVerifyEmail: (...args: unknown[]) => useVerifyEmailMock(...args),
  useResendVerification: (...args: unknown[]) => useResendVerificationMock(...args),
}));

function queryState<T>(overrides: Partial<{ data: T; isLoading: boolean; isError: boolean; error: unknown; refetch: () => Promise<unknown> }>) {
  return { data: undefined, isLoading: false, isError: false, error: null, refetch: vi.fn().mockResolvedValue(undefined), ...overrides };
}

function render(element: ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  act(() => {
    root.render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
  });
  return { container, unmount() { act(() => root.unmount()); container.remove(); } };
}

describe('major route runtime states', () => {
  let roots: Array<{ unmount: () => void }> = [];
  beforeEach(() => {
    useAuthStoreMock.mockReturnValue({ user: null });
    useOrdersMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    useWishlistMock.mockReturnValue({ data: { items: [] } });
    useCartMock.mockReturnValue({ data: { items: [] } });
    useNotificationsMock.mockReturnValue(queryState({ data: { items: [], unread_count: 0 } }));
    useCatalogRecommendationsMock.mockReturnValue(queryState({ data: { strategy: 'ml_ranker_v2', items: [] } }));
    useListUsersMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    useVendorProductsMock.mockReturnValue(queryState({ data: { items: [], total: 0 } }));
    useSearchParamsMock.mockReturnValue(new URLSearchParams('t=test-token'));
    useVerifyEmailMock.mockReturnValue({
      mutate: (_: string, opts: { onSuccess: () => void }) => opts.onSuccess(),
    });
    useResendVerificationMock.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  afterEach(() => {
    roots.forEach((r) => r.unmount());
    roots = [];
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('shows explicit notification failure and retry on user dashboard', () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    useNotificationsMock.mockReturnValue(queryState({ isError: true, error: { isAxiosError: true, response: { status: 429 } }, refetch }));
    const view = render(<UserDashboardPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('Notifications unavailable');
    expect(view.container.textContent).toContain('Too many requests');
  });

  it('shows admin runtime error when one feed returns partial payload', () => {
    useVendorProductsMock.mockReturnValue(queryState({ data: { items: [] } }));
    const view = render(<AdminDashboardPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('Admin metrics unavailable');
    expect(view.container.textContent).toContain('Payload validation failed');
  });

  it('shows verify-email no-token state without silent fallback', () => {
    useSearchParamsMock.mockReturnValue(new URLSearchParams(''));
    const view = render(<VerifyEmailPage />);
    roots.push(view);

    expect(view.container.textContent).toContain('No verification token found');
    expect(view.container.textContent).toContain('Missing query parameter');
  });
});
