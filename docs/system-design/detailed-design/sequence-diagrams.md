# Sequence Diagrams

## Overview
Detailed sequence diagrams for the current backend implementation. These flows use the FastAPI monolith, persisted domain events, notification services, websocket fanout, and stored artifacts instead of a separate Kafka-based service split.

---

## Checkout With Quote Fingerprint And Inventory Reservation

```mermaid
sequenceDiagram
    participant Client
    participant API as Orders API
    participant Cart as Cart Service
    participant Pricing as Pricing Service
    participant Inventory as Inventory Service
    participant OrderRepo as Order Repository
    participant Pay as Payment Service
    participant Notify as Commerce Event Notifier

    Client->>API: GET /checkout/quote
    API->>Cart: loadCart(user)
    API->>Pricing: calculateTotals(address, coupon, shipping)
    Pricing->>Inventory: summarizeStockForCart()
    Inventory-->>Pricing: availability summary
    Pricing-->>API: totals + quoteFingerprint
    API-->>Client: quote response

    Client->>API: POST /checkout + Idempotency-Key + quoteFingerprint
    API->>OrderRepo: validateIdempotency(key, fingerprint)
    API->>Cart: loadCart(user)
    API->>Pricing: rebuildQuote()
    Pricing-->>API: expected fingerprint

    alt fingerprint mismatch
        API-->>Client: 409 quote changed
    else fingerprint matches
        API->>Inventory: reserveStock(variant, qty, expiry)
        Inventory-->>API: reservations created
        API->>OrderRepo: createOrder(order, items, vendorOrders)

        alt online payment
            API->>Pay: initiatePayment(order, provider)
            Pay-->>API: payment session
        else cod or wallet
            API->>OrderRepo: confirmOrderImmediately()
        end

        API->>Notify: emit(order.created)
        Notify-->>Client: websocket notification
        API-->>Client: order + payment details
    end
```

---

## Payment Verification And Order Reconciliation

```mermaid
sequenceDiagram
    participant Gateway as Payment Gateway
    participant Webhook as Webhook Endpoint
    participant Pay as Payment Service
    participant Orders as Order Service
    participant Inventory as Inventory Service
    participant Notify as Commerce Event Notifier
    participant Feed as Admin Live Feed

    Gateway->>Webhook: POST /payments/webhooks/{gateway}
    Webhook->>Pay: verifySignatureAndPayload()

    alt invalid webhook
        Webhook-->>Gateway: 401 Unauthorized
    else valid webhook
        Pay->>Pay: loadPaymentByGatewayReference()

        alt success or capture
            Pay->>Orders: markPaidAndConfirm(order)
            Orders->>Inventory: commitReservations(order)
            Orders->>Notify: emit(order.paid)
            Notify->>Feed: append live event
            Notify-->>Webhook: processed
        else failure or expiry
            Pay->>Orders: cancelOrKeepPending(order)
            Orders->>Inventory: releaseReservations(order)
            Orders->>Notify: emit(order.cancelled or payment.failed)
            Notify->>Feed: append live event
            Notify-->>Webhook: processed
        end

        Webhook-->>Gateway: 200 OK
    end
```

---

## Wishlist Sharing And Price-Drop Notifications

```mermaid
sequenceDiagram
    participant Customer
    participant Commerce as Wishlist API
    participant Vendor as Vendor API
    participant Catalog as Catalog Service
    participant PriceHistory as Variant Price History
    participant Notify as Commerce Event Notifier

    Customer->>Commerce: POST /wishlist/share-links
    Commerce->>Commerce: createShareToken()
    Commerce-->>Customer: shared wishlist URL

    Vendor->>Vendor: update variant selling price
    Vendor->>Catalog: persist variant change
    Catalog->>PriceHistory: store old and new price

    alt price dropped
        Catalog->>Commerce: find users wishlisting product
        Commerce->>Notify: emit(wishlist.price_drop)
        Notify-->>Customer: persisted notification + websocket event
    else no drop
        Catalog-->>Vendor: update only
    end
```

---

## Shipping Label Generation And Retrieval

```mermaid
sequenceDiagram
    participant Vendor
    participant API as Logistics API
    participant Shipment as Shipment Service
    participant Storage as Storage Adapter
    participant Notify as Commerce Event Notifier

    Vendor->>API: POST /vendor/shipments/{shipmentId}/label
    API->>Shipment: loadShipmentAndAuthorize()
    Shipment->>Shipment: build printable label payload

    alt existing artifact and not forced
        Shipment-->>API: existing url + payload
    else generate or regenerate
        Shipment->>Storage: save label artifact
        Storage-->>Shipment: stable label URL
        Shipment->>Shipment: persist label metadata
        Shipment->>Notify: emit(order.shipped or logistics.label_generated)
        Notify-->>Vendor: websocket event
    end

    API-->>Vendor: label url + generatedAt + payload
```

---

## Return Lifecycle With Reverse Pickup And Refund

```mermaid
sequenceDiagram
    participant Customer
    participant Returns as Return API
    participant Orders as Order Service
    participant Logistics as Logistics Service
    participant Payments as Payment Service
    participant Notify as Commerce Event Notifier
    participant Feed as Admin Live Feed

    Customer->>Returns: POST /returns
    Returns->>Orders: validateReturnWindow(order, items)

    alt not eligible
        Returns-->>Customer: 400 not eligible
    else eligible
        Returns->>Returns: create return request + event
        Returns->>Notify: emit(return.requested)
        Notify->>Feed: append event
        Returns-->>Customer: return created
    end

    Note over Returns,Logistics: Admin or vendor approves return

    Returns->>Logistics: create reverse pickup
    Logistics->>Notify: emit(return.approved)

    Note over Logistics,Payments: Reverse pickup completes and item is received

    Logistics->>Returns: mark picked up / received
    Returns->>Payments: create refund
    Payments->>Notify: emit(return.refunded)
    Notify->>Feed: append event
```

---

## Admin Login And Live Operations Monitoring

```mermaid
sequenceDiagram
    participant Admin
    participant Auth as Auth API
    participant OTP as OTP Service
    participant Obs as Observability Log
    participant Feed as Live Feed API
    participant WS as Websocket Manager

    Admin->>Auth: POST /auth/login
    Auth->>OTP: inspect OTP readiness

    alt OTP enabled
        Auth-->>Admin: temp token / OTP required
        Admin->>Auth: POST /auth/otp/validate
        Auth->>Obs: record auth.admin_otp.verified
        Auth-->>Admin: access + refresh
    else OTP not enabled
        Auth->>Obs: record privileged login without enforced OTP
        Auth-->>Admin: access + refresh + otp_recommended
    end

    Feed->>Obs: load recent order, shipment, return, payout events
    Feed-->>Admin: reverse chronological feed
    WS-->>Admin: live commerce events
```
