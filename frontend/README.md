# Frontend Runtime Guide

The web app is a Next.js storefront and portal shell that reads live marketplace and auth state from the FastAPI backend. Production pages should render loading, empty, error, retry, or not-found states instead of falling back to mock data.

## Local Development

- `npm install`
- `npm run dev`
- Configure `NEXT_PUBLIC_API_URL` to point at the backend `api/v1` base URL.

## Verification

- `npm run typecheck`
- `npm run test`
- `npm run build`

## Key Runtime Areas

- Public storefront routes: `/`, `/shop`, `/products/[productId]`
- Customer portal routes under `src/app/(user-dashboard)`
- Vendor portal routes under `src/app/(vendor-dashboard)`
- Social auth provider discovery via `/auth/social/providers/`
