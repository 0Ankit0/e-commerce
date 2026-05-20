# Backend Guide

## Overview

This backend is a FastAPI monolith for a multi-vendor e-commerce platform. It now includes:

- auth, multitenancy, RBAC, notifications, analytics, websocket presence
- vendor onboarding, warehouse and payout workflows
- catalog management, CSV bulk product import, advanced filtering, weighted full-text search autocomplete, and behavior-aware product recommendations
- cart, wishlist, wishlist share links, price-drop alerts, tax rules, address autocomplete, checkout fingerprinting, idempotent order creation
- payment flows for `khalti`, `esewa`, `stripe`, `paypal`, `wallet`, and `cod`
- inventory reservations for unpaid online checkouts, stock commit on payment confirmation, stock release on cancel
- orders, invoices, order notes, order timeline, returns, refunds, reverse pickup, shipment proofs
- logistics zones, shipping options, pickup jobs, manifests, line-haul trips, delivery exceptions, reschedule, RTO, branch/hub performance, and stored shipping-label artifacts
- support tickets with comments, assignment, SLA timestamps, and timeline events
- admin content management for banners and static pages
- admin reporting overview, CSV exports, report-job records, admin live order feed, and admin OTP visibility

Hashids remain the canonical public identifier format. Numeric IDs are accepted on selected endpoints as backward-compatible input, but responses continue to return hashids.

## Local Run

```bash
cd backend
uv sync
cp .env.example .env
uv run uvicorn src.main:app --reload
```

The app creates tables automatically in test mode. For local development, point `DATABASE_URL` and `SYNC_DATABASE_URL` at PostgreSQL.

## Container Runtime

From the repository root, the compose stack now builds the backend image once for both the API and Celery worker, runs migrations before booting the API, and persists local media uploads in a named volume:

```bash
docker compose up --build backend worker db redis
```

For production-like deployments, layer the production override so public hosts and origins must be set explicitly:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Set `TRUSTED_HOSTS`, `BACKEND_CORS_ORIGINS`, `SERVER_HOST`, `FRONTEND_URL`, and `WS_ALLOWED_ORIGINS` before using the production override.

## Workers And Infra

- Redis/Celery back async notifications and background tasks.
- Set `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` for non-eager workers.
- In local/dev, `CELERY_TASK_ALWAYS_EAGER=True` is enough for most API work.
- Local media storage uses `MEDIA_DIR` and `MEDIA_URL`. S3-style storage is supported through the existing storage settings.

## Key Configuration

Important groups in [`.env.example`](./.env.example):

- Core/auth: `SECRET_KEY`, `PASSWORD_PEPPER`, token expiry, password policy, login lockout.
- Runtime/features: `DEBUG`, `TESTING`, `FEATURE_*`.
- DB/cache: `DATABASE_URL`, `SYNC_DATABASE_URL`, Redis and pool settings.
- Maps: `MAP_PROVIDER`, `OSM_MAPS_ENABLED`, `GOOGLE_MAPS_ENABLED`, `GOOGLE_MAPS_API_KEY`.
- Payments: `KHALTI_*`, `ESEWA_*`, `STRIPE_*`, `PAYPAL_*`.
- Notifications: email, SMS, push, VAPID, FCM, OneSignal.
- Throttling: `RATE_LIMIT_*`, burst/error spike settings.

## Provider Notes

### Payments

Supported now:

- `khalti`
- `esewa`
- `stripe`
- `paypal`
- `wallet`
- `cod`
- `razorpay`

### Webhooks

Payment webhooks are exposed at:

```text
POST /api/v1/payments/webhooks/{provider}
```

Headers:

- `X-Webhook-Signature`
- `X-Webhook-Event`

Verification accepts an HMAC-SHA256 signature of the raw request body using the provider secret. A direct secret header match is still accepted as a backward-compatible fallback.

## Behavior By Module

### Catalog And Inventory

- Vendor bulk import endpoints:
  - `GET /api/v1/vendor/products/import/template`
  - `POST /api/v1/vendor/products/import/preview`
  - `POST /api/v1/vendor/products/import/commit`
- Product listing supports filters for price, rating, category, brand, vendor, stock state, featured state, and attribute key/value.
- Search uses weighted full-text ranking across product titles, descriptions, categories, brands, specifications, variants, and SKU keywords.
- Search autocomplete uses the same ranked discovery index, so prefix, phrase, and fuzzy matches stay aligned with full search results.
- Recommendation endpoints blend popularity, user affinity, recent behavior, product similarity, and cross-shopper collaborative signals.
- Recommendation learning now ingests product views, searches, carts, wishlists, ratings, and purchases.
- Inventory reservations are created for unpaid online checkouts and committed after payment confirmation.
- Inventory summary and reorder reporting are available for vendors/admin.

### Checkout And Pricing

- Tax calculation is rule-driven through admin tax rules.
- Shipping is serviceability-aware and supports explicit shipping option selection.
- Checkout quote fingerprints protect clients from stale totals.
- Idempotency keys are persisted and tied to checkout requests.
- Address autocomplete prefers saved addresses and can use OSM or Google depending on config.

### Orders, Returns, Refunds

- Orders expose invoice, timeline, note, tracking, vendor split, and shipment data.
- Admin can add order notes.
- Returns enforce a policy window and now emit timeline events.
- Payment reconciliation updates linked orders after verification, capture, void, refund, and webhooks.
- Commerce events now fan out persisted notifications plus websocket events for order, return, payout, low-stock, and delivery-exception flows.

### Vendors

- Vendor onboarding states include pending, under review, needs resubmission, approved, rejected, and suspended.
- Document and bank-account verification support resubmission and admin review.
- Vendor timeline events capture onboarding and payout workflow milestones.
- Vendors can create payout requests; admins can approve requests, create payout batches, and export settlements.

### Logistics And Support

- Delivery exceptions support failed-delivery recording, reschedule, and RTO initiation.
- Shipping labels are generated as stored artifacts and are available from both vendor and admin/logistics endpoints.
- Agent availability, branch inventory movements, and hub/branch performance endpoints are available.
- Support tickets include assignment, SLA timestamps, customer/admin comments, and timeline events.

### Wishlist And Admin Security

- Customers can create, list, revoke, and publicly share read-only wishlist links.
- Vendor price changes snapshot variant price history and trigger wishlist price-drop notifications.
- Admin logins continue to work without mandatory OTP, but the login response now recommends OTP when a superuser account has not enabled it.
- `GET /api/v1/auth/admin/security/admin-otp-status` exposes current OTP readiness plus the latest OTP audit event for admin accounts.

## SMS quota rollout plan (safe defaults + monitoring)

1. **Schema migration first**: apply `bb91d8e4c112_expand_sms_quota_policy_engine` to add multi-level counters (tenant/phone) and soft/hard throttle metadata.
2. **Safe defaults enabled**:
   - soft cap uses `delay` action with 30s pause,
   - hard cap uses `block`,
   - existing per-user/IP/global caps remain active.
3. **Canary rollout**:
   - keep `global_provider_soft_daily_limit` low in staging to validate trend/offender cards and incident exports,
   - promote to production with conservative limits and privileged override enabled.
4. **Monitoring**:
   - poll `/api/v1/notifications/admin/sms-quotas/dashboard/` for usage trends and top offenders,
   - poll `/api/v1/notifications/admin/sms-quotas/violations/` and `/incidents/export/` for compliance/security workflows.
5. **Operational response**:
   - tune per-tenant/per-phone limits to isolate abuse,
   - switch `soft_throttle_action` (`delay` or `challenge`) before escalating hard blocks.

### Content And Reporting

- Admin content endpoints manage banners and static pages.
- Public content endpoints expose active banners and published pages.
- Admin reporting includes overview, CSV export, and persisted report-job records.

## Verification

The current completion pass was verified with:

```bash
cd backend
uv run python -m compileall src
uv run pytest -q
```

## Status Matrix And Future Work

See [backend-status-matrix.md](../docs/system-design/implementation/backend-status-matrix.md).

Future-only items called out explicitly:

- external routing providers beyond the built-in nearest-neighbor + 2-opt optimizer
- advanced native Apple Sign In client work across frontend/mobile

## References Consulted

These official references informed the backend hardening and feature surface:

- Stripe idempotent requests: https://docs.stripe.com/api/idempotent_requests
- Stripe webhooks: https://docs.stripe.com/webhooks
- Medusa inventory concepts and reservation items: https://docs.medusajs.com/resources/commerce-modules/inventory/concepts
- commercetools cart discounts: https://docs.commercetools.com/api/projects/cartDiscounts
- OWASP API Security Top 10: https://owasp.org/API-Security/
