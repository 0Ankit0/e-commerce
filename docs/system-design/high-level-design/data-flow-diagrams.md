# Data Flow Diagrams

## Overview
Data Flow Diagrams (DFD) showing how data moves through the e-commerce system at different levels.

---

## Level 0: Context Diagram

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))
    
    PaymentGW[Payment Gateway]
    Logistics[Logistics Partner]
    Notifications[Notification Services]
    
    subgraph "E-Commerce System"
        System[E-Commerce Platform]
    end
    
    Customer -->|Orders, Payments, Profile| System
    System -->|Products, Order Status, Notifications| Customer
    
    Vendor -->|Products, Inventory, Order Updates| System
    System -->|Orders, Analytics, Payouts| Vendor
    
    Admin -->|Configuration, Approvals| System
    System -->|Reports, Alerts| Admin
    
    System <-->|Payment Processing| PaymentGW
    System <-->|Shipment Data| Logistics
    System -->|Send Notifications| Notifications
```

---

## Level 1: Major Subsystems

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))
    
    subgraph "E-Commerce Platform"
        UM[User Management]
        PC[Product Catalog]
        OM[Order Management]
        PM[Payment Module]
        LM[Logistics Module]
        NM[Notification Module]
        AM[Analytics Module]
        
        DB[(Database)]
        Cache[(Cache)]
        Search[(Search Engine)]
    end
    
    PaymentGW[Payment Gateway]
    LogisticsAPI[Logistics API]
    EmailSMS[Email/SMS Service]
    
    Customer -->|Register, Login| UM
    Customer -->|Browse, Search| PC
    Customer -->|Place Order| OM
    Customer -->|Pay| PM
    Customer -->|Track| LM
    
    Vendor -->|Manage Products| PC
    Vendor -->|Fulfill Orders| OM
    Vendor -->|View Analytics| AM
    
    Admin -->|Manage Users| UM
    Admin -->|Manage Catalog| PC
    Admin -->|View Reports| AM
    Admin -->|Configure Logistics| LM
    
    PC <--> Search
    UM <--> DB
    PC <--> DB
    OM <--> DB
    PM <--> DB
    LM <--> DB
    
    UM <--> Cache
    PC <--> Cache
    
    PM <--> PaymentGW
    LM <--> LogisticsAPI
    NM --> EmailSMS
    
    OM --> NM
    PM --> NM
    LM --> NM
```

---

## Level 2: Order Management DFD

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))
    
    subgraph "Order Management"
        direction TB
        
        Cart[1.1 Cart Management]
        Checkout[1.2 Checkout Process]
        Split[1.3 Order Splitting]
        Fulfill[1.4 Order Fulfillment]
        Track[1.5 Order Tracking]
        Return[1.6 Returns Processing]
    end
    
    CartDB[(Cart Store)]
    OrderDB[(Order Store)]
    InventoryDB[(Inventory)]
    
    PM[Payment Module]
    LM[Logistics Module]
    NM[Notification Module]
    
    Customer -->|Add/Remove Items| Cart
    Cart <-->|Cart Data| CartDB
    Cart -->|Cart Details| Checkout
    
    Checkout -->|Validate Stock| InventoryDB
    Checkout -->|Payment Request| PM
    PM -->|Payment Status| Checkout
    Checkout -->|Create Order| Split
    
    Split -->|Reserve Stock| InventoryDB
    Split -->|Vendor Orders| OrderDB
    Split -->|Notify| NM
    NM -->|Order Notification| Vendor
    
    Vendor -->|Accept/Pack| Fulfill
    Fulfill -->|Create Shipment| LM
    Fulfill -->|Update Status| OrderDB
    
    LM -->|Tracking Updates| Track
    Track <-->|Order Status| OrderDB
    Customer -->|View Status| Track
    
    Customer -->|Return Request| Return
    Return <-->|Return Data| OrderDB
    Return -->|Reverse Pickup| LM
    Return -->|Refund Request| PM
```

---

## Level 2: Payment DFD

```mermaid
flowchart TB
    Customer((Customer))
    Vendor((Vendor))
    Admin((Admin))
    
    subgraph "Payment Module"
        direction TB
        
        Init[2.1 Payment Initiation]
        Process[2.2 Payment Processing]
        Capture[2.3 Payment Capture]
        Refund[2.4 Refund Processing]
        Settlement[2.5 Vendor Settlement]
    end
    
    PaymentDB[(Payment Store)]
    WalletDB[(Wallet Store)]
    PayoutDB[(Payout Store)]
    
    PaymentGW[Payment Gateway]
    BankAPI[Bank API]
    
    Customer -->|Select Payment| Init
    Init -->|Customer, Amount| Process
    Process <-->|Payment Flow| PaymentGW
    Process -->|Gateway Response| Capture
    
    Capture -->|Store Transaction| PaymentDB
    Capture -->|Update Wallet| WalletDB
    Capture -->|Order Confirmed| OrderModule[Order Module]
    
    OrderModule -->|Refund Request| Refund
    Refund <-->|Process Refund| PaymentGW
    Refund -->|Update Transaction| PaymentDB
    Refund -->|Notify| Customer
    
    Admin -->|Trigger Payout| Settlement
    Settlement <-->|Payout History| PayoutDB
    Settlement <-->|Transfer Funds| BankAPI
    Settlement -->|Payout Confirmation| Vendor
```

---

## Level 2: Logistics DFD

```mermaid
flowchart TB
    Vendor((Vendor))
    Customer((Customer))
    Agent((Delivery Agent))
    HubOp((Hub Operator))
    
    subgraph "Logistics Module"
        direction TB
        
        Pickup[3.1 Pickup Management]
        LineHaul[3.2 Line Haul]
        Hub[3.3 Hub Operations]
        LastMile[3.4 Last Mile]
        Track[3.5 Tracking]
        RTO[3.6 RTO Management]
    end
    
    ShipmentDB[(Shipment Store)]
    RouteDB[(Route Store)]
    TrackingDB[(Tracking Store)]
    
    MapsAPI[Maps API]
    
    Vendor -->|Schedule Pickup| Pickup
    Pickup -->|Create Shipment| ShipmentDB
    Pickup -->|Pickup Complete| LineHaul
    
    LineHaul -->|Create Trip| RouteDB
    HubOp -->|Dispatch/Receive| LineHaul
    LineHaul -->|Update Location| TrackingDB
    LineHaul -->|Arrived at Hub| Hub
    
    HubOp -->|Sort/Process| Hub
    Hub -->|Update Status| ShipmentDB
    Hub -->|Assign to Branch| LastMile
    
    Agent -->|View Assignments| LastMile
    LastMile <-->|Route Optimization| MapsAPI
    Agent -->|Delivery Updates| LastMile
    LastMile -->|Update Status| ShipmentDB
    
    LastMile -->|Delivery Failed| RTO
    RTO -->|RTO Shipment| LineHaul
    
    Track <-->|Shipment Status| ShipmentDB
    Track <-->|Location Updates| TrackingDB
    Customer -->|Track Order| Track
```

---

## Level 2: Product Catalog DFD

```mermaid
flowchart TB
    Vendor((Vendor))
    Customer((Customer))
    Admin((Admin))
    
    subgraph "Product Catalog"
        direction TB
        
        Manage[4.1 Product Management]
        Inventory[4.2 Inventory Management]
        Search[4.3 Search & Discovery]
        Browse[4.4 Catalog Browsing]
        Moderate[4.5 Content Moderation]
    end
    
    ProductDB[(Product Store)]
    InventoryDB[(Inventory Store)]
    SearchEngine[(Elasticsearch)]
    CDN[(Image CDN)]
    
    Vendor -->|Create/Update Product| Manage
    Manage -->|Store Product| ProductDB
    Manage -->|Upload Images| CDN
    Manage -->|Index Product| SearchEngine
    Manage -->|Queue for Review| Moderate
    
    Vendor -->|Update Stock| Inventory
    Inventory <-->|Stock Data| InventoryDB
    Inventory -->|Low Stock Alert| Vendor
    
    Admin -->|Review Products| Moderate
    Moderate -->|Approve/Reject| ProductDB
    
    Customer -->|Search Query| Search
    Search <-->|Full Text Search| SearchEngine
    Search -->|Search Results| Customer
    
    Customer -->|Browse Category| Browse
    Browse <-->|Product List| ProductDB
    Browse <-->|Product Images| CDN
    Browse -->|Product Details| Customer
```

---

## Data Stores Summary

| Data Store | Description | Technology |
|------------|-------------|------------|
| User Store | User accounts, profiles, addresses | PostgreSQL |
| Product Store | Products, variants, categories, brands | PostgreSQL |
| Inventory Store | Stock levels per SKU per warehouse | PostgreSQL + Redis |
| Order Store | Orders, order items, status history | PostgreSQL |
| Cart Store | Shopping carts, cart items | Redis |
| Payment Store | Transactions, refunds, payouts | PostgreSQL |
| Shipment Store | Shipments, tracking, delivery | PostgreSQL |
| Session Store | User sessions, tokens | Redis |
| Search Index | Product search data | Elasticsearch |
| Cache | Frequently accessed data | Redis |
| File Storage | Images, documents | S3/GCS |
| Event Store | Async events, audit logs | Kafka/RabbitMQ |

---

## Data Flow Security

```mermaid
flowchart TB
    subgraph "Public Zone"
        Client[Client App]
    end
    
    subgraph "DMZ"
        WAF[WAF]
        LB[Load Balancer]
        API[API Gateway]
    end
    
    subgraph "Application Zone"
        Auth[Auth Service]
        Services[Microservices]
    end
    
    subgraph "Data Zone"
        DB[(Database)]
        Encrypted[Encrypted at Rest]
    end
    
    Client -->|HTTPS/TLS 1.3| WAF
    WAF -->|Filter Attacks| LB
    LB -->|Rate Limited| API
    API -->|JWT Validation| Auth
    Auth -->|Service Mesh| Services
    Services -->|Encrypted Connection| DB
    DB --> Encrypted
    
    style WAF fill:#f66
    style Encrypted fill:#6f6
```
