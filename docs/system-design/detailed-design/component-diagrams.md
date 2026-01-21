# Component Diagrams

## Overview
Component diagrams showing the software module breakdown and dependencies.

---

## System Component Overview

```mermaid
graph TB
    subgraph "Client Layer"
        CustomerWeb[Customer Web App]
        VendorWeb[Vendor Portal]
        AdminWeb[Admin Dashboard]
        AgentMobile[Agent Mobile App]
    end
    
    subgraph "API Gateway Layer"
        Gateway[Kong API Gateway]
    end
    
    subgraph "Service Layer"
        subgraph "User Services"
            AuthSvc[Auth Service]
            UserSvc[User Service]
        end
        
        subgraph "Catalog Services"
            ProductSvc[Product Service]
            InventorySvc[Inventory Service]
            SearchSvc[Search Service]
        end
        
        subgraph "Order Services"
            CartSvc[Cart Service]
            OrderSvc[Order Service]
            CheckoutSvc[Checkout Service]
        end
        
        subgraph "Payment Services"
            PaymentSvc[Payment Service]
            RefundSvc[Refund Service]
            PayoutSvc[Payout Service]
        end
        
        subgraph "Logistics Services"
            ShipmentSvc[Shipment Service]
            RouteSvc[Route Service]
            TrackingSvc[Tracking Service]
            LineHaulSvc[Line Haul Service]
        end
        
        subgraph "Vendor Services"
            VendorMgmtSvc[Vendor Management]
            VendorOrderSvc[Vendor Order Service]
        end
        
        subgraph "Support Services"
            NotificationSvc[Notification Service]
            AnalyticsSvc[Analytics Service]
            MediaSvc[Media Service]
        end
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        Elasticsearch[(Elasticsearch)]
        S3[(S3)]
        Kafka[Kafka]
    end
    
    CustomerWeb --> Gateway
    VendorWeb --> Gateway
    AdminWeb --> Gateway
    AgentMobile --> Gateway
    
    Gateway --> AuthSvc
    Gateway --> UserSvc
    Gateway --> ProductSvc
    Gateway --> CartSvc
    Gateway --> OrderSvc
    Gateway --> PaymentSvc
    Gateway --> ShipmentSvc
    Gateway --> VendorMgmtSvc
    
    AuthSvc --> UserSvc
    ProductSvc --> InventorySvc
    ProductSvc --> SearchSvc
    OrderSvc --> CartSvc
    OrderSvc --> CheckoutSvc
    CheckoutSvc --> PaymentSvc
    CheckoutSvc --> InventorySvc
    PaymentSvc --> RefundSvc
    VendorMgmtSvc --> PayoutSvc
    ShipmentSvc --> RouteSvc
    ShipmentSvc --> TrackingSvc
    ShipmentSvc --> LineHaulSvc
    VendorMgmtSvc --> VendorOrderSvc
    
    UserSvc --> PostgreSQL
    UserSvc --> Redis
    ProductSvc --> PostgreSQL
    ProductSvc --> Elasticsearch
    ProductSvc --> S3
    InventorySvc --> PostgreSQL
    InventorySvc --> Redis
    CartSvc --> Redis
    OrderSvc --> PostgreSQL
    OrderSvc --> Kafka
    PaymentSvc --> PostgreSQL
    PaymentSvc --> Kafka
    ShipmentSvc --> PostgreSQL
    ShipmentSvc --> Kafka
    NotificationSvc --> Kafka
    AnalyticsSvc --> PostgreSQL
```

---

## Auth Service Components

```mermaid
graph TB
    subgraph "Auth Service"
        subgraph "API"
            AuthController[Auth Controller]
            OAuthController[OAuth Controller]
        end
        
        subgraph "Core"
            AuthManager[Auth Manager]
            TokenManager[Token Manager]
            SessionManager[Session Manager]
            PasswordManager[Password Manager]
        end
        
        subgraph "Providers"
            LocalAuth[Local Auth Provider]
            GoogleAuth[Google OAuth Provider]
            FacebookAuth[Facebook OAuth Provider]
        end
        
        subgraph "Security"
            JWTHandler[JWT Handler]
            OTPHandler[OTP Handler]
            RateLimiter[Rate Limiter]
        end
        
        subgraph "Repository"
            UserRepo[User Repository]
            SessionRepo[Session Repository]
            TokenRepo[Token Repository]
        end
    end
    
    subgraph "External"
        Redis[(Redis)]
        PostgreSQL[(PostgreSQL)]
        SMSProvider[SMS Provider]
    end
    
    AuthController --> AuthManager
    OAuthController --> AuthManager
    
    AuthManager --> TokenManager
    AuthManager --> SessionManager
    AuthManager --> PasswordManager
    
    AuthManager --> LocalAuth
    AuthManager --> GoogleAuth
    AuthManager --> FacebookAuth
    
    TokenManager --> JWTHandler
    AuthManager --> OTPHandler
    AuthController --> RateLimiter
    
    UserRepo --> PostgreSQL
    SessionRepo --> Redis
    TokenRepo --> Redis
    OTPHandler --> SMSProvider
```

---

## Order Service Components

```mermaid
graph TB
    subgraph "Order Service"
        subgraph "API"
            OrderController[Order Controller]
            CartController[Cart Controller]
            CheckoutController[Checkout Controller]
        end
        
        subgraph "Business Logic"
            OrderManager[Order Manager]
            CartManager[Cart Manager]
            CheckoutManager[Checkout Manager]
            OrderSplitter[Order Splitter]
            PricingEngine[Pricing Engine]
        end
        
        subgraph "Validation"
            OrderValidator[Order Validator]
            CouponValidator[Coupon Validator]
            AddressValidator[Address Validator]
        end
        
        subgraph "Domain"
            OrderAggregate[Order Aggregate]
            CartAggregate[Cart Aggregate]
            CouponEntity[Coupon Entity]
        end
        
        subgraph "Repository"
            OrderRepo[Order Repository]
            CartRepo[Cart Repository]
            CouponRepo[Coupon Repository]
        end
        
        subgraph "Integration"
            InventoryClient[Inventory Client]
            PaymentClient[Payment Client]
            VendorClient[Vendor Client]
            EventPublisher[Event Publisher]
        end
    end
    
    subgraph "External Services"
        InventorySvc[Inventory Service]
        PaymentSvc[Payment Service]
        VendorSvc[Vendor Service]
        Kafka[Kafka]
    end
    
    subgraph "Data Stores"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
    end
    
    OrderController --> OrderManager
    CartController --> CartManager
    CheckoutController --> CheckoutManager
    
    OrderManager --> OrderSplitter
    OrderManager --> OrderValidator
    CheckoutManager --> PricingEngine
    CheckoutManager --> CouponValidator
    CheckoutManager --> AddressValidator
    
    OrderManager --> OrderAggregate
    CartManager --> CartAggregate
    
    OrderAggregate --> OrderRepo
    CartAggregate --> CartRepo
    CouponValidator --> CouponRepo
    
    CheckoutManager --> InventoryClient
    CheckoutManager --> PaymentClient
    OrderSplitter --> VendorClient
    OrderManager --> EventPublisher
    
    InventoryClient --> InventorySvc
    PaymentClient --> PaymentSvc
    VendorClient --> VendorSvc
    EventPublisher --> Kafka
    
    OrderRepo --> PostgreSQL
    CartRepo --> Redis
```

---

## Payment Service Components

```mermaid
graph TB
    subgraph "Payment Service"
        subgraph "API"
            PaymentController[Payment Controller]
            WebhookController[Webhook Controller]
            RefundController[Refund Controller]
            PayoutController[Payout Controller]
        end
        
        subgraph "Business Logic"
            PaymentManager[Payment Manager]
            RefundManager[Refund Manager]
            PayoutManager[Payout Manager]
            ReconciliationEngine[Reconciliation Engine]
        end
        
        subgraph "Gateway Adapters"
            GatewayFactory[Gateway Factory]
            RazorpayAdapter[Razorpay Adapter]
            StripeAdapter[Stripe Adapter]
            PayPalAdapter[PayPal Adapter]
        end
        
        subgraph "Security"
            SignatureVerifier[Signature Verifier]
            EncryptionHandler[Encryption Handler]
            FraudDetector[Fraud Detector]
        end
        
        subgraph "Repository"
            PaymentRepo[Payment Repository]
            RefundRepo[Refund Repository]
            PayoutRepo[Payout Repository]
            LedgerRepo[Ledger Repository]
        end
        
        subgraph "Integration"
            OrderClient[Order Client]
            VendorClient[Vendor Client]
            BankClient[Bank Client]
            EventPublisher[Event Publisher]
        end
    end
    
    subgraph "External"
        Razorpay[Razorpay API]
        Stripe[Stripe API]
        PayPal[PayPal API]
        Bank[Bank API]
        Kafka[Kafka]
        PostgreSQL[(PostgreSQL)]
    end
    
    PaymentController --> PaymentManager
    WebhookController --> PaymentManager
    RefundController --> RefundManager
    PayoutController --> PayoutManager
    
    PaymentManager --> GatewayFactory
    RefundManager --> GatewayFactory
    
    GatewayFactory --> RazorpayAdapter
    GatewayFactory --> StripeAdapter
    GatewayFactory --> PayPalAdapter
    
    WebhookController --> SignatureVerifier
    PaymentManager --> EncryptionHandler
    PaymentManager --> FraudDetector
    
    PaymentManager --> PaymentRepo
    RefundManager --> RefundRepo
    PayoutManager --> PayoutRepo
    ReconciliationEngine --> LedgerRepo
    
    PaymentManager --> OrderClient
    PayoutManager --> VendorClient
    PayoutManager --> BankClient
    PaymentManager --> EventPublisher
    
    RazorpayAdapter --> Razorpay
    StripeAdapter --> Stripe
    PayPalAdapter --> PayPal
    BankClient --> Bank
    EventPublisher --> Kafka
    
    PaymentRepo --> PostgreSQL
    RefundRepo --> PostgreSQL
    PayoutRepo --> PostgreSQL
```

---

## Logistics Service Components

```mermaid
graph TB
    subgraph "Logistics Service"
        subgraph "API"
            ShipmentController[Shipment Controller]
            TrackingController[Tracking Controller]
            HubController[Hub Controller]
            AgentController[Agent Controller]
        end
        
        subgraph "Business Logic"
            ShipmentManager[Shipment Manager]
            LineHaulManager[Line Haul Manager]
            DeliveryManager[Delivery Manager]
            RouteOptimizer[Route Optimizer]
            AssignmentEngine[Assignment Engine]
        end
        
        subgraph "Domain"
            ShipmentAggregate[Shipment Aggregate]
            TripAggregate[Trip Aggregate]
            ManifestEntity[Manifest Entity]
            AgentEntity[Agent Entity]
        end
        
        subgraph "Repository"
            ShipmentRepo[Shipment Repository]
            TrackingRepo[Tracking Repository]
            HubRepo[Hub Repository]
            AgentRepo[Agent Repository]
            TripRepo[Trip Repository]
        end
        
        subgraph "Integration"
            PartnerClient[Partner API Client]
            MapsClient[Maps API Client]
            OrderClient[Order Client]
            EventPublisher[Event Publisher]
        end
    end
    
    subgraph "External"
        ThreePL[3PL Partner APIs]
        GoogleMaps[Google Maps API]
        OrderSvc[Order Service]
        Kafka[Kafka]
        PostgreSQL[(PostgreSQL)]
    end
    
    ShipmentController --> ShipmentManager
    TrackingController --> ShipmentManager
    HubController --> LineHaulManager
    AgentController --> DeliveryManager
    
    ShipmentManager --> RouteOptimizer
    DeliveryManager --> AssignmentEngine
    
    ShipmentManager --> ShipmentAggregate
    LineHaulManager --> TripAggregate
    LineHaulManager --> ManifestEntity
    AssignmentEngine --> AgentEntity
    
    ShipmentAggregate --> ShipmentRepo
    ShipmentAggregate --> TrackingRepo
    TripAggregate --> TripRepo
    AgentEntity --> AgentRepo
    
    ShipmentManager --> PartnerClient
    RouteOptimizer --> MapsClient
    ShipmentManager --> OrderClient
    ShipmentManager --> EventPublisher
    
    PartnerClient --> ThreePL
    MapsClient --> GoogleMaps
    OrderClient --> OrderSvc
    EventPublisher --> Kafka
    
    ShipmentRepo --> PostgreSQL
```

---

## Notification Service Components

```mermaid
graph TB
    subgraph "Notification Service"
        subgraph "Event Consumers"
            OrderConsumer[Order Event Consumer]
            PaymentConsumer[Payment Event Consumer]
            ShipmentConsumer[Shipment Event Consumer]
        end
        
        subgraph "Orchestration"
            NotificationManager[Notification Manager]
            TemplateEngine[Template Engine]
            PreferenceManager[Preference Manager]
            ThrottleManager[Throttle Manager]
        end
        
        subgraph "Channels"
            EmailChannel[Email Channel]
            SMSChannel[SMS Channel]
            PushChannel[Push Channel]
            InAppChannel[In-App Channel]
        end
        
        subgraph "Providers"
            SendGridProvider[SendGrid Provider]
            SESProvider[AWS SES Provider]
            TwilioProvider[Twilio Provider]
            FCMProvider[Firebase FCM Provider]
        end
        
        subgraph "Repository"
            NotificationRepo[Notification Repository]
            TemplateRepo[Template Repository]
            PreferenceRepo[Preference Repository]
        end
    end
    
    subgraph "External"
        Kafka[Kafka]
        SendGrid[SendGrid API]
        Twilio[Twilio API]
        FCM[Firebase FCM]
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
    end
    
    Kafka --> OrderConsumer
    Kafka --> PaymentConsumer
    Kafka --> ShipmentConsumer
    
    OrderConsumer --> NotificationManager
    PaymentConsumer --> NotificationManager
    ShipmentConsumer --> NotificationManager
    
    NotificationManager --> TemplateEngine
    NotificationManager --> PreferenceManager
    NotificationManager --> ThrottleManager
    
    NotificationManager --> EmailChannel
    NotificationManager --> SMSChannel
    NotificationManager --> PushChannel
    NotificationManager --> InAppChannel
    
    EmailChannel --> SendGridProvider
    EmailChannel --> SESProvider
    SMSChannel --> TwilioProvider
    PushChannel --> FCMProvider
    
    SendGridProvider --> SendGrid
    TwilioProvider --> Twilio
    FCMProvider --> FCM
    
    NotificationRepo --> PostgreSQL
    TemplateRepo --> PostgreSQL
    PreferenceRepo --> PostgreSQL
    ThrottleManager --> Redis
```

---

## Component Dependencies Matrix

| Component | Depends On | Depended By |
|-----------|------------|-------------|
| Auth Service | User Service, Redis | All Services |
| User Service | PostgreSQL, Redis | Auth, Order, Vendor |
| Product Service | PostgreSQL, Elasticsearch, S3 | Search, Cart, Order |
| Inventory Service | PostgreSQL, Redis | Product, Order, Checkout |
| Cart Service | Redis | Order, Checkout |
| Order Service | PostgreSQL, Kafka | Payment, Shipment, Notification |
| Payment Service | PostgreSQL, Kafka, Gateways | Order, Refund |
| Shipment Service | PostgreSQL, Kafka, Maps | Order, Notification |
| Notification Service | Kafka, Email/SMS/Push | - |
| Analytics Service | PostgreSQL, Kafka | - |
