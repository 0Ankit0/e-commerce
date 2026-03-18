# Backend Status Matrix

This matrix reflects the backend implementation status after the current completion pass.

Status labels:

- `implemented now`: already present before this completion pass
- `implemented in this completion pass`: added or materially completed in this pass
- `future`: documented but intentionally not implemented yet

| Area | Capability | Status |
|------|------------|--------|
| Auth | JWT auth, token tracking, RBAC, social auth hooks | `implemented now` |
| Catalog | Categories, brands, vendor product CRUD, reviews, recommendations | `implemented now` |
| Catalog | Bulk product CSV import with preview, validation, commit, row-level result storage | `implemented in this completion pass` |
| Catalog | Advanced filters and fuzzy autocomplete | `implemented in this completion pass` |
| Inventory | Warehouse stock tracking, low-stock reporting, reorder report | `implemented in this completion pass` |
| Inventory | Reservation-based stock protection for unpaid online orders | `implemented in this completion pass` |
| Cart | Persistent cart, wishlist, coupon apply/remove | `implemented now` |
| Checkout | Serviceability-aware shipping, tax rules, quote fingerprinting, idempotency persistence | `implemented in this completion pass` |
| Checkout | Address autocomplete through saved addresses plus OSM/Google providers | `implemented in this completion pass` |
| Promotions | Coupon validation and discount handling | `implemented now` |
| Promotions | Rule-aware scope, per-user limits, stackability metadata, usage tracking | `implemented in this completion pass` |
| Orders | Order creation, vendor split, tracking, invoice, order notes, order timeline | `implemented in this completion pass` |
| Returns | Policy-window enforcement, reverse-pickup-aware return timeline, admin status transitions | `implemented in this completion pass` |
| Refunds | Refund record tracking and payment reconciliation | `implemented now` |
| Payments | Khalti, eSewa, Stripe, PayPal, wallet, COD | `implemented now` |
| Payments | Order sync on verify/capture/void/refund/webhook | `implemented in this completion pass` |
| Payments | Hardened webhook verification with HMAC support | `implemented in this completion pass` |
| Vendors | Vendor profile, warehouses, analytics, payout history | `implemented now` |
| Vendors | Under-review/resubmission workflow, timeline events, payout requests, payout batches, settlement export | `implemented in this completion pass` |
| Logistics | Zones, shipping options, pickup jobs, manifests, trips, POD | `implemented now` |
| Logistics | Delivery exceptions, reschedule, RTO, label metadata, agent availability, branch/hub performance | `implemented in this completion pass` |
| Support | Ticket creation and admin list | `implemented now` |
| Support | Ticket comments, assignment, SLA timestamps, ticket timeline | `implemented in this completion pass` |
| Content | Admin banners and static pages plus public content endpoints | `implemented in this completion pass` |
| Reporting | Admin overview dashboard | `implemented now` |
| Reporting | CSV export and persisted report jobs | `implemented in this completion pass` |
| Security | Public hashid responses, numeric-id compatibility input, timezone-aware UTC helpers, safer password hash default, payment audit logs | `implemented in this completion pass` |
| Notifications | Async notification infrastructure, device registry, preferences | `implemented now` |
| Notifications | Low-stock, payout, return-event, and richer order-state fanout | `future` |
| Logistics | External route optimization engine | `future` |
| Logistics | Real-time courier GPS ingestion | `future` |
| Recommendations | ML-grade ranking and re-ranking | `future` |
| Payments | Razorpay integration | `future` |

## Requirement Coverage Notes

- The requirements docs list Razorpay under payment gateways. The running backend intentionally keeps the active provider set to `khalti`, `esewa`, `stripe`, `paypal`, `wallet`, and `cod`; Razorpay remains future work.
- The implementation stays in the current FastAPI monolith rather than splitting into separate services.
- Hashids remain the outward-facing identifier format.
- The maps abstraction defaults to OSM and upgrades to Google when configured.
