# REST API Endpoints Documentation

See `/doc/` for interactive Swagger documentation.

## Canonical API Namespace

All contract-facing endpoints are now available under:

- `/api/v1/`

## Canonical Contract Endpoints (`/api/v1`)

### Auth
- `POST /api/v1/auth/signup/`
- `POST /api/v1/auth/token-refresh/`
- `POST /api/v1/auth/logout/`
- `GET|PUT|PATCH /api/v1/auth/profile/me/`
- `GET|POST /api/v1/auth/profile/`
- `GET|PUT|PATCH|DELETE /api/v1/auth/profile/{id}/`

### Products
- `GET|POST /api/v1/products/`
- `GET|PUT|PATCH|DELETE /api/v1/products/{slug}/`

### Cart
- `GET|POST /api/v1/cart/`
- `GET|PUT|PATCH|DELETE /api/v1/cart/{id}/`

### Orders
- `GET|POST /api/v1/orders/`
- `GET|PUT|PATCH|DELETE /api/v1/orders/{id}/`

### Payments
- `GET|POST /api/v1/payments/`
- `GET|PUT|PATCH|DELETE /api/v1/payments/{id}/`

### Vendor
- `GET|POST /api/v1/vendor/`
- `GET|PUT|PATCH|DELETE /api/v1/vendor/{slug}/`
- `GET|POST /api/v1/vendor/orders/`
- `GET|PUT|PATCH|DELETE /api/v1/vendor/orders/{id}/`

### Admin
- `POST /api/v1/admin/refunds/`

### Recommendations
- `GET /api/v1/recommendations/`
- `GET /api/v1/recommendations/for-you/`

## Backward Compatibility and Deprecation

Legacy module endpoints under `/api/` remain available for backward compatibility.

Examples include:
- `/api/auth/...`
- `/api/users/...`
- `/api/catalog/...`
- `/api/orders/...`
- `/api/payments/...`
- `/api/vendors/...`
- `/api/inventory/...`
- `/api/logistics/...`

These legacy endpoints are marked as **deprecated** in OpenAPI and should be migrated to `/api/v1/...`.
