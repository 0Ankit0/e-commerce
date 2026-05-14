# Frontend Runtime Guide

The web app is a Next.js storefront and portal shell that reads live marketplace and auth state from the FastAPI backend. Production pages should render loading, empty, error, retry, or not-found states instead of falling back to mock data.

## Local Development

- `npm install`
- `npm run dev`
- Configure `NEXT_PUBLIC_API_URL` to point at the backend `api/v1` base URL.

## Container Runtime

- Use the repository root compose file for containerized runs; the stale nested frontend compose file has been removed.
- The frontend Docker image now builds a production bundle and starts with `next start` instead of `next dev`.
- `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` are passed as Docker build args and runtime env so the generated bundle can target the correct backend.

From the repository root:

```bash
docker compose up --build frontend backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Set `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` before using the production override.

## Verification

- `npm run typecheck`
- `npm run test`
- `npm run build`

## Key Runtime Areas

- Public storefront routes: `/`, `/shop`, `/products/[productId]`
- Customer portal routes under `src/app/(user-dashboard)`
- Vendor portal routes under `src/app/(vendor-dashboard)`
- Social auth provider discovery via `/auth/social/providers/`
- Storefront discovery hooks live in `src/hooks/use-catalog.ts` and now cover full-text search, autocomplete, recommendation feeds, and recommendation-event tracking.
- `src/app/shop/page.tsx` consumes ranked search and autocomplete suggestions.
- `src/app/products/[productId]/page.tsx` and `src/app/(user-dashboard)/dashboard/page.tsx` render recommendation rails backed by `/recommendations`.
