# C4 Component Diagram

## Overview
Detailed C4 Component diagrams for key services showing internal structure at the component level.

---

## Product Service - Component Diagram

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph boundary["Product Service (Container: Node.js)"]
        subgraph "API Layer"
            ProductController["Product Controller<br><i>Component: Express Router</i><br>Handles product CRUD APIs"]
            CategoryController["Category Controller<br><i>Component: Express Router</i><br>Handles category APIs"]
            SearchController["Search Controller<br><i>Component: Express Router</i><br>Handles search APIs"]
        end
        
        subgraph "Application Layer"
            ProductManager["Product Manager<br><i>Component: Service</i><br>Product business logic"]
            CategoryManager["Category Manager<br><i>Component: Service</i><br>Category management"]
            SearchManager["Search Manager<br><i>Component: Service</i><br>Search orchestration"]
            ImageProcessor["Image Processor<br><i>Component: Service</i><br>Image resizing/optimization"]
        end
        
        subgraph "Domain Layer"
            ProductAggregate["Product Aggregate<br><i>Component: Domain Model</i><br>Product entity & rules"]
            VariantEntity["Variant Entity<br><i>Component: Domain Model</i><br>Product variants"]
            CategoryEntity["Category Entity<br><i>Component: Domain Model</i><br>Category hierarchy"]
        end
        
        subgraph "Infrastructure Layer"
            ProductRepository["Product Repository<br><i>Component: Repository</i><br>Product persistence"]
            CategoryRepository["Category Repository<br><i>Component: Repository</i><br>Category persistence"]
            SearchIndexer["Search Indexer<br><i>Component: Adapter</i><br>Elasticsearch indexing"]
            StorageClient["Storage Client<br><i>Component: Adapter</i><br>S3 file operations"]
            CacheManager["Cache Manager<br><i>Component: Adapter</i><br>Redis caching"]
        end
    end
    
    subgraph "External Systems"
        PostgreSQL[(PostgreSQL<br>Database)]
        Elasticsearch[(Elasticsearch<br>Search Engine)]
        Redis[(Redis<br>Cache)]
        S3[(S3<br>Object Storage)]
    end
    
    Gateway --> ProductController
    Gateway --> CategoryController
    Gateway --> SearchController
    
    ProductController --> ProductManager
    CategoryController --> CategoryManager
    SearchController --> SearchManager
    
    ProductManager --> ProductAggregate
    ProductManager --> ImageProcessor
    ProductAggregate --> VariantEntity
    CategoryManager --> CategoryEntity
    
    ProductAggregate --> ProductRepository
    CategoryEntity --> CategoryRepository
    SearchManager --> SearchIndexer
    ImageProcessor --> StorageClient
    ProductManager --> CacheManager
    
    ProductRepository --> PostgreSQL
    CategoryRepository --> PostgreSQL
    SearchIndexer --> Elasticsearch
    StorageClient --> S3
    CacheManager --> Redis
```

---

## Order Service - Component Diagram

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph boundary["Order Service (Container: Node.js)"]
        subgraph "API Layer"
            OrderController["Order Controller<br><i>Component: Express Router</i><br>Order management APIs"]
            CartController["Cart Controller<br><i>Component: Express Router</i><br>Cart operations APIs"]
            CheckoutController["Checkout Controller<br><i>Component: Express Router</i><br>Checkout flow APIs"]
        end
        
        subgraph "Application Layer"
            OrderManager["Order Manager<br><i>Component: Service</i><br>Order orchestration"]
            CartManager["Cart Manager<br><i>Component: Service</i><br>Cart operations"]
            CheckoutManager["Checkout Manager<br><i>Component: Service</i><br>Checkout flow"]
            OrderSplitter["Order Splitter<br><i>Component: Service</i><br>Multi-vendor splitting"]
            PricingEngine["Pricing Engine<br><i>Component: Service</i><br>Price calculation"]
            CouponProcessor["Coupon Processor<br><i>Component: Service</i><br>Coupon validation/apply"]
        end
        
        subgraph "Domain Layer"
            OrderAggregate["Order Aggregate<br><i>Component: Domain Model</i><br>Order entity & rules"]
            CartAggregate["Cart Aggregate<br><i>Component: Domain Model</i><br>Cart entity"]
            OrderItemEntity["OrderItem Entity<br><i>Component: Domain Model</i><br>Order line items"]
            VendorOrderEntity["VendorOrder Entity<br><i>Component: Domain Model</i><br>Vendor sub-orders"]
        end
        
        subgraph "Infrastructure Layer"
            OrderRepository["Order Repository<br><i>Component: Repository</i><br>Order persistence"]
            CartRepository["Cart Repository<br><i>Component: Repository</i><br>Cart persistence"]
            InventoryClient["Inventory Client<br><i>Component: HTTP Client</i><br>Inventory service calls"]
            PaymentClient["Payment Client<br><i>Component: HTTP Client</i><br>Payment service calls"]
            EventPublisher["Event Publisher<br><i>Component: Kafka Producer</i><br>Domain events"]
        end
    end
    
    subgraph "External Systems"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        InventoryService[Inventory Service]
        PaymentService[Payment Service]
        Kafka[Kafka]
    end
    
    Gateway --> OrderController
    Gateway --> CartController
    Gateway --> CheckoutController
    
    OrderController --> OrderManager
    CartController --> CartManager
    CheckoutController --> CheckoutManager
    
    OrderManager --> OrderSplitter
    CheckoutManager --> PricingEngine
    CheckoutManager --> CouponProcessor
    
    OrderManager --> OrderAggregate
    CartManager --> CartAggregate
    OrderAggregate --> OrderItemEntity
    OrderAggregate --> VendorOrderEntity
    
    OrderAggregate --> OrderRepository
    CartAggregate --> CartRepository
    CheckoutManager --> InventoryClient
    CheckoutManager --> PaymentClient
    OrderManager --> EventPublisher
    
    OrderRepository --> PostgreSQL
    CartRepository --> Redis
    InventoryClient --> InventoryService
    PaymentClient --> PaymentService
    EventPublisher --> Kafka
```

---

## Payment Service - Component Diagram

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph boundary["Payment Service (Container: Node.js)"]
        subgraph "API Layer"
            PaymentController["Payment Controller<br><i>Component: Express Router</i><br>Payment APIs"]
            WebhookHandler["Webhook Handler<br><i>Component: Express Router</i><br>Gateway callbacks"]
            RefundController["Refund Controller<br><i>Component: Express Router</i><br>Refund APIs"]
            PayoutController["Payout Controller<br><i>Component: Express Router</i><br>Vendor payout APIs"]
        end
        
        subgraph "Application Layer"
            PaymentManager["Payment Manager<br><i>Component: Service</i><br>Payment orchestration"]
            RefundManager["Refund Manager<br><i>Component: Service</i><br>Refund processing"]
            PayoutManager["Payout Manager<br><i>Component: Service</i><br>Vendor settlements"]
            ReconciliationEngine["Reconciliation Engine<br><i>Component: Service</i><br>Payment matching"]
        end
        
        subgraph "Gateway Adapters"
            GatewayFactory["Gateway Factory<br><i>Component: Factory</i><br>Gateway selection"]
            RazorpayAdapter["Razorpay Adapter<br><i>Component: Adapter</i><br>Razorpay integration"]
            StripeAdapter["Stripe Adapter<br><i>Component: Adapter</i><br>Stripe integration"]
        end
        
        subgraph "Security Layer"
            SignatureValidator["Signature Validator<br><i>Component: Security</i><br>Webhook verification"]
            Encryptor["Encryptor<br><i>Component: Security</i><br>Card data encryption"]
            FraudChecker["Fraud Checker<br><i>Component: Security</i><br>Fraud detection"]
        end
        
        subgraph "Infrastructure Layer"
            PaymentRepository["Payment Repository<br><i>Component: Repository</i><br>Transaction storage"]
            RefundRepository["Refund Repository<br><i>Component: Repository</i><br>Refund storage"]
            PayoutRepository["Payout Repository<br><i>Component: Repository</i><br>Payout storage"]
            BankClient["Bank Client<br><i>Component: HTTP Client</i><br>Bank transfers"]
            EventPublisher["Event Publisher<br><i>Component: Kafka Producer</i><br>Payment events"]
        end
    end
    
    subgraph "External Systems"
        PostgreSQL[(PostgreSQL)]
        Razorpay[Razorpay API]
        Stripe[Stripe API]
        Bank[Bank API]
        Kafka[Kafka]
    end
    
    Gateway --> PaymentController
    Razorpay --> WebhookHandler
    Stripe --> WebhookHandler
    Gateway --> RefundController
    Gateway --> PayoutController
    
    PaymentController --> PaymentManager
    WebhookHandler --> SignatureValidator
    SignatureValidator --> PaymentManager
    RefundController --> RefundManager
    PayoutController --> PayoutManager
    
    PaymentManager --> GatewayFactory
    PaymentManager --> Encryptor
    PaymentManager --> FraudChecker
    
    GatewayFactory --> RazorpayAdapter
    GatewayFactory --> StripeAdapter
    
    PaymentManager --> PaymentRepository
    RefundManager --> RefundRepository
    PayoutManager --> PayoutRepository
    PayoutManager --> BankClient
    PaymentManager --> EventPublisher
    
    RazorpayAdapter --> Razorpay
    StripeAdapter --> Stripe
    PaymentRepository --> PostgreSQL
    BankClient --> Bank
    EventPublisher --> Kafka
```

---

## Logistics Service - Component Diagram

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph boundary["Logistics Service (Container: Node.js)"]
        subgraph "API Layer"
            ShipmentController["Shipment Controller<br><i>Component: Express Router</i><br>Shipment APIs"]
            TrackingController["Tracking Controller<br><i>Component: Express Router</i><br>Tracking APIs"]
            HubController["Hub Controller<br><i>Component: Express Router</i><br>Hub operations APIs"]
            AgentController["Agent Controller<br><i>Component: Express Router</i><br>Agent APIs"]
        end
        
        subgraph "Application Layer"
            ShipmentManager["Shipment Manager<br><i>Component: Service</i><br>Shipment lifecycle"]
            LineHaulManager["Line Haul Manager<br><i>Component: Service</i><br>Inter-hub transfers"]
            DeliveryManager["Delivery Manager<br><i>Component: Service</i><br>Last mile delivery"]
            RouteOptimizer["Route Optimizer<br><i>Component: Service</i><br>Route planning"]
            AssignmentEngine["Assignment Engine<br><i>Component: Service</i><br>Agent assignment"]
        end
        
        subgraph "Domain Layer"
            ShipmentAggregate["Shipment Aggregate<br><i>Component: Domain Model</i><br>Shipment entity"]
            TripAggregate["Trip Aggregate<br><i>Component: Domain Model</i><br>Line haul trips"]
            ManifestEntity["Manifest Entity<br><i>Component: Domain Model</i><br>Package manifests"]
            AgentEntity["Agent Entity<br><i>Component: Domain Model</i><br>Delivery agents"]
        end
        
        subgraph "Infrastructure Layer"
            ShipmentRepository["Shipment Repository<br><i>Component: Repository</i><br>Shipment storage"]
            TrackingRepository["Tracking Repository<br><i>Component: Repository</i><br>Tracking events"]
            TripRepository["Trip Repository<br><i>Component: Repository</i><br>Trip storage"]
            MapsClient["Maps Client<br><i>Component: HTTP Client</i><br>Google Maps API"]
            PartnerClient["Partner Client<br><i>Component: HTTP Client</i><br>3PL APIs"]
            EventPublisher["Event Publisher<br><i>Component: Kafka Producer</i><br>Logistics events"]
        end
    end
    
    subgraph "External Systems"
        PostgreSQL[(PostgreSQL)]
        GoogleMaps[Google Maps API]
        ThreePL[3PL Partner APIs]
        Kafka[Kafka]
    end
    
    Gateway --> ShipmentController
    Gateway --> TrackingController
    Gateway --> HubController
    Gateway --> AgentController
    
    ShipmentController --> ShipmentManager
    TrackingController --> ShipmentManager
    HubController --> LineHaulManager
    AgentController --> DeliveryManager
    
    ShipmentManager --> RouteOptimizer
    DeliveryManager --> AssignmentEngine
    
    ShipmentManager --> ShipmentAggregate
    LineHaulManager --> TripAggregate
    TripAggregate --> ManifestEntity
    AssignmentEngine --> AgentEntity
    
    ShipmentAggregate --> ShipmentRepository
    ShipmentAggregate --> TrackingRepository
    TripAggregate --> TripRepository
    RouteOptimizer --> MapsClient
    ShipmentManager --> PartnerClient
    ShipmentManager --> EventPublisher
    
    ShipmentRepository --> PostgreSQL
    MapsClient --> GoogleMaps
    PartnerClient --> ThreePL
    EventPublisher --> Kafka
```

---

## Notification Service - Component Diagram

```mermaid
graph TB
    subgraph "Event Sources"
        Kafka[Kafka Event Bus]
    end
    
    subgraph boundary["Notification Service (Container: Python)"]
        subgraph "Consumer Layer"
            OrderEventConsumer["Order Event Consumer<br><i>Component: Kafka Consumer</i><br>Order notifications"]
            PaymentEventConsumer["Payment Event Consumer<br><i>Component: Kafka Consumer</i><br>Payment notifications"]
            ShipmentEventConsumer["Shipment Event Consumer<br><i>Component: Kafka Consumer</i><br>Delivery notifications"]
        end
        
        subgraph "Orchestration Layer"
            NotificationOrchestrator["Notification Orchestrator<br><i>Component: Service</i><br>Notification routing"]
            TemplateProcessor["Template Processor<br><i>Component: Service</i><br>Template rendering"]
            PreferenceChecker["Preference Checker<br><i>Component: Service</i><br>User preferences"]
            ThrottleController["Throttle Controller<br><i>Component: Service</i><br>Rate control"]
        end
        
        subgraph "Channel Layer"
            EmailChannel["Email Channel<br><i>Component: Channel</i><br>Email sending"]
            SMSChannel["SMS Channel<br><i>Component: Channel</i><br>SMS sending"]
            PushChannel["Push Channel<br><i>Component: Channel</i><br>Push notifications"]
            InAppChannel["In-App Channel<br><i>Component: Channel</i><br>In-app messages"]
        end
        
        subgraph "Provider Adapters"
            SendGridAdapter["SendGrid Adapter<br><i>Component: Adapter</i><br>SendGrid integration"]
            TwilioAdapter["Twilio Adapter<br><i>Component: Adapter</i><br>Twilio integration"]
            FCMAdapter["FCM Adapter<br><i>Component: Adapter</i><br>Firebase FCM"]
        end
        
        subgraph "Infrastructure Layer"
            NotificationRepository["Notification Repository<br><i>Component: Repository</i><br>Notification log"]
            TemplateRepository["Template Repository<br><i>Component: Repository</i><br>Template storage"]
            PreferenceRepository["Preference Repository<br><i>Component: Repository</i><br>User preferences"]
        end
    end
    
    subgraph "External Systems"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        SendGrid[SendGrid API]
        Twilio[Twilio API]
        FCM[Firebase FCM]
    end
    
    Kafka --> OrderEventConsumer
    Kafka --> PaymentEventConsumer
    Kafka --> ShipmentEventConsumer
    
    OrderEventConsumer --> NotificationOrchestrator
    PaymentEventConsumer --> NotificationOrchestrator
    ShipmentEventConsumer --> NotificationOrchestrator
    
    NotificationOrchestrator --> TemplateProcessor
    NotificationOrchestrator --> PreferenceChecker
    NotificationOrchestrator --> ThrottleController
    
    NotificationOrchestrator --> EmailChannel
    NotificationOrchestrator --> SMSChannel
    NotificationOrchestrator --> PushChannel
    NotificationOrchestrator --> InAppChannel
    
    EmailChannel --> SendGridAdapter
    SMSChannel --> TwilioAdapter
    PushChannel --> FCMAdapter
    
    NotificationRepository --> PostgreSQL
    TemplateRepository --> PostgreSQL
    PreferenceRepository --> PostgreSQL
    ThrottleController --> Redis
    
    SendGridAdapter --> SendGrid
    TwilioAdapter --> Twilio
    FCMAdapter --> FCM
```

---

## Component Summary Table

| Service | Components | Responsibilities |
|---------|------------|------------------|
| **Product Service** | Controller, Manager, Repository, Indexer, Cache | Product CRUD, search, caching |
| **Order Service** | Controller, Manager, Splitter, Pricing, Publisher | Order lifecycle, multi-vendor |
| **Payment Service** | Controller, Manager, Gateway Adapters, Security | Payment processing, refunds |
| **Logistics Service** | Controller, Manager, Optimizer, Assignment | Shipment, tracking, delivery |
| **Notification Service** | Consumers, Orchestrator, Channels, Adapters | Multi-channel notifications |
