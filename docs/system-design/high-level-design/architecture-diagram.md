# High-Level Architecture Diagram

## Overview
This document summarizes the implemented backend architecture. The current codebase runs as a FastAPI monolith with domain modules, shared persistence, async notification tasks, websocket fanout, and external payment/logistics/maps integrations.

---

## System Architecture Overview

```mermaid
graph TB
    subgraph "Clients"
        WebApp[Customer Web]
        MobileApp[Customer Mobile]
        VendorApp[Vendor Portal]
        AdminApp[Admin Dashboard]
        AgentApp[Agent App]
    end

    subgraph "Edge"
        CDN[CDN]
        WAF[WAF]
        LB[Load Balancer]
    end

    subgraph "Application"
        API[FastAPI Monolith]

        subgraph "Backend Modules"
            IAM[IAM]
            Catalog[Catalog]
            Commerce[Cart, Wishlist, Pricing]
            Orders[Checkout, Orders, Returns]
            Payments[Payments, Refunds]
            Vendors[Vendors, Payouts]
            Logistics[Shipments, Tracking]
            Support[Support, CMS, Reports]
            Notify[Notifications + Websocket Fanout]
        end
    end

    subgraph "Data"
        DB[(PostgreSQL)]
        Redis[(Redis)]
        Storage[(Object Storage)]
    end

    subgraph "External Services"
        PaymentGW[Payment Providers]
        LogisticsPartner[Logistics Partner]
        Maps[Maps Provider]
        Messaging[Email / SMS / Push]
    end

    WebApp --> CDN
    MobileApp --> CDN
    VendorApp --> CDN
    AdminApp --> CDN
    AgentApp --> CDN

    CDN --> WAF
    WAF --> LB
    LB --> API

    API --> IAM
    API --> Catalog
    API --> Commerce
    API --> Orders
    API --> Payments
    API --> Vendors
    API --> Logistics
    API --> Support
    API --> Notify

    IAM --> DB
    Catalog --> DB
    Commerce --> DB
    Orders --> DB
    Payments --> DB
    Vendors --> DB
    Logistics --> DB
    Support --> DB
    Notify --> DB

    IAM --> Redis
    Catalog --> Redis
    Commerce --> Redis

    Catalog --> Storage
    Logistics --> Storage
    Support --> Storage

    Payments --> PaymentGW
    Logistics --> LogisticsPartner
    Commerce --> Maps
    Notify --> Messaging
```

---

## Runtime Interaction Model

```mermaid
graph LR
    Client[Client Request] --> API[FastAPI Router]
    API --> Domain[Domain Service / Repository]
    Domain --> DB[(PostgreSQL)]
    Domain --> Redis[(Redis)]

    Domain --> Event[Persisted Domain Event / Notification]
    Event --> Notify[Notification Dispatcher]
    Notify --> WS[Websocket Manager]
    Notify --> Msg[Email / SMS / Push]

    Domain --> External[Payment / Logistics / Maps Provider]
```

---

## Key Backend Responsibilities

| Module | Main Responsibilities |
|--------|-----------------------|
| IAM | JWT auth, OTP enable/verify/disable, privileged-account OTP readiness |
| Catalog | Product CRUD, search/filtering, CSV import, variant price history |
| Commerce | Cart, wishlist, share links, quote building, tax and shipping rules |
| Orders | Checkout, idempotency, order timelines, returns, invoice metadata |
| Payments | Initiation, verify/webhooks, refunds, reconciliation |
| Vendors | Onboarding, verification flow, payouts, settlement exports |
| Logistics | Shipment lifecycle, delivery exceptions, RTO, label artifacts |
| Support | Tickets, comments, SLA fields, reports, banners, static pages |
| Notifications | Persisted notifications, websocket fanout, low-stock and commerce events |

---

## Current Constraints

- The repository is documented as a monolith even where older design drafts discussed microservices.
- Search is implemented without a separate search engine dependency requirement.
- Route optimization, courier GPS ingestion, and recommendation ranking are implemented inside the FastAPI monolith. External routing engines and larger ML serving stacks remain optional future upgrades.
