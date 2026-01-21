# High-Level Architecture Diagram

## Overview
This document presents the high-level architecture of the e-commerce platform, showing major components and their interactions.

---

## System Architecture Overview

```mermaid
graph TB
    subgraph "Clients"
        WebApp[Web Application]
        MobileApp[Mobile Apps<br>iOS/Android]
        VendorApp[Vendor Portal]
        AdminApp[Admin Dashboard]
        AgentApp[Delivery Agent App]
    end
    
    subgraph "Edge Layer"
        CDN[CDN<br>CloudFront]
        WAF[WAF]
        LB[Load Balancer]
    end
    
    subgraph "API Layer"
        Gateway[API Gateway]
        Auth[Auth Service]
    end
    
    subgraph "Application Services"
        UserSvc[User Service]
        ProductSvc[Product Service]
        OrderSvc[Order Service]
        PaymentSvc[Payment Service]
        CartSvc[Cart Service]
        SearchSvc[Search Service]
        LogisticsSvc[Logistics Service]
        NotifSvc[Notification Service]
        VendorSvc[Vendor Service]
        AnalyticsSvc[Analytics Service]
    end
    
    subgraph "Data Layer"
        PrimaryDB[(PostgreSQL<br>Primary)]
        ReplicaDB[(PostgreSQL<br>Replicas)]
        Redis[(Redis<br>Cache)]
        Elastic[(Elasticsearch)]
        S3[(S3<br>Object Storage)]
    end
    
    subgraph "Message Layer"
        Kafka[Kafka<br>Event Streaming]
        RabbitMQ[RabbitMQ<br>Task Queue]
    end
    
    subgraph "External Services"
        PaymentGW[Payment Gateways]
        SMS[SMS Provider]
        Email[Email Provider]
        Push[Push Service]
        Maps[Maps API]
    end
    
    WebApp --> CDN
    MobileApp --> CDN
    VendorApp --> CDN
    AdminApp --> CDN
    AgentApp --> CDN
    
    CDN --> WAF
    WAF --> LB
    LB --> Gateway
    Gateway --> Auth
    
    Auth --> UserSvc
    Gateway --> ProductSvc
    Gateway --> OrderSvc
    Gateway --> PaymentSvc
    Gateway --> CartSvc
    Gateway --> SearchSvc
    Gateway --> LogisticsSvc
    Gateway --> VendorSvc
    
    UserSvc --> PrimaryDB
    ProductSvc --> PrimaryDB
    OrderSvc --> PrimaryDB
    PaymentSvc --> PrimaryDB
    VendorSvc --> PrimaryDB
    LogisticsSvc --> PrimaryDB
    
    ProductSvc --> ReplicaDB
    OrderSvc --> ReplicaDB
    AnalyticsSvc --> ReplicaDB
    
    UserSvc --> Redis
    CartSvc --> Redis
    ProductSvc --> Redis
    
    SearchSvc --> Elastic
    ProductSvc --> Elastic
    
    ProductSvc --> S3
    VendorSvc --> S3
    
    OrderSvc --> Kafka
    PaymentSvc --> Kafka
    LogisticsSvc --> Kafka
    
    NotifSvc --> RabbitMQ
    Kafka --> NotifSvc
    
    PaymentSvc --> PaymentGW
    NotifSvc --> SMS
    NotifSvc --> Email
    NotifSvc --> Push
    LogisticsSvc --> Maps
```

---

## Microservices Architecture

```mermaid
graph TB
    subgraph "Frontend Applications"
        FE1[Customer Web<br>Next.js]
        FE2[Customer Mobile<br>React Native]
        FE3[Vendor Portal<br>React]
        FE4[Admin Panel<br>React]
        FE5[Agent App<br>React Native]
    end
    
    subgraph "API Gateway Layer"
        Kong[Kong API Gateway]
        
        subgraph "Gateway Functions"
            RateLimit[Rate Limiting]
            AuthN[Authentication]
            Routing[Request Routing]
            Transform[Response Transform]
        end
    end
    
    subgraph "Core Services"
        direction LR
        
        subgraph "User Domain"
            UserSvc[User Service]
            AuthSvc[Auth Service]
        end
        
        subgraph "Catalog Domain"
            ProductSvc[Product Service]
            InventorySvc[Inventory Service]
            SearchSvc[Search Service]
        end
        
        subgraph "Order Domain"
            CartSvc[Cart Service]
            OrderSvc[Order Service]
            PaymentSvc[Payment Service]
        end
        
        subgraph "Vendor Domain"
            VendorSvc[Vendor Service]
            PayoutSvc[Payout Service]
        end
        
        subgraph "Logistics Domain"
            ShipmentSvc[Shipment Service]
            RoutingSvc[Routing Service]
            TrackingSvc[Tracking Service]
        end
        
        subgraph "Support Domain"
            NotifSvc[Notification Service]
            AnalyticsSvc[Analytics Service]
            ReportSvc[Reporting Service]
        end
    end
    
    subgraph "Shared Infrastructure"
        ConfigSvc[Config Service]
        DiscoverySvc[Service Discovery]
        TracingSvc[Distributed Tracing]
    end
    
    FE1 --> Kong
    FE2 --> Kong
    FE3 --> Kong
    FE4 --> Kong
    FE5 --> Kong
    
    Kong --> RateLimit
    RateLimit --> AuthN
    AuthN --> Routing
    Routing --> Transform
    
    Transform --> UserSvc
    Transform --> ProductSvc
    Transform --> OrderSvc
    Transform --> VendorSvc
    Transform --> ShipmentSvc
    
    UserSvc --> AuthSvc
    ProductSvc --> InventorySvc
    ProductSvc --> SearchSvc
    OrderSvc --> CartSvc
    OrderSvc --> PaymentSvc
    VendorSvc --> PayoutSvc
    ShipmentSvc --> RoutingSvc
    ShipmentSvc --> TrackingSvc
    
    OrderSvc --> NotifSvc
    PaymentSvc --> NotifSvc
    ShipmentSvc --> NotifSvc
```

---

## Service Communication Patterns

```mermaid
graph LR
    subgraph "Synchronous - REST/gRPC"
        A[Client] -->|Request| B[API Gateway]
        B -->|Forward| C[Service A]
        C -->|Query| D[Service B]
        D -->|Response| C
        C -->|Response| B
        B -->|Response| A
    end
```

```mermaid
graph LR
    subgraph "Asynchronous - Event-Driven"
        E[Order Service] -->|Publish| F[Event Bus<br>Kafka]
        F -->|Subscribe| G[Inventory Service]
        F -->|Subscribe| H[Notification Service]
        F -->|Subscribe| I[Analytics Service]
    end
```

---

## Data Architecture

```mermaid
graph TB
    subgraph "Write Path"
        App[Application] -->|Write| Primary[(Primary DB)]
        Primary -->|Replicate| Replica1[(Replica 1)]
        Primary -->|Replicate| Replica2[(Replica 2)]
        Primary -->|CDC| Kafka[Kafka]
        Kafka -->|Consume| Elastic[(Elasticsearch)]
        Kafka -->|Consume| Analytics[(Analytics DB)]
    end
    
    subgraph "Read Path"
        App2[Application] -->|Cache Miss| Redis[(Redis Cache)]
        Redis -->|Miss| Replica1
        App2 -->|Search| Elastic
        App2 -->|Heavy Reads| Replica1
    end
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js, React Native | Web and mobile apps |
| **API Gateway** | Kong / AWS API Gateway | Routing, auth, rate limiting |
| **Services** | Node.js / Python / Go | Business logic |
| **Database** | PostgreSQL | Primary data store |
| **Cache** | Redis | Session, cart, hot data |
| **Search** | Elasticsearch | Product search |
| **Message Queue** | Kafka, RabbitMQ | Event streaming, tasks |
| **Object Storage** | S3/GCS | Images, documents |
| **CDN** | CloudFront/Cloudflare | Static assets |
| **Container** | Docker, Kubernetes | Deployment |
| **Monitoring** | Prometheus, Grafana | Metrics |
| **Logging** | ELK Stack | Centralized logs |
| **Tracing** | Jaeger | Distributed tracing |

---

## Scalability Patterns

```mermaid
graph TB
    subgraph "Horizontal Scaling"
        LB[Load Balancer]
        LB --> S1[Service Instance 1]
        LB --> S2[Service Instance 2]
        LB --> S3[Service Instance 3]
        LB --> SN[Service Instance N]
    end
    
    subgraph "Database Scaling"
        Write[Write Operations] --> Primary[(Primary)]
        Primary --> R1[(Replica 1)]
        Primary --> R2[(Replica 2)]
        Read[Read Operations] --> R1
        Read --> R2
    end
    
    subgraph "Cache Strategy"
        App[Application]
        App -->|1. Check Cache| Cache[(Redis)]
        Cache -->|2. Cache Miss| DB[(Database)]
        DB -->|3. Populate Cache| Cache
        Cache -->|4. Return| App
    end
```

---

## Security Architecture

```mermaid
graph TB
    subgraph "Perimeter Security"
        Internet[Internet]
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
    end
    
    subgraph "Network Security"
        PublicSubnet[Public Subnet]
        PrivateSubnet[Private Subnet]
        DataSubnet[Data Subnet]
    end
    
    subgraph "Application Security"
        Gateway[API Gateway<br>JWT Validation]
        Services[Services<br>mTLS]
    end
    
    subgraph "Data Security"
        EncryptRest[Encryption at Rest<br>AES-256]
        EncryptTransit[Encryption in Transit<br>TLS 1.3]
        SecretMgmt[Secret Management<br>Vault]
    end
    
    Internet --> WAF
    WAF --> DDoS
    DDoS --> PublicSubnet
    PublicSubnet --> Gateway
    Gateway --> PrivateSubnet
    PrivateSubnet --> Services
    Services --> DataSubnet
    DataSubnet --> EncryptRest
    Services --> EncryptTransit
    Services --> SecretMgmt
```

---

## High Availability Design

```mermaid
graph TB
    subgraph "Region A - Primary"
        LB_A[Load Balancer]
        K8s_A[Kubernetes Cluster]
        DB_A[(Primary DB)]
        Cache_A[(Redis Primary)]
    end
    
    subgraph "Region B - DR"
        LB_B[Load Balancer]
        K8s_B[Kubernetes Cluster]
        DB_B[(Standby DB)]
        Cache_B[(Redis Replica)]
    end
    
    DNS[DNS - Route 53]
    
    DNS -->|Active| LB_A
    DNS -.->|Failover| LB_B
    
    LB_A --> K8s_A
    LB_B --> K8s_B
    
    K8s_A --> DB_A
    K8s_B --> DB_B
    
    K8s_A --> Cache_A
    K8s_B --> Cache_B
    
    DB_A -.->|Async Replication| DB_B
    Cache_A -.->|Sync| Cache_B
```
