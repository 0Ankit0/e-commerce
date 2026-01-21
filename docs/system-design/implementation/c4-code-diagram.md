# C4 Code Diagram

## Overview
C4 Code diagrams showing class-level details for key components. This is the lowest level of the C4 model.

---

## Order Service - Code Level Diagram

```mermaid
classDiagram
    namespace API {
        class OrderRouter {
            +create_order(order_data, db, current_user): OrderResponse
            +get_order(order_id, db, current_user): OrderResponse
            +list_orders(db, current_user, skip, limit): List~OrderResponse~
            +cancel_order(order_id, reason, db, current_user): OrderResponse
        }
        
        class OrderCreate {
            +address_id: UUID
            +payment_method: PaymentMethod
            +coupon_code: Optional~str~
            +notes: Optional~str~
        }
    }
    
    namespace Application {
        class OrderService {
            -db: AsyncSession
            -order_repo: OrderRepository
            -cart_service: CartService
            -inventory_client: InventoryClient
            -payment_client: PaymentClient
            -event_publisher: EventPublisher
            +create_order(user_id, order_data): Order
            +get_order(order_id): Order
            +cancel_order(order_id, reason): None
        }
        
        class CheckoutService {
            -pricing_engine: PricingEngine
            -coupon_validator: CouponValidator
            -address_validator: AddressValidator
            +validate_checkout(cart, address): CheckoutResult
            +calculate_total(cart, address, coupon): OrderTotal
        }
        
        class OrderSplitter {
            +split_by_vendor(order): List~VendorOrder~
        }
        
        class PricingEngine {
            +calculate_subtotal(items): Decimal
            +calculate_discount(items, coupon): Decimal
            +calculate_shipping(address, items): Decimal
            +calculate_tax(subtotal, address): Decimal
        }
    }
    
    namespace Domain {
        class Order {
            +id: UUID
            +order_number: str
            +user_id: UUID
            +status: OrderStatus
            +items: List~OrderItem~
            +total: Decimal
            +created_at: datetime
            +cancel(reason): None
            +update_status(status): None
        }
        
        class OrderItem {
            +id: UUID
            +product_id: UUID
            +variant_id: UUID
            +quantity: int
            +unit_price: Decimal
            +get_line_total(): Decimal
        }
    }
    
    namespace Infrastructure {
        class OrderRepository {
            -db: AsyncSession
            +find_by_id(id): Optional~Order~
            +save(order): Order
            +find_by_user(user_id, skip, limit): List~Order~
        }
        
        class InventoryClient {
            -http_client: httpx.AsyncClient
            +check_availability(items): AvailabilityResult
            +reserve_stock(order_id, items): None
            +release_stock(order_id): None
        }
        
        class EventPublisher {
            -kafka_producer: AIOKafkaProducer
            +publish(topic, event): None
        }
    }
    
    OrderRouter --> OrderService
    OrderRouter --> OrderCreate
    
    OrderService --> CheckoutService
    OrderService --> OrderSplitter
    OrderService --> OrderRepository
    OrderService --> InventoryClient
    OrderService --> EventPublisher
    
    CheckoutService --> PricingEngine
    
    OrderService --> Order
    Order --> OrderItem
```
```

---

## Payment Service - Code Level Diagram

```mermaid
classDiagram
    namespace API {
        class PaymentRouter {
            +create_payment(order_id, amount, db): PaymentOrderResponse
            +get_payment_status(payment_id, db): PaymentStatusResponse
        }
        
        class WebhookRouter {
            +handle_razorpay(request, raw_body): JSONResponse
            +handle_stripe(request, raw_body): JSONResponse
        }
    }
    
    namespace Application {
        class PaymentService {
            -db: AsyncSession
            -payment_repo: PaymentRepository
            -gateway_factory: GatewayFactory
            -order_client: OrderClient
            -event_publisher: EventPublisher
            +create_payment_order(order_id, amount): PaymentOrder
            +handle_webhook(gateway, payload): None
            +refund(payment_id, amount): Refund
        }
        
        class RefundService {
            -refund_repo: RefundRepository
            -gateway_factory: GatewayFactory
            +initiate_refund(payment_id, amount): Refund
            +process_refund(refund_id): None
        }
    }
    
    namespace Domain {
        class Payment {
            +id: UUID
            +order_id: UUID
            +gateway_order_id: str
            +status: PaymentStatus
            +amount: Decimal
            +method: PaymentMethod
            +authorize(): None
            +capture(): None
            +fail(reason): None
        }
        
        class Refund {
            +id: UUID
            +payment_id: UUID
            +amount: Decimal
            +status: RefundStatus
            +initiate(): None
            +process(): None
        }
    }
    
    namespace GatewayAdapters {
        class PaymentGateway {
            <<protocol>>
            +create_order(amount): GatewayOrder
            +verify_payment(payment_id): VerifyResult
            +refund(payment_id, amount): RefundResult
        }
        
        class RazorpayAdapter {
            -api_key: str
            -api_secret: str
            -client: razorpay.Client
            +create_order(amount): GatewayOrder
            +verify_payment(payment_id): VerifyResult
            +refund(payment_id, amount): RefundResult
        }
        
        class StripeAdapter {
            -api_key: str
            -client: stripe.Client
            +create_order(amount): GatewayOrder
            +verify_payment(payment_id): VerifyResult
            +refund(payment_id, amount): RefundResult
        }
        
        class GatewayFactory {
            +get_gateway(name): PaymentGateway
        }
    }
    
    namespace Security {
        class SignatureValidator {
            +validate_razorpay(payload, signature): bool
            +validate_stripe(payload, signature): bool
        }
    }
    
    PaymentRouter --> PaymentService
    WebhookRouter --> PaymentService
    WebhookRouter --> SignatureValidator
    
    PaymentService --> GatewayFactory
    PaymentService --> Payment
    
    RefundService --> Refund
    RefundService --> GatewayFactory
    
    GatewayFactory --> RazorpayAdapter
    GatewayFactory --> StripeAdapter
    
    RazorpayAdapter ..|> PaymentGateway
    StripeAdapter ..|> PaymentGateway
```

---

## Logistics Service - Code Level Diagram

```mermaid
classDiagram
    namespace API {
        class ShipmentController {
            -shipmentService: ShipmentService
            +createShipment(req, res): Promise~void~
            +getTracking(req, res): Promise~void~
            +updateStatus(req, res): Promise~void~
        }
        
        class DeliveryController {
            -deliveryService: DeliveryService
            +getAssignments(req, res): Promise~void~
            +markDelivered(req, res): Promise~void~
            +reportException(req, res): Promise~void~
        }
    }
    
    namespace Application {
        class ShipmentService {
            -shipmentRepository: ShipmentRepository
            -trackingRepository: TrackingRepository
            -partnerClient: PartnerClient
            -eventPublisher: EventPublisher
            +createShipment(order): Promise~Shipment~
            +updateStatus(awb, status): Promise~void~
            +getTracking(awb): Promise~TrackingInfo~
        }
        
        class DeliveryService {
            -agentRepository: AgentRepository
            -shipmentRepository: ShipmentRepository
            -assignmentEngine: AssignmentEngine
            +getAgentAssignments(agentId): Promise~Shipment[]~
            +completeDelivery(awb, pod): Promise~void~
            +handleException(awb, exception): Promise~void~
        }
        
        class RouteOptimizer {
            -mapsClient: MapsClient
            +optimizeRoute(shipments): Promise~OptimizedRoute~
            +calculateETA(origin, destination): Promise~Duration~
        }
        
        class AssignmentEngine {
            -agentRepository: AgentRepository
            +assignToAgent(shipment): Promise~Agent~
            +rebalance(branchId): Promise~void~
        }
    }
    
    namespace Domain {
        class Shipment {
            +id: UUID
            +awb: string
            +status: ShipmentStatus
            +origin: Location
            +destination: Address
            +weight: Weight
            +updateStatus(status, location): void
            +assignAgent(agent): void
            +markDelivered(pod): void
        }
        
        class TrackingEvent {
            +id: UUID
            +shipmentId: UUID
            +status: string
            +location: Location
            +timestamp: DateTime
        }
        
        class DeliveryAgent {
            +id: UUID
            +name: string
            +status: AgentStatus
            +currentLoad: number
            +capacity: number
            +location: Location
            +canAcceptDelivery(): boolean
            +assignDelivery(shipment): void
        }
    }
    
    namespace Infrastructure {
        class PartnerClient {
            -httpClient: AxiosInstance
            +createShipment(data): Promise~ShipmentResponse~
            +getTracking(awb): Promise~TrackingResponse~
        }
        
        class MapsClient {
            -apiKey: string
            +getDirections(origin, dest): Promise~Route~
            +calculateDistance(origin, dest): Promise~Distance~
        }
    }
    
    ShipmentController --> ShipmentService
    DeliveryController --> DeliveryService
    
    ShipmentService --> Shipment
    ShipmentService --> TrackingEvent
    ShipmentService --> PartnerClient
    
    DeliveryService --> DeliveryAgent
    DeliveryService --> AssignmentEngine
    
    RouteOptimizer --> MapsClient
    AssignmentEngine --> DeliveryAgent
```

---

## Notification Service - Code Level Diagram

```mermaid
classDiagram
    namespace EventConsumers {
        class OrderEventConsumer {
            -notificationOrchestrator: NotificationOrchestrator
            +handleOrderCreated(event): Promise~void~
            +handleOrderShipped(event): Promise~void~
            +handleOrderDelivered(event): Promise~void~
        }
        
        class PaymentEventConsumer {
            -notificationOrchestrator: NotificationOrchestrator
            +handlePaymentSuccess(event): Promise~void~
            +handlePaymentFailed(event): Promise~void~
            +handleRefundProcessed(event): Promise~void~
        }
    }
    
    namespace Application {
        class NotificationOrchestrator {
            -templateProcessor: TemplateProcessor
            -preferenceManager: PreferenceManager
            -channelRouter: ChannelRouter
            +send(type, userId, data): Promise~void~
            +sendBulk(type, userIds, data): Promise~void~
        }
        
        class TemplateProcessor {
            -templateRepository: TemplateRepository
            +render(templateId, data): Promise~RenderedContent~
        }
        
        class PreferenceManager {
            -preferenceRepository: PreferenceRepository
            +getPreferences(userId): Promise~Preferences~
            +shouldSend(userId, channel, type): Promise~boolean~
        }
        
        class ChannelRouter {
            -channels: Map~string, Channel~
            +route(notification, channels): Promise~void~
        }
    }
    
    namespace Channels {
        class Channel {
            <<interface>>
            +send(notification): Promise~void~
        }
        
        class EmailChannel {
            -emailProvider: EmailProvider
            +send(notification): Promise~void~
        }
        
        class SMSChannel {
            -smsProvider: SMSProvider
            +send(notification): Promise~void~
        }
        
        class PushChannel {
            -pushProvider: PushProvider
            +send(notification): Promise~void~
        }
    }
    
    namespace Providers {
        class EmailProvider {
            <<interface>>
            +sendEmail(to, subject, body): Promise~void~
        }
        
        class SendGridProvider {
            -apiKey: string
            +sendEmail(to, subject, body): Promise~void~
        }
        
        class SMSProvider {
            <<interface>>
            +sendSMS(to, message): Promise~void~
        }
        
        class TwilioProvider {
            -accountSid: string
            -authToken: string
            +sendSMS(to, message): Promise~void~
        }
    }
    
    OrderEventConsumer --> NotificationOrchestrator
    PaymentEventConsumer --> NotificationOrchestrator
    
    NotificationOrchestrator --> TemplateProcessor
    NotificationOrchestrator --> PreferenceManager
    NotificationOrchestrator --> ChannelRouter
    
    ChannelRouter --> EmailChannel
    ChannelRouter --> SMSChannel
    ChannelRouter --> PushChannel
    
    EmailChannel ..|> Channel
    SMSChannel ..|> Channel
    PushChannel ..|> Channel
    
    EmailChannel --> SendGridProvider
    SMSChannel --> TwilioProvider
    
    SendGridProvider ..|> EmailProvider
    TwilioProvider ..|> SMSProvider
```

---

## Code Organization Summary

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| **API** | HTTP handling, validation, routing | Controllers, DTOs, Middleware |
| **Application** | Business logic orchestration | Services, Use Cases |
| **Domain** | Core business entities and rules | Entities, Value Objects, Domain Events |
| **Infrastructure** | External integrations, persistence | Repositories, API Clients, Message Publishers |

---

## Design Patterns Used

| Pattern | Purpose | Location |
|---------|---------|----------|
| **Repository** | Abstract data access | Infrastructure layer |
| **Factory** | Create gateway instances | Payment gateway selection |
| **Adapter** | Integrate external services | API clients, providers |
| **Strategy** | Interchangeable algorithms | Pricing, routing |
| **Observer** | Event-driven communication | Kafka event publishing |
| **Decorator** | Add cross-cutting concerns | Logging, caching |
| **DI/IoC** | Dependency management | All layers |
