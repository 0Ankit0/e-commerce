# Domain Model

## Overview
The Domain Model shows the key business entities and their relationships in the e-commerce system.

---

## Complete Domain Model

```mermaid
erDiagram
    USER ||--o{ ADDRESS : has
    USER ||--o{ ORDER : places
    USER ||--o{ CART : has
    USER ||--o{ WISHLIST : has
    USER ||--o{ REVIEW : writes
    USER ||--o{ WALLET : has
    
    VENDOR ||--o{ PRODUCT : sells
    VENDOR ||--o{ PAYOUT : receives
    VENDOR ||--|| BANK_ACCOUNT : has
    VENDOR ||--o{ WAREHOUSE : has
    
    PRODUCT ||--o{ PRODUCT_VARIANT : has
    PRODUCT }o--|| CATEGORY : belongs_to
    PRODUCT }o--|| BRAND : has
    PRODUCT ||--o{ PRODUCT_IMAGE : has
    PRODUCT ||--o{ REVIEW : has
    
    PRODUCT_VARIANT ||--o{ INVENTORY : tracked_in
    INVENTORY }o--|| WAREHOUSE : stored_at
    
    CART ||--o{ CART_ITEM : contains
    CART_ITEM }o--|| PRODUCT_VARIANT : references
    
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER_ITEM }o--|| PRODUCT_VARIANT : references
    ORDER ||--o{ SHIPMENT : has
    ORDER }o--o| COUPON : uses
    ORDER ||--|| PAYMENT : has
    ORDER }o--|| ADDRESS : delivered_to
    
    SHIPMENT ||--o{ SHIPMENT_TRACKING : has
    SHIPMENT }o--|| BRANCH : assigned_to
    SHIPMENT }o--o| DELIVERY_AGENT : delivered_by
    
    LINE_HAUL_TRIP ||--o{ SHIPMENT : contains
    LINE_HAUL_TRIP }o--|| HUB : origin
    LINE_HAUL_TRIP }o--|| HUB : destination
    LINE_HAUL_TRIP }o--|| VEHICLE : uses

    RETURN ||--|| ORDER_ITEM : for
    RETURN ||--|| REFUND : triggers
    
    ADMIN ||--o{ ADMIN_ROLE : has
    ADMIN_ROLE ||--o{ PERMISSION : grants
```

---

## User Domain

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String phone
        +String name
        +String passwordHash
        +UserType type
        +UserStatus status
        +DateTime createdAt
        +DateTime lastLoginAt
        +register()
        +login()
        +updateProfile()
        +resetPassword()
    }
    
    class Address {
        +UUID id
        +UUID userId
        +String name
        +String phone
        +String line1
        +String line2
        +String city
        +String state
        +String pincode
        +String country
        +String landmark
        +AddressType type
        +Boolean isDefault
        +validate()
        +checkServiceability()
    }
    
    class Wallet {
        +UUID id
        +UUID userId
        +Decimal balance
        +String currency
        +credit()
        +debit()
        +getTransactions()
    }
    
    class WalletTransaction {
        +UUID id
        +UUID walletId
        +TransactionType type
        +Decimal amount
        +String reference
        +DateTime createdAt
    }
    
    User "1" --> "*" Address
    User "1" --> "1" Wallet
    Wallet "1" --> "*" WalletTransaction
```

---

## Product Domain

```mermaid
classDiagram
    class Category {
        +UUID id
        +String name
        +String slug
        +UUID parentId
        +Integer level
        +String iconUrl
        +Boolean isActive
        +getProducts()
        +getSubcategories()
    }
    
    class Product {
        +UUID id
        +UUID vendorId
        +UUID categoryId
        +UUID brandId
        +String name
        +String slug
        +String description
        +ProductStatus status
        +Decimal avgRating
        +Integer reviewCount
        +DateTime createdAt
        +addVariant()
        +updateStock()
        +publish()
    }
    
    class ProductVariant {
        +UUID id
        +UUID productId
        +String sku
        +String name
        +Decimal mrp
        +Decimal sellingPrice
        +Decimal costPrice
        +JSON attributes
        +Boolean isActive
        +checkAvailability()
        +getPrice()
    }
    
    class ProductImage {
        +UUID id
        +UUID productId
        +String url
        +Integer position
        +Boolean isPrimary
    }
    
    class Inventory {
        +UUID id
        +UUID variantId
        +UUID warehouseId
        +Integer quantity
        +Integer reservedQty
        +Integer reorderLevel
        +reserve()
        +release()
        +deduct()
    }
    
    class Brand {
        +UUID id
        +String name
        +String logo
        +Boolean isActive
    }
    
    Category "1" --> "*" Product
    Product "1" --> "*" ProductVariant
    Product "1" --> "*" ProductImage
    Product "*" --> "1" Brand
    ProductVariant "1" --> "*" Inventory
```

---

## Order Domain

```mermaid
classDiagram
    class Cart {
        +UUID id
        +UUID userId
        +DateTime updatedAt
        +addItem()
        +removeItem()
        +updateQuantity()
        +getTotal()
        +checkout()
    }
    
    class CartItem {
        +UUID id
        +UUID cartId
        +UUID variantId
        +Integer quantity
        +Decimal priceAtAdd
    }
    
    class Order {
        +UUID id
        +String orderNumber
        +UUID userId
        +UUID addressId
        +OrderStatus status
        +Decimal subtotal
        +Decimal discount
        +Decimal shippingCharge
        +Decimal tax
        +Decimal total
        +PaymentStatus paymentStatus
        +DateTime createdAt
        +DateTime deliveredAt
        +splitByVendor()
        +cancel()
        +track()
    }
    
    class OrderItem {
        +UUID id
        +UUID orderId
        +UUID vendorId
        +UUID variantId
        +Integer quantity
        +Decimal unitPrice
        +Decimal totalPrice
        +OrderItemStatus status
        +markShipped()
        +markDelivered()
    }
    
    class Coupon {
        +UUID id
        +String code
        +CouponType type
        +Decimal value
        +Decimal minOrderValue
        +Decimal maxDiscount
        +DateTime validFrom
        +DateTime validTo
        +Integer usageLimit
        +Integer usedCount
        +validate()
        +apply()
    }
    
    Cart "1" --> "*" CartItem
    Order "1" --> "*" OrderItem
    Order "*" --> "0..1" Coupon
```

---

## Payment Domain

```mermaid
classDiagram
    class Payment {
        +UUID id
        +UUID orderId
        +String gatewayRef
        +PaymentMethod method
        +PaymentStatus status
        +Decimal amount
        +String currency
        +JSON gatewayResponse
        +DateTime createdAt
        +DateTime capturedAt
        +authorize()
        +capture()
        +refund()
    }
    
    class Refund {
        +UUID id
        +UUID paymentId
        +UUID returnId
        +String gatewayRef
        +Decimal amount
        +RefundStatus status
        +RefundMethod method
        +DateTime initiatedAt
        +DateTime completedAt
        +initiate()
        +process()
    }
    
    class VendorPayout {
        +UUID id
        +UUID vendorId
        +Decimal amount
        +Decimal commission
        +Decimal netAmount
        +PayoutStatus status
        +String bankRef
        +DateTime periodStart
        +DateTime periodEnd
        +DateTime processedAt
        +calculate()
        +process()
    }
    
    Payment "1" --> "*" Refund
```

---

## Logistics Domain

```mermaid
classDiagram
    class Shipment {
        +UUID id
        +String awb
        +UUID orderId
        +UUID vendorId
        +UUID branchId
        +ShipmentStatus status
        +ShipmentType type
        +Decimal weight
        +JSON dimensions
        +DateTime createdAt
        +DateTime dispatchedAt
        +DateTime deliveredAt
        +track()
        +updateStatus()
    }
    
    class ShipmentTracking {
        +UUID id
        +UUID shipmentId
        +String status
        +String location
        +String remarks
        +DateTime timestamp
    }
    
    class Hub {
        +UUID id
        +String name
        +String code
        +String address
        +String city
        +HubType type
        +Boolean isActive
        +getInbound()
        +getOutbound()
    }
    
    class Branch {
        +UUID id
        +UUID hubId
        +String name
        +String code
        +String address
        +String[] pincodes
        +Boolean isActive
        +assignAgent()
        +getDeliveries()
    }
    
    class DeliveryAgent {
        +UUID id
        +UUID branchId
        +String name
        +String phone
        +AgentStatus status
        +Integer capacity
        +Integer currentLoad
        +assignDelivery()
        +completeDelivery()
    }
    
    class LineHaulTrip {
        +UUID id
        +UUID originHubId
        +UUID destHubId
        +UUID vehicleId
        +TripStatus status
        +DateTime departureTime
        +DateTime arrivalTime
        +Integer packageCount
        +dispatch()
        +complete()
    }
    
    class Vehicle {
        +UUID id
        +String number
        +VehicleType type
        +Integer capacity
        +VehicleStatus status
    }
    
    Shipment "1" --> "*" ShipmentTracking
    Hub "1" --> "*" Branch
    Branch "1" --> "*" DeliveryAgent
    LineHaulTrip "*" --> "1" Hub : origin
    LineHaulTrip "*" --> "1" Hub : destination
    LineHaulTrip "*" --> "1" Vehicle
```

---

## Vendor Domain

```mermaid
classDiagram
    class Vendor {
        +UUID id
        +UUID userId
        +String businessName
        +String displayName
        +String gstin
        +String pan
        +VendorStatus status
        +Decimal rating
        +DateTime createdAt
        +DateTime approvedAt
        +submitForApproval()
        +activate()
        +suspend()
    }
    
    class BankAccount {
        +UUID id
        +UUID vendorId
        +String accountName
        +String accountNumber
        +String ifscCode
        +String bankName
        +Boolean isPrimary
        +Boolean isVerified
        +verify()
    }
    
    class Warehouse {
        +UUID id
        +UUID vendorId
        +String name
        +String address
        +String pincode
        +String city
        +Boolean isDefault
        +Boolean isActive
    }
    
    class VendorDocument {
        +UUID id
        +UUID vendorId
        +DocumentType type
        +String fileUrl
        +DocumentStatus status
        +String remarks
        +DateTime uploadedAt
        +DateTime verifiedAt
    }
    
    Vendor "1" --> "*" BankAccount
    Vendor "1" --> "*" Warehouse
    Vendor "1" --> "*" VendorDocument
```

---

## Enumeration Types

```mermaid
classDiagram
    class UserType {
        <<enumeration>>
        CUSTOMER
        VENDOR
        ADMIN
        DELIVERY_AGENT
        HUB_OPERATOR
    }
    
    class OrderStatus {
        <<enumeration>>
        PENDING
        CONFIRMED
        PROCESSING
        PACKED
        SHIPPED
        IN_TRANSIT
        OUT_FOR_DELIVERY
        DELIVERED
        CANCELLED
        RETURNED
    }
    
    class PaymentStatus {
        <<enumeration>>
        PENDING
        AUTHORIZED
        CAPTURED
        FAILED
        REFUNDED
        PARTIALLY_REFUNDED
    }
    
    class ShipmentStatus {
        <<enumeration>>
        CREATED
        PICKED_UP
        IN_TRANSIT
        AT_HUB
        OUT_FOR_DELIVERY
        DELIVERED
        RTO_INITIATED
        RTO_DELIVERED
    }
    
    class VendorStatus {
        <<enumeration>>
        PENDING_APPROVAL
        DOCUMENTS_REQUIRED
        APPROVED
        ACTIVE
        SUSPENDED
        DEACTIVATED
    }
```
