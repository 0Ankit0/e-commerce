# System Context Diagram

## Overview
The system context below reflects the implemented backend and its external actors and dependencies.

---

## Main System Context Diagram

```mermaid
graph TB
    subgraph Actors
        Customer((Customer))
        Vendor((Vendor))
        Admin((Admin))
        DeliveryAgent((Delivery Agent))
        HubOperator((Hub Operator))
    end

    subgraph ExternalSystems
        PG[Payment Providers<br>Khalti / eSewa / Stripe / PayPal]
        SMS[SMS Provider]
        Email[Email Service]
        Push[Push Service]
        Maps[Maps Provider<br>OSM default / Google optional]
        Storage[Object Storage]
        ERP[Vendor ERP Systems]
        Bank[Banking / Payout System]
        Logistics[Logistics Partner]
    end

    subgraph "E-Commerce Platform"
        Platform[FastAPI Monolith]
    end

    Customer -->|browse, wishlist, checkout, track, return| Platform
    Vendor -->|catalog, inventory, orders, payouts, labels| Platform
    Admin -->|monitor, approve, moderate, report| Platform
    DeliveryAgent -->|pickup and delivery updates| Platform
    HubOperator -->|shipment and branch operations| Platform

    Platform -->|process and verify payments| PG
    Platform -->|OTP and notifications| SMS
    Platform -->|transactional emails| Email
    Platform -->|push and websocket-triggered notification fanout| Push
    Platform -->|address search and ETA support| Maps
    Platform -->|store media and shipping labels| Storage
    Platform <-->|inventory and catalog sync| ERP
    Platform -->|vendor settlements| Bank
    Platform <-->|shipments and tracking| Logistics
```

---

## Detailed Context With Data Flows

```mermaid
graph LR
    subgraph Clients
        Web[Web Client]
        Mobile[Mobile App]
        VendorUI[Vendor Portal]
        AdminUI[Admin Dashboard]
    end

    subgraph Platform
        API[REST API]
        WS[Websocket Manager]
    end

    subgraph Payments
        Khalti[Khalti]
        Esewa[eSewa]
        Stripe[Stripe]
        Paypal[PayPal]
    end

    subgraph Messaging
        SMS[SMS Gateway]
        Email[Email Provider]
        Push[Push Provider]
    end

    subgraph Operations
        Logistics[Logistics Partner]
        Maps[Maps Provider]
        Storage[Object Storage]
    end

    Web --> API
    Mobile --> API
    VendorUI --> API
    AdminUI --> API

    API --> WS
    API --> Khalti
    API --> Esewa
    API --> Stripe
    API --> Paypal
    API --> SMS
    API --> Email
    API --> Push
    API --> Logistics
    API --> Maps
    API --> Storage
```

---

## Security Boundaries

```mermaid
graph TB
    subgraph "Public Zone"
        Internet[Internet]
        CDN[CDN]
    end

    subgraph "Edge Zone"
        WAF[Web Application Firewall]
        LB[Load Balancer]
    end

    subgraph "Application Zone"
        API[FastAPI Application]
        Redis[Redis Cache]
        Worker[Async Task Worker]
        WS[Websocket Manager]
    end

    subgraph "Data Zone"
        DB[(Primary Database)]
        Storage[(Object Storage)]
    end

    subgraph "External Services"
        PG[Payment Providers]
        MSG[SMS / Email / Push]
        LOG[Logistics Partner]
    end

    Internet --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> API
    API --> Redis
    API --> Worker
    API --> WS
    API --> DB
    API --> Storage
    API -- TLS --> PG
    API -- TLS --> MSG
    API -- TLS --> LOG
```

---

## External Dependency Notes

| System | Purpose | Current Role |
|--------|---------|--------------|
| Payment providers | Charge, authorize, capture, refund | Implemented |
| SMS / Email / Push | OTP and transactional notifications | Implemented |
| Maps provider | Address autocomplete and ETA support | Implemented with OSM default |
| Object storage | Product media and shipping labels | Implemented |
| ERP sync | Vendor integration option | Partial / integration dependent |
| External route optimization | Advanced delivery planning | Future-only |
