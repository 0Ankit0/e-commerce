# Class Diagrams

## Overview
Detailed class diagrams showing classes, methods, attributes, and relationships for key components.

---

## User Domain Classes

```mermaid
classDiagram
    class User {
        -UUID id
        -String email
        -String phone
        -String passwordHash
        -String name
        -UserType type
        -UserStatus status
        -DateTime createdAt
        -DateTime updatedAt
        -DateTime lastLoginAt
        +register(email, password, name) User
        +login(email, password) AuthToken
        +logout() void
        +updateProfile(data) User
        +changePassword(oldPass, newPass) void
        +resetPassword(token, newPass) void
        +requestPasswordReset(email) void
        +verifyEmail(token) void
        +verifyPhone(otp) void
    }
    
    class Address {
        -UUID id
        -UUID userId
        -String name
        -String phone
        -String addressLine1
        -String addressLine2
        -String city
        -String state
        -String pincode
        -String country
        -String landmark
        -AddressType type
        -Boolean isDefault
        -Float latitude
        -Float longitude
        -DateTime createdAt
        +validate() Boolean
        +checkServiceability() ServiceabilityResult
        +setAsDefault() void
        +geocode() void
    }
    
    class AuthToken {
        -String accessToken
        -String refreshToken
        -DateTime expiresAt
        -String tokenType
        +isExpired() Boolean
        +refresh() AuthToken
        +revoke() void
    }
    
    class Session {
        -UUID id
        -UUID userId
        -String deviceId
        -String ipAddress
        -String userAgent
        -DateTime createdAt
        -DateTime lastActiveAt
        +isActive() Boolean
        +terminate() void
    }
    
    class Wallet {
        -UUID id
        -UUID userId
        -Decimal balance
        -String currency
        -DateTime updatedAt
        +credit(amount, reference) Transaction
        +debit(amount, reference) Transaction
        +getBalance() Decimal
        +getTransactions(page, limit) Transaction[]
    }
    
    class WalletTransaction {
        -UUID id
        -UUID walletId
        -TransactionType type
        -Decimal amount
        -Decimal balanceAfter
        -String reference
        -String description
        -DateTime createdAt
    }
    
    User "1" --> "*" Address : has
    User "1" --> "1" Wallet : has
    User "1" --> "*" Session : has
    Wallet "1" --> "*" WalletTransaction : has
```

---

## Product Domain Classes

```mermaid
classDiagram
    class Category {
        -UUID id
        -String name
        -String slug
        -UUID parentId
        -Integer level
        -String description
        -String iconUrl
        -String imageUrl
        -Integer sortOrder
        -Boolean isActive
        -JSON attributes
        -DateTime createdAt
        +getProducts(filters, page) Product[]
        +getSubcategories() Category[]
        +getPath() Category[]
        +updateAttributes(attrs) void
    }
    
    class Product {
        -UUID id
        -UUID vendorId
        -UUID categoryId
        -UUID brandId
        -String name
        -String slug
        -String shortDescription
        -String description
        -JSON specifications
        -ProductStatus status
        -Decimal avgRating
        -Integer reviewCount
        -Integer viewCount
        -Boolean isFeatured
        -DateTime createdAt
        -DateTime updatedAt
        -DateTime publishedAt
        +addVariant(data) ProductVariant
        +removeVariant(variantId) void
        +addImage(url, position) ProductImage
        +publish() void
        +unpublish() void
        +updateStock(variantId, quantity) void
        +getPrice() PriceRange
    }
    
    class ProductVariant {
        -UUID id
        -UUID productId
        -String sku
        -String name
        -Decimal mrp
        -Decimal sellingPrice
        -Decimal costPrice
        -JSON attributes
        -Decimal weight
        -JSON dimensions
        -Boolean isDefault
        -Boolean isActive
        -DateTime createdAt
        +getStock(warehouseId) Integer
        +getAvailableStock() Integer
        +reserveStock(quantity) Boolean
        +releaseStock(quantity) void
        +getDiscountPercent() Decimal
    }
    
    class ProductImage {
        -UUID id
        -UUID productId
        -String url
        -String thumbnailUrl
        -String altText
        -Integer position
        -Boolean isPrimary
        -DateTime createdAt
    }
    
    class Inventory {
        -UUID id
        -UUID variantId
        -UUID warehouseId
        -Integer quantity
        -Integer reservedQuantity
        -Integer reorderLevel
        -Integer reorderQuantity
        -DateTime lastRestockedAt
        -DateTime updatedAt
        +getAvailable() Integer
        +reserve(quantity) Boolean
        +release(quantity) void
        +deduct(quantity) void
        +restock(quantity) void
        +isLowStock() Boolean
    }
    
    class Brand {
        -UUID id
        -String name
        -String slug
        -String logoUrl
        -String description
        -Boolean isActive
        -DateTime createdAt
    }
    
    class Review {
        -UUID id
        -UUID productId
        -UUID userId
        -UUID orderId
        -Integer rating
        -String title
        -String content
        -String[] images
        -ReviewStatus status
        -Integer helpfulCount
        -DateTime createdAt
        +markHelpful(userId) void
        +moderate(status) void
    }
    
    Category "1" --> "*" Product
    Product "1" --> "*" ProductVariant
    Product "1" --> "*" ProductImage
    Product "*" --> "1" Brand
    Product "1" --> "*" Review
    ProductVariant "1" --> "*" Inventory
```

---

## Order Domain Classes

```mermaid
classDiagram
    class Cart {
        -UUID id
        -UUID userId
        -String sessionId
        -DateTime createdAt
        -DateTime updatedAt
        +addItem(variantId, quantity) CartItem
        +removeItem(itemId) void
        +updateQuantity(itemId, quantity) void
        +clear() void
        +getItems() CartItem[]
        +getTotal() CartTotal
        +applyCoupon(code) DiscountResult
        +removeCoupon() void
        +checkout() Order
    }
    
    class CartItem {
        -UUID id
        -UUID cartId
        -UUID variantId
        -Integer quantity
        -Decimal priceAtAdd
        -DateTime addedAt
        +getProduct() Product
        +getVariant() ProductVariant
        +getLineTotal() Decimal
        +isAvailable() Boolean
    }
    
    class Order {
        -UUID id
        -String orderNumber
        -UUID userId
        -UUID addressId
        -OrderStatus status
        -PaymentMethod paymentMethod
        -PaymentStatus paymentStatus
        -Decimal subtotal
        -Decimal discount
        -Decimal shippingCharge
        -Decimal tax
        -Decimal total
        -String couponCode
        -Decimal couponDiscount
        -String notes
        -DateTime createdAt
        -DateTime confirmedAt
        -DateTime shippedAt
        -DateTime deliveredAt
        -DateTime cancelledAt
        +getItems() OrderItem[]
        +getVendorOrders() VendorOrder[]
        +cancel(reason) void
        +track() TrackingInfo
        +requestReturn(itemIds) Return
        +addNote(note) void
    }
    
    class OrderItem {
        -UUID id
        -UUID orderId
        -UUID vendorOrderId
        -UUID vendorId
        -UUID productId
        -UUID variantId
        -String productName
        -String variantName
        -String imageUrl
        -Integer quantity
        -Decimal unitPrice
        -Decimal totalPrice
        -OrderItemStatus status
        -DateTime createdAt
        +getProduct() Product
        +requestReturn() Return
    }
    
    class VendorOrder {
        -UUID id
        -UUID orderId
        -UUID vendorId
        -String vendorOrderNumber
        -VendorOrderStatus status
        -Decimal subtotal
        -Decimal commission
        -Decimal vendorAmount
        -DateTime createdAt
        -DateTime acceptedAt
        -DateTime packedAt
        +accept() void
        +reject(reason) void
        +markPacked() void
        +getShipment() Shipment
    }
    
    class Coupon {
        -UUID id
        -String code
        -String name
        -String description
        -CouponType type
        -Decimal value
        -Decimal minOrderValue
        -Decimal maxDiscount
        -DateTime validFrom
        -DateTime validTo
        -Integer usageLimit
        -Integer usedCount
        -Integer perUserLimit
        -Boolean isActive
        -String[] applicableCategories
        -String[] applicableProducts
        +validate(cart) ValidationResult
        +apply(cart) DiscountResult
        +incrementUsage() void
        +isValid() Boolean
    }
    
    Cart "1" --> "*" CartItem
    Order "1" --> "*" OrderItem
    Order "1" --> "*" VendorOrder
    Order "*" --> "0..1" Coupon
```

---

## Payment Domain Classes

```mermaid
classDiagram
    class Payment {
        -UUID id
        -UUID orderId
        -String gatewayOrderId
        -String gatewayPaymentId
        -PaymentGateway gateway
        -PaymentMethod method
        -PaymentStatus status
        -Decimal amount
        -String currency
        -JSON gatewayResponse
        -String failureReason
        -DateTime createdAt
        -DateTime authorizedAt
        -DateTime capturedAt
        -DateTime failedAt
        +authorize() AuthResult
        +capture() CaptureResult
        +refund(amount) Refund
        +getStatus() PaymentStatus
    }
    
    class Refund {
        -UUID id
        -UUID paymentId
        -UUID returnId
        -String gatewayRefundId
        -Decimal amount
        -RefundReason reason
        -RefundStatus status
        -RefundMethod method
        -JSON gatewayResponse
        -DateTime initiatedAt
        -DateTime processedAt
        -DateTime failedAt
        +process() RefundResult
        +getStatus() RefundStatus
    }
    
    class VendorPayout {
        -UUID id
        -UUID vendorId
        -String payoutNumber
        -Decimal orderAmount
        -Decimal commission
        -Decimal deductions
        -Decimal netAmount
        -PayoutStatus status
        -String bankReference
        -DateTime periodStart
        -DateTime periodEnd
        -DateTime processedAt
        -DateTime failedAt
        +calculate() void
        +process() PayoutResult
        +getBreakdown() PayoutBreakdown[]
    }
    
    class PayoutBreakdown {
        -UUID id
        -UUID payoutId
        -UUID orderId
        -Decimal orderAmount
        -Decimal commission
        -Decimal deductions
        -Decimal netAmount
    }
    
    class PaymentGatewayAdapter {
        <<interface>>
        +createOrder(amount, currency) GatewayOrder
        +verifyPayment(paymentId) VerifyResult
        +capturePayment(paymentId) CaptureResult
        +refundPayment(paymentId, amount) RefundResult
    }
    
    class RazorpayAdapter {
        -String apiKey
        -String apiSecret
        +createOrder(amount, currency) GatewayOrder
        +verifyPayment(paymentId) VerifyResult
        +capturePayment(paymentId) CaptureResult
        +refundPayment(paymentId, amount) RefundResult
    }
    
    class StripeAdapter {
        -String apiKey
        +createOrder(amount, currency) GatewayOrder
        +verifyPayment(paymentId) VerifyResult
        +capturePayment(paymentId) CaptureResult
        +refundPayment(paymentId, amount) RefundResult
    }
    
    Payment "1" --> "*" Refund
    VendorPayout "1" --> "*" PayoutBreakdown
    PaymentGatewayAdapter <|.. RazorpayAdapter
    PaymentGatewayAdapter <|.. StripeAdapter
```

---

## Logistics Domain Classes

```mermaid
classDiagram
    class Shipment {
        -UUID id
        -String awb
        -UUID orderId
        -UUID vendorOrderId
        -UUID vendorId
        -UUID originWarehouseId
        -UUID destinationBranchId
        -UUID deliveryAgentId
        -ShipmentStatus status
        -ShipmentType type
        -Decimal weight
        -JSON dimensions
        -Decimal declaredValue
        -Boolean isCOD
        -Decimal codAmount
        -DateTime createdAt
        -DateTime pickedUpAt
        -DateTime deliveredAt
        +updateStatus(status, location) void
        +assignAgent(agentId) void
        +markDelivered(pod) void
        +initiateRTO(reason) void
        +getTracking() TrackingEvent[]
    }
    
    class TrackingEvent {
        -UUID id
        -UUID shipmentId
        -String status
        -String statusCode
        -String location
        -String remarks
        -Float latitude
        -Float longitude
        -DateTime timestamp
    }
    
    class Hub {
        -UUID id
        -String name
        -String code
        -HubType type
        -String address
        -String city
        -String state
        -String pincode
        -Float latitude
        -Float longitude
        -String contactPhone
        -Boolean isActive
        -DateTime createdAt
        +getBranches() Branch[]
        +getInboundManifests() Manifest[]
        +getOutboundManifests() Manifest[]
    }
    
    class Branch {
        -UUID id
        -UUID hubId
        -String name
        -String code
        -String address
        -String[] servicePincodes
        -String contactPhone
        -Integer agentCapacity
        -Boolean isActive
        -DateTime createdAt
        +getAgents() DeliveryAgent[]
        +getPendingDeliveries() Shipment[]
        +assignDeliveries() void
    }
    
    class DeliveryAgent {
        -UUID id
        -UUID branchId
        -UUID userId
        -String name
        -String phone
        -String vehicleNumber
        -VehicleType vehicleType
        -AgentStatus status
        -Integer capacity
        -Integer currentLoad
        -Float currentLatitude
        -Float currentLongitude
        -DateTime lastLocationAt
        +getAssignedDeliveries() Shipment[]
        +updateLocation(lat, lng) void
        +startRoute() void
        +completeDelivery(awb, pod) void
        +markUnavailable(reason) void
    }
    
    class LineHaulTrip {
        -UUID id
        -String tripNumber
        -UUID originHubId
        -UUID destinationHubId
        -UUID vehicleId
        -UUID driverId
        -TripStatus status
        -Integer packageCount
        -Decimal totalWeight
        -DateTime scheduledDeparture
        -DateTime actualDeparture
        -DateTime scheduledArrival
        -DateTime actualArrival
        +addShipments(awbs) void
        +dispatch() void
        +complete() void
        +logCheckpoint(location) void
    }
    
    class Manifest {
        -UUID id
        -String manifestNumber
        -ManifestType type
        -UUID tripId
        -UUID hubId
        -Integer packageCount
        -DateTime createdAt
        +getShipments() Shipment[]
        +reconcile(scannedAwbs) ReconcileResult
    }
    
    Shipment "1" --> "*" TrackingEvent
    Hub "1" --> "*" Branch
    Branch "1" --> "*" DeliveryAgent
    LineHaulTrip "1" --> "*" Manifest
    Manifest "*" --> "*" Shipment
```

---

## Vendor Domain Classes

```mermaid
classDiagram
    class Vendor {
        -UUID id
        -UUID userId
        -String businessName
        -String displayName
        -String slug
        -String description
        -String logoUrl
        -String bannerUrl
        -String gstin
        -String pan
        -VendorStatus status
        -Decimal rating
        -Integer ratingCount
        -Integer productCount
        -Integer orderCount
        -CommissionTier commissionTier
        -DateTime createdAt
        -DateTime approvedAt
        +submitForApproval() void
        +activate() void
        +suspend(reason) void
        +getProducts() Product[]
        +getOrders() VendorOrder[]
        +getAnalytics(period) Analytics
    }
    
    class VendorDocument {
        -UUID id
        -UUID vendorId
        -DocumentType type
        -String documentNumber
        -String fileUrl
        -DocumentStatus status
        -String remarks
        -DateTime uploadedAt
        -DateTime verifiedAt
        +verify() void
        +reject(reason) void
    }
    
    class BankAccount {
        -UUID id
        -UUID vendorId
        -String accountHolderName
        -String accountNumber
        -String ifscCode
        -String bankName
        -String branchName
        -Boolean isPrimary
        -VerificationStatus status
        -DateTime createdAt
        -DateTime verifiedAt
        +verify() void
        +setAsPrimary() void
    }
    
    class Warehouse {
        -UUID id
        -UUID vendorId
        -String name
        -String address
        -String city
        -String state
        -String pincode
        -String contactName
        -String contactPhone
        -Float latitude
        -Float longitude
        -Boolean isDefault
        -Boolean isActive
        -DateTime createdAt
        +getInventory() Inventory[]
        +setAsDefault() void
    }
    
    class VendorSettings {
        -UUID id
        -UUID vendorId
        -Boolean autoAcceptOrders
        -Integer processingDays
        -Boolean enableCOD
        -Decimal minOrderValue
        -String returnPolicy
        -JSON shippingSettings
        -JSON notificationPrefs
        +update(settings) void
    }
    
    Vendor "1" --> "*" VendorDocument
    Vendor "1" --> "*" BankAccount
    Vendor "1" --> "*" Warehouse
    Vendor "1" --> "1" VendorSettings
```
