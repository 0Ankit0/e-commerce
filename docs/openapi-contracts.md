# OpenAPI Contract Drift Guardrails

This repository now treats FastAPI OpenAPI output as the source of truth for frontend response contracts.

## Workflow

1. Export current FastAPI schema:
   - `cd frontend && npm run contracts:export`
2. Validate current schema against committed baseline:
   - `cd frontend && npm run contracts:check`
3. Refresh baseline when an intentional API contract change is made:
   - `cd frontend && npm run contracts:sync`

## What the compatibility check blocks

The check in `frontend/scripts/check-openapi-drift.mjs` fails CI when it detects:

- Response property requiredness changes.
- Response property type changes.
- Enum value changes (including enum expansion).
- Nullable flag changes.
- Paginated response metadata omissions (`items`, `total`, `skip`, `limit`, `has_more`).

## Frontend edge-case protections

- `StrictPaginatedResponse` enforces pagination metadata presence in TS payload types.
- `asApiEnum` maps newly introduced enum values to `"unknown"` to avoid runtime breakage when backend adds values before frontend deploy.

## Discovery API notes

- Discovery contract changes now include the ranked catalog endpoints used by `frontend/src/app/shop/page.tsx` and the recommendation feed consumed from `frontend/src/app/products/[productId]/page.tsx` and `frontend/src/app/(user-dashboard)/dashboard/page.tsx`.
- When changing `/products`, `/search`, `/search/autocomplete`, `/recommendations`, or `/recommendations/events`, refresh the exported schema before updating the committed snapshot.

## Hashid/numeric-id compatibility

`decode_id_or_404` keeps documented compatibility by accepting both canonical hashids and legacy numeric IDs.
A dedicated unit test is included at `backend/tests/unit/iam/utils/test_hashid_compatibility.py`.
