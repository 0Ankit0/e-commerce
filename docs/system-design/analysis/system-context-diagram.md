# System Context Diagram

## Overview
The System Context Diagram shows the e-commerce platform's boundaries and its interactions with external systems and actors.

---

## Main System Context Diagram

```mermaid
graph TB
    subgraph External Actors
        Customer((Customer))
        Vendor((Vendor))
        Admin((Admin))
        DeliveryAgent((Delivery Agent))
        HubOperator((Hub Operator))
    end
    
    subgraph External Systems
        PG[Payment Gateways<br>Razorpay/Stripe/PayPal]
        SMS[SMS Provider<br>Twilio/MSG91]
        Email[Email Service<br>SendGrid/SES]
        Push[Push Notification<br>Firebase/OneSignal]
        Maps[Maps Service<br>Google Maps/Mapbox]
        Analytics[Analytics<br>Google Analytics/Mixpanel]
        CDN[CDN<br>CloudFront/Cloudflare]
        Storage[Object Storage<br>S3/GCS]
        ERP[Vendor ERP Systems]
        Bank[Banking System]
    end
    
    subgraph "E-Commerce Platform"
        Platform[E-Commerce<br>Platform]
    end
    
    Customer -->|Browse, Order, Pay| Platform
    Vendor -->|Manage Products, Orders| Platform
    Admin -->|Configure, Monitor| Platform
    DeliveryAgent -->|Deliver, Update| Platform
    HubOperator -->|Process Shipments| Platform
    
    Platform -->|Process Payments| PG
    Platform -->|Send SMS/OTP| SMS
    Platform -->|Send Emails| Email
    Platform -->|Send Notifications| Push
    Platform -->|Location Services| Maps
    Platform -->|Track Events| Analytics
    Platform -->|Serve Static Content| CDN
    Platform -->|Store Files| Storage
    Platform <-->|Sync Inventory| ERP
    Platform -->|Payouts| Bank
```

---

## Detailed Context with Data Flows

```mermaid
graph LR
    subgraph Customers
        Web[Web Browser]
        MobileApp[Mobile App]
    end
    
    subgraph "E-Commerce Platform"
        API[API Gateway]
        Frontend[Web Frontend]
    end
    
    subgraph "Payment Ecosystem"
        PG[Payment Gateway]
        CC[Credit Card Networks]
        UPI[UPI/NPCI]
        Wallet[Digital Wallets]
    end
    
    subgraph "Communication"
        SMS[SMS Gateway]
        Email[Email Server]
        Push[Push Service]
    end
    
    subgraph "Logistics Partners"
        LP1[3PL Partner 1]
        LP2[3PL Partner 2]
        LP3[Own Fleet]
    end
    
    Web -->|HTTPS| Frontend
    MobileApp -->|REST/GraphQL| API
    Frontend --> API
    
    API -->|Payment Request| PG
    PG --> CC
    PG --> UPI
    PG --> Wallet
    
    API --> SMS
    API --> Email
    API --> Push
    
    API <-->|Shipment Data| LP1
    API <-->|Shipment Data| LP2
    API <-->|Shipment Data| LP3
```

---

## Integration Points Detail

### Payment Gateway Integration

```mermaid
sequenceDiagram
    participant C as Customer
    participant P as Platform
    participant PG as Payment Gateway
    participant Bank as Bank/Card Network
    
    C->>P: Initiate Payment
    P->>PG: Create Order
    PG-->>P: Order ID
    P-->>C: Redirect to Gateway
    C->>PG: Enter Payment Details
    PG->>Bank: Authorize
    Bank-->>PG: Auth Response
    PG-->>C: Redirect to Platform
    C->>P: Payment Callback
    P->>PG: Verify Payment
    PG-->>P: Payment Status
    P-->>C: Order Confirmation
```

### Logistics Partner Integration

```mermaid
sequenceDiagram
    participant V as Vendor
    participant P as Platform
    participant LP as Logistics Partner
    participant H as Hub
    participant DA as Delivery Agent
    
    V->>P: Order Packed
    P->>LP: Create Shipment
    LP-->>P: AWB Number
    P->>LP: Schedule Pickup
    LP->>V: Pickup Agent Arrives
    V->>LP: Handover Package
    LP-->>P: Pickup Confirmed
    LP->>H: Transit to Hub
    H->>LP: Received at Hub
    LP-->>P: At Hub
    H->>DA: Assign for Delivery
    DA->>C: Deliver Package
    DA->>LP: POD Captured
    LP-->>P: Delivered
```

---

## External System Dependencies

| System | Purpose | Integration Type | Criticality |
|--------|---------|------------------|-------------|
| Payment Gateway | Process payments | REST API | Critical |
| SMS Provider | OTP, notifications | REST API | High |
| Email Service | Transactional emails | SMTP/API | High |
| Push Notification | Mobile/web push | SDK/API | Medium |
| Maps API | Address, routing | REST API | Medium |
| CDN | Static assets | HTTP | High |
| Object Storage | Images, files | SDK | High |
| Analytics | User tracking | JS SDK | Low |
| ERP Systems | Vendor inventory sync | API/Webhook | Medium |
| Banking | Vendor payouts | API | High |

---

## Security Boundaries

```mermaid
graph TB
    subgraph "Public Zone"
        Internet[Internet]
        CDN[CDN]
    end
    
    subgraph "DMZ"
        WAF[Web Application Firewall]
        LB[Load Balancer]
        API[API Gateway]
    end
    
    subgraph "Application Zone"
        App[Application Servers]
        Cache[Redis Cache]
        Queue[Message Queue]
    end
    
    subgraph "Data Zone"
        DB[(Primary Database)]
        Replica[(Read Replicas)]
        Search[Search Engine]
    end
    
    subgraph "External Services"
        PG[Payment Gateway]
        SMS[SMS Provider]
    end
    
    Internet --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> API
    API --> App
    App --> Cache
    App --> Queue
    App --> DB
    App --> Replica
    App --> Search
    App -- Encrypted --> PG
    App -- Encrypted --> SMS
```
