# C4 Diagrams

## Overview
These C4 diagrams describe the current repository architecture, not the earlier microservice proposal. The running backend is a FastAPI monolith with internal modules for catalog, commerce, orders, payments, logistics, vendors, support, notifications, and websocket fanout.

---

## Level 1: System Context Diagram

```mermaid
graph TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))
    Agent((Delivery Agent))

    subgraph "E-Commerce Platform"
        System[E-Commerce System<br>FastAPI monolith for marketplace, fulfillment, support, and admin operations]
    end

    PaymentGW[Payment Providers<br>Khalti, eSewa, Stripe, PayPal]
    LogisticsPartner[Logistics Partner]
    NotificationProviders[Email / SMS / Push]
    MapsAPI[Maps Provider<br>OSM default, Google optional]
    MediaStorage[Object Storage]

    Customer -->|browse, buy, track, return, wishlist| System
    Vendor -->|manage catalog, inventory, payouts, labels| System
    Admin -->|approve, monitor, report, moderate| System
    Agent -->|pickup and delivery updates| System

    System -->|initiate and verify payments| PaymentGW
    System <-->|create shipments and tracking| LogisticsPartner
    System -->|transactional notifications| NotificationProviders
    System -->|address lookup and ETA support| MapsAPI
    System -->|media and label artifacts| MediaStorage
```

---

## Level 2: Container Diagram

```mermaid
graph TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))
    Agent((Agent))

    subgraph "E-Commerce Platform"
        Web[Web / Mobile Clients]
        VendorUI[Vendor Portal]
        AdminUI[Admin Dashboard]
        AgentUI[Agent App]

        API[FastAPI Application<br>Versioned routers and domain modules]
        WS[Websocket Manager]
        Worker[Async Notification / Task Worker]

        DB[(PostgreSQL)]
        Redis[(Redis)]
        Storage[(Object Storage)]
    end

    PaymentGW[Payment Providers]
    Msg[Email / SMS / Push]
    Maps[Maps Provider]
    LogisticsPartner[Logistics Partner]

    Customer --> Web
    Vendor --> VendorUI
    Admin --> AdminUI
    Agent --> AgentUI

    Web --> API
    VendorUI --> API
    AdminUI --> API
    AgentUI --> API

    API --> WS
    API --> Worker
    API --> DB
    API --> Redis
    API --> Storage

    API --> PaymentGW
    API --> Maps
    API --> LogisticsPartner
    Worker --> Msg
```

---

## Level 3: Component Diagram - Commerce Core

```mermaid
graph TB
    Client[Authenticated Client]

    subgraph "FastAPI Commerce Core"
        CommerceAPI[Cart / Wishlist / Pricing Routers]
        CatalogAPI[Catalog Routers]
        OrdersAPI[Checkout / Orders / Returns Routers]

        Pricing[Pricing and Quote Engine]
        Inventory[Inventory and Reservation Logic]
        Promotions[Coupon and Promotion Rules]
        Wishlist[Wishlist Sharing and Price-Drop Logic]
        Timelines[Order and Return Event Timeline Logic]
        Notify[Commerce Event Notifier]
    end

    DB[(PostgreSQL)]
    Cache[(Redis)]
    WS[Websocket Manager]

    Client --> CommerceAPI
    Client --> CatalogAPI
    Client --> OrdersAPI

    CommerceAPI --> Pricing
    CommerceAPI --> Wishlist
    OrdersAPI --> Pricing
    OrdersAPI --> Inventory
    OrdersAPI --> Timelines
    Pricing --> Promotions
    CatalogAPI --> Wishlist

    Wishlist --> Notify
    Timelines --> Notify
    Inventory --> DB
    Pricing --> DB
    Promotions --> DB
    Wishlist --> DB
    Timelines --> DB
    CommerceAPI --> Cache
    Notify --> WS
    Notify --> DB
```

---

## Level 3: Component Diagram - Operations And Fulfillment

```mermaid
graph TB
    Operator[Vendor / Admin / Agent]

    subgraph "Operations Components"
        VendorAPI[Vendor Routers]
        LogisticsAPI[Logistics Routers]
        PaymentAPI[Payment Routers]
        AdminAPI[Admin and Reporting Routers]

        LabelService[Shipping Label Artifact Service]
        Payouts[Payout Request and Batch Service]
        Reconciliation[Payment Verification and Refund Reconciliation]
        LiveFeed[Admin Live Feed Aggregator]
        Notify[Notification and Websocket Fanout]
    end

    DB[(PostgreSQL)]
    Storage[(Object Storage)]
    PayGW[Payment Providers]
    LogisticsPartner[Logistics Partner]
    WS[Websocket Manager]

    Operator --> VendorAPI
    Operator --> LogisticsAPI
    Operator --> PaymentAPI
    Operator --> AdminAPI

    VendorAPI --> LabelService
    VendorAPI --> Payouts
    PaymentAPI --> Reconciliation
    LogisticsAPI --> LabelService
    AdminAPI --> LiveFeed

    LabelService --> Storage
    LabelService --> DB
    Payouts --> DB
    Reconciliation --> PayGW
    Reconciliation --> DB
    LogisticsAPI --> LogisticsPartner
    LiveFeed --> DB
    LiveFeed --> WS
    Notify --> WS
    Notify --> DB
```

---

## Current-Future Boundary

| Area | Current Repository State |
|------|--------------------------|
| Architecture | Monolith |
| Search | Database-backed filtering and fuzzy application-side ranking |
| Notifications | Persisted notifications plus websocket fanout |
| Payments | Khalti, eSewa, Stripe, PayPal, wallet, COD |
| Routing | Built-in nearest-neighbor + 2-opt optimization plus persisted courier GPS ingestion |
| Recommendations | Weighted feature ranker with diversity re-ranking |
| Future-only | Razorpay and external route optimization engines |
