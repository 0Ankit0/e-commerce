# C4 Diagrams

## Overview
C4 (Context, Containers, Components, Code) diagrams provide a hierarchical way to describe architecture at different levels of abstraction.

---

## Level 1: System Context Diagram

```mermaid
graph TB
    Customer((Customer<br>👤))
    Vendor((Vendor<br>🏪))
    Admin((Admin<br>👨‍💼))
    Agent((Delivery Agent<br>🛵))
    
    subgraph "E-Commerce Platform"
        System[E-Commerce System<br>Enables online shopping,<br>vendor management, and<br>order fulfillment]
    end
    
    PaymentGW[Payment Gateway<br>📱 External System<br>Razorpay, Stripe]
    LogisticsPartner[Logistics Partner<br>🚚 External System<br>3PL Integration]
    NotificationSvc[Notification Services<br>📧 External System<br>SMS, Email, Push]
    MapsAPI[Maps Service<br>🗺️ External System<br>Google Maps]
    
    Customer -->|Browses products,<br>places orders,<br>tracks deliveries| System
    Vendor -->|Manages products,<br>fulfills orders,<br>views analytics| System
    Admin -->|Manages platform,<br>users, and settings| System
    Agent -->|Delivers orders,<br>captures POD| System
    
    System -->|Processes payments| PaymentGW
    System <-->|Creates shipments,<br>gets tracking| LogisticsPartner
    System -->|Sends notifications| NotificationSvc
    System -->|Gets directions,<br>calculates ETA| MapsAPI
    
    style System fill:#438DD5,color:#fff
    style PaymentGW fill:#999,color:#fff
    style LogisticsPartner fill:#999,color:#fff
    style NotificationSvc fill:#999,color:#fff
    style MapsAPI fill:#999,color:#fff
```

---

## Level 2: Container Diagram

```mermaid
graph TB
    Customer((Customer 👤))
    Vendor((Vendor 🏪))
    Admin((Admin 👨‍💼))
    Agent((Agent 🛵))
    
    subgraph "E-Commerce Platform"
        subgraph "Frontend Applications"
            WebApp[Customer Web App<br>Container: Next.js<br>Provides shopping experience]
            VendorPortal[Vendor Portal<br>Container: React<br>Product & order management]
            AdminDash[Admin Dashboard<br>Container: React<br>Platform management]
            AgentApp[Agent Mobile App<br>Container: React Native<br>Delivery management]
        end
        
        subgraph "API Layer"
            Gateway[API Gateway<br>Container: Kong<br>Routing, Auth, Rate Limiting]
        end
        
        subgraph "Microservices"
            UserSvc[User Service<br>Container: Node.js<br>Authentication & profiles]
            ProductSvc[Product Service<br>Container: Node.js<br>Catalog management]
            OrderSvc[Order Service<br>Container: Node.js<br>Order processing]
            PaymentSvc[Payment Service<br>Container: Node.js<br>Payment handling]
            LogSvc[Logistics Service<br>Container: Node.js<br>Shipping management]
            NotifSvc[Notification Service<br>Container: Python<br>Multi-channel notifications]
        end
        
        subgraph "Data Stores"
            DB[(PostgreSQL<br>Database<br>Primary data store)]
            Redis[(Redis<br>Cache<br>Sessions, caching)]
            Elastic[(Elasticsearch<br>Search Engine<br>Product search)]
            S3[(S3<br>Object Store<br>Images, files)]
        end
        
        subgraph "Message Bus"
            Kafka[Apache Kafka<br>Event Streaming<br>Async communication]
        end
    end
    
    PaymentGW[Payment Gateway]
    SMS[SMS Provider]
    Email[Email Provider]
    
    Customer --> WebApp
    Vendor --> VendorPortal
    Admin --> AdminDash
    Agent --> AgentApp
    
    WebApp --> Gateway
    VendorPortal --> Gateway
    AdminDash --> Gateway
    AgentApp --> Gateway
    
    Gateway --> UserSvc
    Gateway --> ProductSvc
    Gateway --> OrderSvc
    Gateway --> PaymentSvc
    Gateway --> LogSvc
    
    UserSvc --> DB
    ProductSvc --> DB
    OrderSvc --> DB
    PaymentSvc --> DB
    LogSvc --> DB
    
    UserSvc --> Redis
    ProductSvc --> Redis
    ProductSvc --> Elastic
    ProductSvc --> S3
    
    OrderSvc --> Kafka
    PaymentSvc --> Kafka
    LogSvc --> Kafka
    Kafka --> NotifSvc
    
    PaymentSvc --> PaymentGW
    NotifSvc --> SMS
    NotifSvc --> Email
    
    style WebApp fill:#438DD5,color:#fff
    style VendorPortal fill:#438DD5,color:#fff
    style AdminDash fill:#438DD5,color:#fff
    style AgentApp fill:#438DD5,color:#fff
    style Gateway fill:#438DD5,color:#fff
    style UserSvc fill:#438DD5,color:#fff
    style ProductSvc fill:#438DD5,color:#fff
    style OrderSvc fill:#438DD5,color:#fff
    style PaymentSvc fill:#438DD5,color:#fff
    style LogSvc fill:#438DD5,color:#fff
    style NotifSvc fill:#438DD5,color:#fff
```

---

## Level 3: Component Diagram - Order Service

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph "Order Service"
        subgraph "API Layer"
            OrderController[Order Controller<br>Component: Express Router<br>Handles HTTP requests]
            CartController[Cart Controller<br>Component: Express Router<br>Cart operations]
        end
        
        subgraph "Business Logic"
            OrderManager[Order Manager<br>Component: Service<br>Order orchestration]
            CartManager[Cart Manager<br>Component: Service<br>Cart management]
            CheckoutManager[Checkout Manager<br>Component: Service<br>Checkout flow]
            PricingEngine[Pricing Engine<br>Component: Service<br>Price calculation]
        end
        
        subgraph "Domain Layer"
            OrderRepo[Order Repository<br>Component: Repository<br>Order persistence]
            CartRepo[Cart Repository<br>Component: Repository<br>Cart persistence]
            OrderValidator[Order Validator<br>Component: Validator<br>Business rules]
        end
        
        subgraph "Integration"
            PaymentClient[Payment Client<br>Component: HTTP Client<br>Payment service calls]
            InventoryClient[Inventory Client<br>Component: HTTP Client<br>Stock checks]
            EventPublisher[Event Publisher<br>Component: Kafka Producer<br>Order events]
        end
    end
    
    subgraph "External"
        PaymentSvc[Payment Service]
        InventorySvc[Inventory Service]
        Kafka[Kafka]
        DB[(PostgreSQL)]
        Redis[(Redis)]
    end
    
    Gateway --> OrderController
    Gateway --> CartController
    
    OrderController --> OrderManager
    CartController --> CartManager
    OrderManager --> CheckoutManager
    CheckoutManager --> PricingEngine
    
    OrderManager --> OrderRepo
    OrderManager --> OrderValidator
    CartManager --> CartRepo
    
    CheckoutManager --> PaymentClient
    CheckoutManager --> InventoryClient
    OrderManager --> EventPublisher
    
    PaymentClient --> PaymentSvc
    InventoryClient --> InventorySvc
    EventPublisher --> Kafka
    OrderRepo --> DB
    CartRepo --> Redis
    
    style OrderController fill:#85BBF0,color:#000
    style CartController fill:#85BBF0,color:#000
    style OrderManager fill:#85BBF0,color:#000
    style CartManager fill:#85BBF0,color:#000
    style CheckoutManager fill:#85BBF0,color:#000
    style PricingEngine fill:#85BBF0,color:#000
    style OrderRepo fill:#85BBF0,color:#000
    style CartRepo fill:#85BBF0,color:#000
    style OrderValidator fill:#85BBF0,color:#000
    style PaymentClient fill:#85BBF0,color:#000
    style InventoryClient fill:#85BBF0,color:#000
    style EventPublisher fill:#85BBF0,color:#000
```

---

## Level 3: Component Diagram - Logistics Service

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph "Logistics Service"
        subgraph "API Layer"
            ShipmentController[Shipment Controller<br>Handles shipment APIs]
            TrackingController[Tracking Controller<br>Handles tracking APIs]
            HubController[Hub Controller<br>Handles hub operations]
        end
        
        subgraph "Business Logic"
            ShipmentManager[Shipment Manager<br>Shipment orchestration]
            RouteOptimizer[Route Optimizer<br>Route planning]
            AssignmentEngine[Assignment Engine<br>Agent assignment]
            LineHaulManager[Line Haul Manager<br>Inter-hub transfers]
        end
        
        subgraph "Domain Layer"
            ShipmentRepo[Shipment Repository<br>Shipment persistence]
            TrackingRepo[Tracking Repository<br>Tracking history]
            HubRepo[Hub Repository<br>Hub data]
            AgentRepo[Agent Repository<br>Agent data]
        end
        
        subgraph "Integration"
            MapsClient[Maps Client<br>Google Maps API]
            PartnerClient[Partner Client<br>3PL Integration]
            EventPublisher[Event Publisher<br>Kafka Producer]
        end
    end
    
    subgraph "External"
        MapsAPI[Google Maps API]
        ThreePL[3PL Partner API]
        Kafka[Kafka]
        DB[(PostgreSQL)]
    end
    
    Gateway --> ShipmentController
    Gateway --> TrackingController
    Gateway --> HubController
    
    ShipmentController --> ShipmentManager
    TrackingController --> ShipmentManager
    HubController --> LineHaulManager
    
    ShipmentManager --> RouteOptimizer
    ShipmentManager --> AssignmentEngine
    
    ShipmentManager --> ShipmentRepo
    ShipmentManager --> TrackingRepo
    LineHaulManager --> HubRepo
    AssignmentEngine --> AgentRepo
    
    RouteOptimizer --> MapsClient
    ShipmentManager --> PartnerClient
    ShipmentManager --> EventPublisher
    
    MapsClient --> MapsAPI
    PartnerClient --> ThreePL
    EventPublisher --> Kafka
    ShipmentRepo --> DB
    TrackingRepo --> DB
```

---

## Level 3: Component Diagram - Payment Service

```mermaid
graph TB
    subgraph "API Gateway"
        Gateway[Kong API Gateway]
    end
    
    subgraph "Payment Service"
        subgraph "API Layer"
            PaymentController[Payment Controller<br>Payment APIs]
            RefundController[Refund Controller<br>Refund APIs]
            WebhookHandler[Webhook Handler<br>Gateway callbacks]
        end
        
        subgraph "Business Logic"
            PaymentManager[Payment Manager<br>Payment orchestration]
            RefundManager[Refund Manager<br>Refund processing]
            PayoutManager[Payout Manager<br>Vendor payouts]
            ReconciliationEngine[Reconciliation<br>Settlement matching]
        end
        
        subgraph "Domain Layer"
            PaymentRepo[Payment Repository<br>Transaction storage]
            RefundRepo[Refund Repository<br>Refund storage]
            LedgerRepo[Ledger Repository<br>Financial records]
        end
        
        subgraph "Gateway Adapters"
            RazorpayAdapter[Razorpay Adapter<br>Razorpay integration]
            StripeAdapter[Stripe Adapter<br>Stripe integration]
            PayPalAdapter[PayPal Adapter<br>PayPal integration]
        end
        
        subgraph "Integration"
            EventPublisher[Event Publisher<br>Kafka Producer]
            BankClient[Bank Client<br>Bank transfers]
        end
    end
    
    subgraph "External"
        Razorpay[Razorpay API]
        Stripe[Stripe API]
        PayPal[PayPal API]
        Bank[Bank API]
        Kafka[Kafka]
        DB[(PostgreSQL)]
    end
    
    Gateway --> PaymentController
    Gateway --> RefundController
    Razorpay --> WebhookHandler
    Stripe --> WebhookHandler
    
    PaymentController --> PaymentManager
    RefundController --> RefundManager
    WebhookHandler --> PaymentManager
    
    PaymentManager --> PaymentRepo
    RefundManager --> RefundRepo
    PayoutManager --> LedgerRepo
    
    PaymentManager --> RazorpayAdapter
    PaymentManager --> StripeAdapter
    PaymentManager --> PayPalAdapter
    
    RazorpayAdapter --> Razorpay
    StripeAdapter --> Stripe
    PayPalAdapter --> PayPal
    
    PaymentManager --> EventPublisher
    PayoutManager --> BankClient
    
    EventPublisher --> Kafka
    BankClient --> Bank
    PaymentRepo --> DB
```

---

## Container Relationships Matrix

| Container | Depends On | Depended By |
|-----------|------------|-------------|
| **Customer Web App** | API Gateway | - |
| **Vendor Portal** | API Gateway | - |
| **Admin Dashboard** | API Gateway | - |
| **API Gateway** | All Services | All Frontends |
| **User Service** | PostgreSQL, Redis | Gateway, Order Service |
| **Product Service** | PostgreSQL, Elasticsearch, S3 | Gateway, Order Service |
| **Order Service** | PostgreSQL, Redis, Kafka | Gateway, Payment Service |
| **Payment Service** | PostgreSQL, Kafka, Payment Gateways | Order Service |
| **Logistics Service** | PostgreSQL, Kafka, Maps API | Order Service |
| **Notification Service** | Kafka, SMS/Email Providers | All Services |

---

## Deployment Context

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Public Subnets"
                ALB[Application Load Balancer]
                NAT[NAT Gateway]
            end
            
            subgraph "Private Subnets - Application"
                EKS[EKS Cluster]
                subgraph "Pods"
                    Gateway[API Gateway Pods]
                    Services[Microservice Pods]
                end
            end
            
            subgraph "Private Subnets - Data"
                RDS[(RDS PostgreSQL)]
                ElastiCache[(ElastiCache Redis)]
                OpenSearch[(OpenSearch)]
            end
        end
        
        S3[(S3 Buckets)]
        CloudFront[CloudFront CDN]
        MSK[Amazon MSK - Kafka]
        SES[Amazon SES]
        SNS[Amazon SNS]
    end
    
    Internet[Internet] --> CloudFront
    CloudFront --> ALB
    ALB --> Gateway
    Gateway --> Services
    Services --> RDS
    Services --> ElastiCache
    Services --> OpenSearch
    Services --> S3
    Services --> MSK
    Services --> SES
    Services --> SNS
    
    style EKS fill:#FF9900,color:#fff
    style RDS fill:#3B48CC,color:#fff
    style S3 fill:#569A31,color:#fff
```
