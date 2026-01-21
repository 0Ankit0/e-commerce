# Sequence Diagrams

## Overview
Detailed sequence diagrams showing internal object interactions for key system operations.

---

## Place Order - Internal Sequence

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant OrderCtrl as OrderController
    participant CheckoutSvc as CheckoutService
    participant CartSvc as CartService
    participant InventorySvc as InventoryService
    participant PricingSvc as PricingService
    participant PaymentSvc as PaymentService
    participant OrderRepo as OrderRepository
    participant EventBus as Kafka
    
    Client->>Gateway: POST /orders/checkout
    Gateway->>OrderCtrl: checkout(userId, addressId, paymentMethod)
    
    OrderCtrl->>CartSvc: getCart(userId)
    CartSvc-->>OrderCtrl: cart
    
    OrderCtrl->>CheckoutSvc: validateCheckout(cart, addressId)
    
    loop For each cart item
        CheckoutSvc->>InventorySvc: checkAvailability(variantId, qty)
        InventorySvc-->>CheckoutSvc: available: true/false
    end
    
    CheckoutSvc->>PricingSvc: calculateTotal(cart, addressId, coupon)
    PricingSvc->>PricingSvc: calculateSubtotal()
    PricingSvc->>PricingSvc: calculateDiscount()
    PricingSvc->>PricingSvc: calculateShipping()
    PricingSvc->>PricingSvc: calculateTax()
    PricingSvc-->>CheckoutSvc: orderTotal
    
    CheckoutSvc-->>OrderCtrl: validationResult
    
    alt Validation Failed
        OrderCtrl-->>Client: 400 Bad Request (errors)
    else Validation Passed
        OrderCtrl->>CheckoutSvc: createOrder(cart, address, total)
        
        CheckoutSvc->>OrderRepo: beginTransaction()
        
        loop For each cart item
            CheckoutSvc->>InventorySvc: reserveStock(variantId, qty)
            InventorySvc-->>CheckoutSvc: reserved
        end
        
        CheckoutSvc->>OrderRepo: createOrder(orderData)
        OrderRepo-->>CheckoutSvc: order
        
        CheckoutSvc->>OrderRepo: createOrderItems(items)
        CheckoutSvc->>OrderRepo: createVendorOrders(vendorOrders)
        
        alt Online Payment
            CheckoutSvc->>PaymentSvc: createPaymentOrder(orderId, amount)
            PaymentSvc->>PaymentSvc: callGateway()
            PaymentSvc-->>CheckoutSvc: paymentOrder
        end
        
        CheckoutSvc->>OrderRepo: commitTransaction()
        CheckoutSvc->>CartSvc: clearCart(userId)
        
        CheckoutSvc->>EventBus: publish(OrderCreated)
        
        CheckoutSvc-->>OrderCtrl: order
        OrderCtrl-->>Client: 201 Created (order, paymentUrl)
    end
```

---

## Payment Processing - Internal Sequence

```mermaid
sequenceDiagram
    participant Gateway as Payment Gateway
    participant Webhook as WebhookHandler
    participant PaymentSvc as PaymentService
    participant PaymentRepo as PaymentRepository
    participant OrderSvc as OrderService
    participant InventorySvc as InventoryService
    participant EventBus as Kafka
    participant NotifSvc as NotificationService
    
    Gateway->>Webhook: POST /webhooks/payment
    Webhook->>Webhook: verifySignature(payload, signature)
    
    alt Invalid Signature
        Webhook-->>Gateway: 401 Unauthorized
    else Valid Signature
        Webhook->>PaymentSvc: handlePaymentWebhook(payload)
        
        PaymentSvc->>PaymentRepo: getPaymentByGatewayId(gatewayPaymentId)
        PaymentRepo-->>PaymentSvc: payment
        
        alt Payment Successful
            PaymentSvc->>PaymentRepo: updateStatus(CAPTURED)
            PaymentSvc->>OrderSvc: confirmOrder(orderId)
            
            OrderSvc->>OrderSvc: updateOrderStatus(CONFIRMED)
            
            loop For each vendor order
                OrderSvc->>EventBus: publish(VendorOrderCreated)
            end
            
            OrderSvc->>InventorySvc: confirmReservations(orderId)
            InventorySvc->>InventorySvc: deductStock()
            
            OrderSvc-->>PaymentSvc: orderConfirmed
            
        else Payment Failed
            PaymentSvc->>PaymentRepo: updateStatus(FAILED)
            PaymentSvc->>OrderSvc: cancelOrder(orderId, "Payment Failed")
            
            OrderSvc->>InventorySvc: releaseReservations(orderId)
            InventorySvc->>InventorySvc: releaseStock()
            
            OrderSvc-->>PaymentSvc: orderCancelled
        end
        
        PaymentSvc->>EventBus: publish(PaymentStatusChanged)
        EventBus->>NotifSvc: consume(PaymentStatusChanged)
        NotifSvc->>NotifSvc: sendOrderConfirmation()
        
        PaymentSvc-->>Webhook: processed
        Webhook-->>Gateway: 200 OK
    end
```

---

## Vendor Order Fulfillment - Internal Sequence

```mermaid
sequenceDiagram
    participant Client as VendorApp
    participant Gateway as API Gateway
    participant VendorCtrl as VendorController
    participant OrderSvc as OrderService
    participant ShipmentSvc as ShipmentService
    participant LogisticsClient as LogisticsPartnerAPI
    participant OrderRepo as OrderRepository
    participant EventBus as Kafka
    
    Client->>Gateway: POST /vendor/orders/{id}/accept
    Gateway->>VendorCtrl: acceptOrder(vendorId, orderId)
    
    VendorCtrl->>OrderSvc: acceptVendorOrder(vendorOrderId)
    OrderSvc->>OrderRepo: getVendorOrder(vendorOrderId)
    OrderRepo-->>OrderSvc: vendorOrder
    
    OrderSvc->>OrderRepo: updateStatus(PROCESSING)
    OrderSvc->>EventBus: publish(OrderAccepted)
    OrderSvc-->>VendorCtrl: accepted
    VendorCtrl-->>Client: 200 OK
    
    Note over Client,EventBus: Later - Vendor packs order
    
    Client->>Gateway: POST /vendor/orders/{id}/pack
    Gateway->>VendorCtrl: markPacked(vendorId, orderId)
    
    VendorCtrl->>OrderSvc: markVendorOrderPacked(vendorOrderId)
    OrderSvc->>OrderRepo: updateStatus(PACKED)
    
    OrderSvc->>ShipmentSvc: createShipment(vendorOrder)
    ShipmentSvc->>ShipmentSvc: calculateDimensions()
    ShipmentSvc->>LogisticsClient: createShipment(shipmentData)
    LogisticsClient-->>ShipmentSvc: awb, labelUrl
    
    ShipmentSvc->>ShipmentSvc: saveShipment(awb)
    ShipmentSvc-->>OrderSvc: shipment
    
    OrderSvc->>EventBus: publish(OrderPacked)
    OrderSvc-->>VendorCtrl: packedWithShipment
    VendorCtrl-->>Client: 200 OK (awb, labelUrl)
    
    Note over Client,EventBus: Later - Schedule pickup
    
    Client->>Gateway: POST /vendor/orders/{id}/schedule-pickup
    Gateway->>VendorCtrl: schedulePickup(vendorId, orderId, slot)
    
    VendorCtrl->>ShipmentSvc: schedulePickup(shipmentId, slot)
    ShipmentSvc->>LogisticsClient: schedulePickup(awb, slot)
    LogisticsClient-->>ShipmentSvc: pickupScheduled
    
    ShipmentSvc->>EventBus: publish(PickupScheduled)
    ShipmentSvc-->>VendorCtrl: scheduled
    VendorCtrl-->>Client: 200 OK
```

---

## Last Mile Delivery - Internal Sequence

```mermaid
sequenceDiagram
    participant App as AgentApp
    participant Gateway as API Gateway
    participant DeliveryCtrl as DeliveryController
    participant ShipmentSvc as ShipmentService
    participant AgentSvc as AgentService
    participant ShipmentRepo as ShipmentRepository
    participant TrackingRepo as TrackingRepository
    participant EventBus as Kafka
    participant NotifSvc as NotificationService
    
    App->>Gateway: GET /agent/deliveries
    Gateway->>DeliveryCtrl: getAssignedDeliveries(agentId)
    DeliveryCtrl->>AgentSvc: getDeliveries(agentId)
    AgentSvc->>ShipmentRepo: findByAgent(agentId, status=OUT_FOR_DELIVERY)
    ShipmentRepo-->>AgentSvc: shipments[]
    AgentSvc-->>DeliveryCtrl: deliveries
    DeliveryCtrl-->>App: deliveries[]
    
    Note over App,NotifSvc: Agent arrives at delivery location
    
    App->>Gateway: POST /agent/deliveries/{awb}/arrived
    Gateway->>DeliveryCtrl: markArrived(agentId, awb)
    
    DeliveryCtrl->>ShipmentSvc: updateStatus(awb, ARRIVED)
    ShipmentSvc->>TrackingRepo: addEvent(ARRIVED, location)
    ShipmentSvc->>EventBus: publish(AgentArrived)
    
    EventBus->>NotifSvc: consume(AgentArrived)
    NotifSvc->>NotifSvc: sendPushToCustomer("Agent arriving")
    
    ShipmentSvc-->>DeliveryCtrl: updated
    DeliveryCtrl-->>App: 200 OK
    
    Note over App,NotifSvc: Agent delivers and captures POD
    
    App->>Gateway: POST /agent/deliveries/{awb}/deliver
    Gateway->>DeliveryCtrl: markDelivered(agentId, awb, pod)
    
    DeliveryCtrl->>ShipmentSvc: completeDelivery(awb, pod)
    ShipmentSvc->>ShipmentSvc: validatePOD(pod)
    
    ShipmentSvc->>ShipmentRepo: updateStatus(DELIVERED)
    ShipmentSvc->>TrackingRepo: addEvent(DELIVERED, location, pod)
    
    ShipmentSvc->>AgentSvc: decrementLoad(agentId)
    
    ShipmentSvc->>EventBus: publish(OrderDelivered)
    
    EventBus->>NotifSvc: consume(OrderDelivered)
    NotifSvc->>NotifSvc: sendDeliveryConfirmation()
    
    ShipmentSvc-->>DeliveryCtrl: delivered
    DeliveryCtrl-->>App: 200 OK
```

---

## Line Haul Transit - Internal Sequence

```mermaid
sequenceDiagram
    participant HubApp as HubOperatorApp
    participant Gateway as API Gateway
    participant HubCtrl as HubController
    participant LineHaulSvc as LineHaulService
    participant ManifestRepo as ManifestRepository
    participant ShipmentRepo as ShipmentRepository
    participant TripRepo as TripRepository
    participant EventBus as Kafka
    
    Note over HubApp,EventBus: Creating outbound manifest
    
    HubApp->>Gateway: POST /hub/manifests
    Gateway->>HubCtrl: createManifest(destinationHubId, awbs[])
    
    HubCtrl->>LineHaulSvc: createOutboundManifest(hubId, destHubId, awbs)
    LineHaulSvc->>ShipmentRepo: validateAwbs(awbs)
    ShipmentRepo-->>LineHaulSvc: shipments[]
    
    LineHaulSvc->>ManifestRepo: createManifest(manifestData)
    ManifestRepo-->>LineHaulSvc: manifest
    
    loop For each shipment
        LineHaulSvc->>ShipmentRepo: updateStatus(IN_TRANSIT_TO_HUB)
    end
    
    LineHaulSvc-->>HubCtrl: manifest
    HubCtrl-->>HubApp: manifest(id, count)
    
    Note over HubApp,EventBus: Dispatching vehicle
    
    HubApp->>Gateway: POST /hub/trips/{tripId}/dispatch
    Gateway->>HubCtrl: dispatchTrip(tripId)
    
    HubCtrl->>LineHaulSvc: dispatch(tripId)
    LineHaulSvc->>TripRepo: updateStatus(IN_TRANSIT)
    LineHaulSvc->>TripRepo: setActualDeparture(now)
    
    LineHaulSvc->>EventBus: publish(TripDispatched)
    
    LineHaulSvc-->>HubCtrl: dispatched
    HubCtrl-->>HubApp: 200 OK
    
    Note over HubApp,EventBus: Vehicle arrives at destination
    
    HubApp->>Gateway: POST /hub/trips/{tripId}/arrive
    Gateway->>HubCtrl: completeTrip(tripId)
    
    HubCtrl->>LineHaulSvc: complete(tripId)
    LineHaulSvc->>TripRepo: updateStatus(ARRIVED)
    LineHaulSvc->>TripRepo: setActualArrival(now)
    
    LineHaulSvc->>ManifestRepo: getManifests(tripId)
    ManifestRepo-->>LineHaulSvc: manifests[]
    
    LineHaulSvc->>EventBus: publish(TripCompleted)
    
    LineHaulSvc-->>HubCtrl: completed
    HubCtrl-->>HubApp: 200 OK
    
    Note over HubApp,EventBus: Processing inbound packages
    
    HubApp->>Gateway: POST /hub/manifests/{id}/scan
    Gateway->>HubCtrl: scanInbound(manifestId, awb)
    
    HubCtrl->>LineHaulSvc: scanPackage(manifestId, awb)
    LineHaulSvc->>ShipmentRepo: updateStatus(RECEIVED_AT_HUB)
    LineHaulSvc->>ManifestRepo: markPackageReceived(awb)
    
    LineHaulSvc->>EventBus: publish(PackageReceived)
    
    LineHaulSvc-->>HubCtrl: scanned(remaining)
    HubCtrl-->>HubApp: 200 OK(remaining count)
```

---

## Return Processing - Internal Sequence

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant ReturnCtrl as ReturnController
    participant ReturnSvc as ReturnService
    participant OrderSvc as OrderService
    participant ShipmentSvc as ShipmentService
    participant RefundSvc as RefundService
    participant ReturnRepo as ReturnRepository
    participant EventBus as Kafka
    
    Client->>Gateway: POST /orders/{orderId}/return
    Gateway->>ReturnCtrl: createReturn(userId, orderId, itemIds, reason)
    
    ReturnCtrl->>ReturnSvc: initiateReturn(orderId, itemIds, reason)
    
    ReturnSvc->>OrderSvc: validateReturnEligibility(orderId, itemIds)
    OrderSvc-->>ReturnSvc: eligibility
    
    alt Not Eligible
        ReturnSvc-->>ReturnCtrl: error(reason)
        ReturnCtrl-->>Client: 400 Bad Request
    else Eligible
        ReturnSvc->>ReturnRepo: createReturn(returnData)
        ReturnRepo-->>ReturnSvc: return
        
        ReturnSvc->>EventBus: publish(ReturnRequested)
        
        ReturnSvc-->>ReturnCtrl: return
        ReturnCtrl-->>Client: 201 Created (returnId)
    end
    
    Note over Client,EventBus: Vendor approves return
    
    EventBus->>VendorSvc: consume(ReturnRequested)
    VendorSvc->>ReturnRepo: updateStatus(APPROVED)
    
    VendorSvc->>ShipmentSvc: createReversePickup(return)
    ShipmentSvc-->>VendorSvc: reverseAwb
    
    VendorSvc->>EventBus: publish(ReturnApproved)
    
    Note over Client,EventBus: Item returned to vendor
    
    EventBus->>ReturnSvc: consume(ReverseDelivered)
    ReturnSvc->>ReturnRepo: updateStatus(RECEIVED)
    
    ReturnSvc->>RefundSvc: initiateRefund(returnId, amount)
    RefundSvc->>RefundSvc: processRefund()
    RefundSvc-->>ReturnSvc: refund
    
    ReturnSvc->>OrderSvc: updateItemStatus(RETURNED)
    ReturnSvc->>ReturnRepo: updateStatus(COMPLETED)
    
    ReturnSvc->>EventBus: publish(ReturnCompleted)
```
