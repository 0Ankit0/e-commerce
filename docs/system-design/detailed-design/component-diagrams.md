# Component Diagrams

## Overview
These component diagrams reflect the implemented FastAPI monolith rather than an older service-by-service split.

---

## System Component Overview

```mermaid
graph TB
    subgraph "Client Layer"
        CustomerWeb[Customer Web / Mobile]
        VendorWeb[Vendor Portal]
        AdminWeb[Admin Dashboard]
        AgentApp[Agent App]
    end

    subgraph "FastAPI Backend"
        APIRouter[Versioned API Routers]

        subgraph "Core Modules"
            Auth[Auth + OTP]
            Catalog[Catalog + Search]
            Commerce[Cart + Wishlist + Pricing]
            Orders[Checkout + Orders + Returns]
            Payments[Payments + Refunds]
            Vendors[Vendors + Payouts]
            Logistics[Shipments + Tracking + Labels]
            Support[Support + Reports + CMS]
            Notify[Notifications + Websocket Fanout]
        end
    end

    subgraph "Infrastructure"
        DB[(PostgreSQL)]
        Redis[(Redis)]
        Storage[(Object Storage)]
        WS[Websocket Manager]
    end

    CustomerWeb --> APIRouter
    VendorWeb --> APIRouter
    AdminWeb --> APIRouter
    AgentApp --> APIRouter

    APIRouter --> Auth
    APIRouter --> Catalog
    APIRouter --> Commerce
    APIRouter --> Orders
    APIRouter --> Payments
    APIRouter --> Vendors
    APIRouter --> Logistics
    APIRouter --> Support

    Catalog --> DB
    Commerce --> DB
    Orders --> DB
    Payments --> DB
    Vendors --> DB
    Logistics --> DB
    Support --> DB
    Notify --> DB
    Auth --> DB

    Auth --> Redis
    Catalog --> Redis
    Commerce --> Redis

    Catalog --> Storage
    Logistics --> Storage
    Support --> Storage
    Notify --> WS
```

---

## Identity And Security Components

```mermaid
graph TB
    subgraph "IAM Module"
        Login[Login Endpoint]
        OTPSetup[OTP Enable / Verify / Disable]
        OTPValidate[OTP Challenge Validation]
        TokenSvc[JWT Token Service]
        PasswordSvc[Password Hash / Verify]
        AdminReadiness[Admin OTP Readiness View]
        Audit[Observability Audit Logging]
    end

    Redis[(Redis)]
    DB[(PostgreSQL)]

    Login --> TokenSvc
    Login --> PasswordSvc
    Login --> AdminReadiness
    OTPSetup --> Audit
    OTPValidate --> Audit
    AdminReadiness --> DB
    TokenSvc --> Redis
    PasswordSvc --> DB
    Audit --> DB
```

---

## Commerce And Order Components

```mermaid
graph TB
    subgraph "Commerce / Orders"
        CartAPI[Cart Routes]
        WishlistAPI[Wishlist Routes]
        CheckoutAPI[Checkout Routes]
        OrdersAPI[Order Routes]
        ReturnsAPI[Return Routes]

        QuoteEngine[Quote Fingerprint Builder]
        TaxRules[Tax Rule Evaluator]
        ShippingRules[Shipping Serviceability Evaluator]
        PromoRules[Promotion / Coupon Evaluator]
        Reservations[Inventory Reservation Manager]
        Timelines[Order / Return Timeline Writer]
        PriceDrops[Price History + Price-Drop Detector]
        Notify[Commerce Event Notifier]
    end

    DB[(PostgreSQL)]
    Cache[(Redis)]
    WS[Websocket Manager]

    CartAPI --> QuoteEngine
    WishlistAPI --> PriceDrops
    CheckoutAPI --> QuoteEngine
    CheckoutAPI --> Reservations
    CheckoutAPI --> PromoRules
    CheckoutAPI --> TaxRules
    CheckoutAPI --> ShippingRules
    OrdersAPI --> Timelines
    ReturnsAPI --> Timelines

    PriceDrops --> Notify
    Timelines --> Notify
    Notify --> WS

    QuoteEngine --> DB
    Reservations --> DB
    PromoRules --> DB
    Timelines --> DB
    PriceDrops --> DB
    CartAPI --> Cache
```

---

## Logistics, Payouts, And Operations Components

```mermaid
graph TB
    subgraph "Operations Modules"
        VendorAPI[Vendor Routes]
        LogisticsAPI[Logistics Routes]
        AdminAPI[Admin Routes]
        PaymentAPI[Payment Routes]

        LabelSvc[Shipping Label Generator]
        PayoutSvc[Payout Request and Batch Manager]
        Reconcile[Payment Verification and Refund Reconciliation]
        DeliveryOps[Delivery Exception / Reschedule / RTO Logic]
        LiveFeed[Admin Live Feed Aggregator]
        Notify[Notification Dispatcher]
    end

    DB[(PostgreSQL)]
    Storage[(Object Storage)]
    WS[Websocket Manager]
    Gateways[Payment Providers]
    LogisticsPartner[Logistics Partner]

    VendorAPI --> LabelSvc
    VendorAPI --> PayoutSvc
    LogisticsAPI --> LabelSvc
    LogisticsAPI --> DeliveryOps
    PaymentAPI --> Reconcile
    AdminAPI --> LiveFeed

    LabelSvc --> Storage
    LabelSvc --> DB
    PayoutSvc --> DB
    Reconcile --> Gateways
    Reconcile --> DB
    DeliveryOps --> LogisticsPartner
    DeliveryOps --> DB
    LiveFeed --> DB
    LiveFeed --> WS
    Notify --> WS
```
