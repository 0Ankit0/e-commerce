# C4 Component Diagram

## Overview
This document captures component-level structure for the current FastAPI backend. It intentionally reflects the monolith in the repository instead of the earlier separate-service proposal.

---

## Catalog And Commerce Components

```mermaid
graph TB
    Client[Client]

    subgraph boundary["Catalog + Commerce Components"]
        CatalogRoutes["Catalog Routes<br><i>FastAPI routers</i>"]
        CommerceRoutes["Cart / Wishlist Routes<br><i>FastAPI routers</i>"]
        SearchService["Search and Filter Service<br><i>Service</i>"]
        ImportService["CSV Import Preview / Commit<br><i>Service</i>"]
        PriceHistory["Variant Price History Recorder<br><i>Service</i>"]
        WishlistShare["Wishlist Share Link Manager<br><i>Service</i>"]
        PriceDropNotifier["Wishlist Price-Drop Notifier<br><i>Service</i>"]
        CatalogRepo["Catalog Repository Layer<br><i>Repository</i>"]
        Cache["Redis Cache Adapter<br><i>Adapter</i>"]
        Storage["Media Storage Adapter<br><i>Adapter</i>"]
    end

    DB[(PostgreSQL)]
    WS[Websocket Manager]

    Client --> CatalogRoutes
    Client --> CommerceRoutes
    CatalogRoutes --> SearchService
    CatalogRoutes --> ImportService
    CatalogRoutes --> PriceHistory
    CommerceRoutes --> WishlistShare
    PriceHistory --> PriceDropNotifier
    SearchService --> CatalogRepo
    ImportService --> CatalogRepo
    PriceHistory --> CatalogRepo
    WishlistShare --> CatalogRepo
    PriceDropNotifier --> WS
    CatalogRepo --> DB
    SearchService --> Cache
    ImportService --> Storage
```

---

## Orders And Payments Components

```mermaid
graph TB
    Client[Client]

    subgraph boundary["Orders + Payments Components"]
        CheckoutRoutes["Checkout Routes<br><i>FastAPI routers</i>"]
        OrderRoutes["Order / Return Routes<br><i>FastAPI routers</i>"]
        PaymentRoutes["Payment Routes<br><i>FastAPI routers</i>"]

        QuoteEngine["Quote Fingerprint Builder<br><i>Service</i>"]
        ReservationSvc["Inventory Reservation Service<br><i>Service</i>"]
        TimelineSvc["Order and Return Event Writer<br><i>Service</i>"]
        PaymentManager["Payment Manager<br><i>Service</i>"]
        RefundManager["Refund Manager<br><i>Service</i>"]
        GatewayFactory["Gateway Factory<br><i>Factory</i>"]
        SignatureValidator["Webhook Signature Validator<br><i>Security</i>"]
        EventNotifier["Commerce Event Notifier<br><i>Service</i>"]
    end

    DB[(PostgreSQL)]
    PayGW[Supported Payment Providers]
    WS[Websocket Manager]

    Client --> CheckoutRoutes
    Client --> OrderRoutes
    Client --> PaymentRoutes

    CheckoutRoutes --> QuoteEngine
    CheckoutRoutes --> ReservationSvc
    OrderRoutes --> TimelineSvc
    PaymentRoutes --> PaymentManager
    PaymentRoutes --> RefundManager
    PaymentRoutes --> SignatureValidator
    PaymentManager --> GatewayFactory
    PaymentManager --> EventNotifier
    RefundManager --> EventNotifier
    TimelineSvc --> EventNotifier
    EventNotifier --> WS
    QuoteEngine --> DB
    ReservationSvc --> DB
    TimelineSvc --> DB
    PaymentManager --> DB
    RefundManager --> DB
    GatewayFactory --> PayGW
```

---

## Logistics, Vendors, And Admin Components

```mermaid
graph TB
    Operator[Vendor / Admin / Agent]

    subgraph boundary["Operations Components"]
        VendorRoutes["Vendor Routes<br><i>FastAPI routers</i>"]
        LogisticsRoutes["Logistics Routes<br><i>FastAPI routers</i>"]
        AdminRoutes["Admin Routes<br><i>FastAPI routers</i>"]
        LabelService["Shipping Label Artifact Service<br><i>Service</i>"]
        ExceptionService["Delivery Exception and RTO Service<br><i>Service</i>"]
        PayoutService["Payout Request / Batch Service<br><i>Service</i>"]
        ReportService["Report Export and Job Service<br><i>Service</i>"]
        LiveFeed["Admin Live Feed Aggregator<br><i>Service</i>"]
        NotificationService["Notification Dispatcher<br><i>Service</i>"]
    end

    DB[(PostgreSQL)]
    Storage[(Object Storage)]
    LogisticsPartner[Logistics Partner]
    WS[Websocket Manager]

    Operator --> VendorRoutes
    Operator --> LogisticsRoutes
    Operator --> AdminRoutes

    VendorRoutes --> LabelService
    VendorRoutes --> PayoutService
    LogisticsRoutes --> LabelService
    LogisticsRoutes --> ExceptionService
    AdminRoutes --> ReportService
    AdminRoutes --> LiveFeed

    LabelService --> Storage
    LabelService --> DB
    ExceptionService --> LogisticsPartner
    ExceptionService --> NotificationService
    PayoutService --> NotificationService
    ReportService --> Storage
    ReportService --> DB
    LiveFeed --> DB
    LiveFeed --> WS
    NotificationService --> WS
    NotificationService --> DB
```

---

## IAM Component Notes

| Capability | Component Role |
|-----------|----------------|
| OTP setup and verification | IAM routers + OTP service |
| Admin OTP readiness | IAM admin security endpoint |
| Audit visibility | Observability log writer and reader |
| Login recommendation | Auth login response builder for privileged users without OTP |
