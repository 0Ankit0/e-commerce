# Data Flow Diagrams

## Overview
These DFDs show the implemented data movement through the current backend.

---

## Level 0: Context Diagram

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))
    Agent((Agent))

    PaymentGW[Payment Providers]
    Logistics[Logistics Partner]
    Messaging[Email / SMS / Push]
    Maps[Maps Provider]

    subgraph "E-Commerce Platform"
        System[FastAPI Backend]
    end

    Customer -->|browse, checkout, track, return, wishlist| System
    Vendor -->|catalog, inventory, payouts, labels| System
    Admin -->|approvals, reports, live feed, content| System
    Agent -->|pickup and delivery updates| System

    System <-->|payment setup, verify, webhooks| PaymentGW
    System <-->|shipment creation and tracking| Logistics
    System -->|notifications| Messaging
    System -->|address lookup and ETA support| Maps
```

---

## Level 1: Major Subsystems

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))

    subgraph "Backend"
        IAM[Identity and Access]
        Catalog[Catalog and Search]
        Commerce[Cart, Wishlist, Pricing]
        Orders[Checkout, Orders, Returns]
        Payments[Payments and Refunds]
        Logistics[Shipments and Tracking]
        Vendors[Vendor Operations and Payouts]
        Support[Support, Reports, CMS]
        Notify[Notifications and Websockets]

        DB[(PostgreSQL)]
        Cache[(Redis)]
        Storage[(Object Storage)]
    end

    Customer --> IAM
    Customer --> Catalog
    Customer --> Commerce
    Customer --> Orders

    Vendor --> Catalog
    Vendor --> Vendors
    Vendor --> Logistics

    Admin --> Vendors
    Admin --> Orders
    Admin --> Support

    IAM <--> DB
    Catalog <--> DB
    Commerce <--> DB
    Orders <--> DB
    Payments <--> DB
    Logistics <--> DB
    Vendors <--> DB
    Support <--> DB
    Notify <--> DB

    Commerce <--> Cache
    Catalog <--> Cache
    IAM <--> Cache

    Catalog <--> Storage
    Logistics <--> Storage
    Support <--> Storage

    Orders --> Notify
    Payments --> Notify
    Logistics --> Notify
    Vendors --> Notify
    Commerce --> Notify
```

---

## Level 2: Checkout And Order Flow

```mermaid
flowchart TB
    Customer((Customer))

    Quote[1. Quote Builder]
    Checkout[2. Checkout Validation]
    Reserve[3. Inventory Reservation]
    Payment[4. Payment Setup / Confirmation]
    Order[5. Order Persistence]
    Timeline[6. Order Events]
    Notify[7. Notifications + Websocket]

    CartDB[(Cart / Commerce Data)]
    OrderDB[(Orders)]
    InventoryDB[(Inventory + Reservations)]
    PaymentDB[(Payments)]

    Customer -->|request quote| Quote
    Quote <-->|cart, tax, shipping, promotion rules| CartDB
    Quote -->|quoteFingerprint| Checkout

    Customer -->|submit checkout| Checkout
    Checkout -->|validate quote and idempotency| OrderDB
    Checkout --> Reserve
    Reserve <-->|reserve / release / commit| InventoryDB

    Checkout --> Payment
    Payment <-->|provider status| PaymentDB
    Payment --> Order
    Order --> OrderDB
    Order --> Timeline
    Timeline --> OrderDB
    Timeline --> Notify
```

---

## Level 2: Wishlist Sharing And Price-Drop Flow

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))

    Wishlist[Wishlist Module]
    Share[Share Link Manager]
    Catalog[Catalog Update Path]
    PriceHistory[Variant Price History]
    Notification[Price-Drop Notification Flow]

    CommerceDB[(Wishlist / Share Links)]
    CatalogDB[(Products / Variants)]
    NotifyDB[(Notifications)]

    Customer -->|save product| Wishlist
    Wishlist --> CommerceDB

    Customer -->|create share link| Share
    Share --> CommerceDB

    Vendor -->|change price| Catalog
    Catalog --> CatalogDB
    Catalog --> PriceHistory
    PriceHistory --> CatalogDB
    PriceHistory --> Notification
    Notification --> NotifyDB
    Notification -->|persisted alert + websocket event| Customer
```

---

## Level 2: Fulfillment, Shipping Labels, And Live Feed

```mermaid
flowchart TB
    Vendor((Vendor))
    Admin((Admin))
    Agent((Agent))

    Fulfillment[Vendor Fulfillment]
    Labels[Shipping Label Generator]
    Tracking[Shipment Tracking]
    Exceptions[Delivery Exceptions / RTO]
    Feed[Admin Live Feed]
    Notify[Notifications]

    ShipmentDB[(Shipments / Tracking)]
    Storage[(Object Storage)]
    OpsDB[(Order Events / Return Events / Payout Events)]

    Vendor -->|pack and request label| Fulfillment
    Fulfillment --> Labels
    Labels --> Storage
    Labels --> ShipmentDB

    Agent -->|pickup and delivery updates| Tracking
    Tracking --> ShipmentDB
    Tracking --> OpsDB

    Tracking --> Exceptions
    Exceptions --> ShipmentDB
    Exceptions --> OpsDB
    Exceptions --> Notify

    Feed <-->|recent operations| OpsDB
    Notify --> Admin
    Feed --> Admin
```

---

## Notes

| Area | Current State |
|------|---------------|
| Notifications | Generated automatically from domain mutations rather than manually triggered notification APIs |
| Shipping labels | Saved as backend-generated artifacts with stable URLs |
| Live operations feed | Aggregates persisted domain and audit events |
| Routing and GPS | Built-in route optimization and persisted courier GPS ingestion are part of the current backend scope |
| Future-only | External route optimization vendors remain outside current DFD scope |
