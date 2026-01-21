# System Sequence Diagrams

## Overview
System Sequence Diagrams (SSD) show black-box interactions between actors and the system, treating the system as a single entity.

---

## Customer: Place Order Sequence

```mermaid
sequenceDiagram
    actor Customer
    participant System as E-Commerce System
    participant PaymentGW as Payment Gateway
    
    Customer->>System: browseProducts(category, filters)
    System-->>Customer: productList
    
    Customer->>System: viewProductDetails(productId)
    System-->>Customer: productDetails
    
    Customer->>System: addToCart(productId, variant, quantity)
    System-->>Customer: cartUpdated
    
    Customer->>System: proceedToCheckout()
    System-->>Customer: checkoutPage(addresses, summary)
    
    Customer->>System: selectAddress(addressId)
    System-->>Customer: deliveryCharges, ETA
    
    Customer->>System: applyCoupon(couponCode)
    System-->>Customer: discountApplied | error
    
    Customer->>System: selectPaymentMethod(method)
    System-->>Customer: paymentOptions
    
    Customer->>System: placeOrder()
    System->>PaymentGW: createPaymentOrder(amount)
    PaymentGW-->>System: paymentURL
    System-->>Customer: redirect(paymentURL)
    
    Customer->>PaymentGW: completePayment(details)
    PaymentGW-->>Customer: paymentResult
    PaymentGW->>System: webhook(paymentStatus)
    
    Customer->>System: paymentCallback(status)
    System-->>Customer: orderConfirmation(orderId)
```

---

## Customer: Track Order Sequence

```mermaid
sequenceDiagram
    actor Customer
    participant System as E-Commerce System
    
    Customer->>System: viewOrders()
    System-->>Customer: orderList
    
    Customer->>System: getOrderDetails(orderId)
    System-->>Customer: orderDetails(items, status)
    
    Customer->>System: trackShipment(orderId)
    System-->>Customer: trackingInfo(milestones, location, ETA)
    
    loop Real-time Updates
        System-->>Customer: pushNotification(statusUpdate)
    end
    
    Customer->>System: downloadInvoice(orderId)
    System-->>Customer: invoicePDF
```

---

## Customer: Return Request Sequence

```mermaid
sequenceDiagram
    actor Customer
    participant System as E-Commerce System
    
    Customer->>System: initiateReturn(orderId, itemId)
    System-->>Customer: returnEligibility(policy, reasons)
    
    Customer->>System: submitReturn(reason, photos)
    System-->>Customer: returnRequestId, status
    
    System-->>Customer: notification(pickupScheduled, date)
    
    Customer->>System: checkReturnStatus(returnId)
    System-->>Customer: returnStatus(stage, timeline)
    
    System-->>Customer: notification(refundProcessed, amount)
```

---

## Vendor: Order Fulfillment Sequence

```mermaid
sequenceDiagram
    actor Vendor
    participant System as E-Commerce System
    participant Logistics as Logistics Partner
    
    System-->>Vendor: newOrderNotification(orderId)
    
    Vendor->>System: getOrderDetails(orderId)
    System-->>Vendor: orderDetails(items, customer, address)
    
    Vendor->>System: acceptOrder(orderId)
    System-->>Vendor: orderAccepted
    
    Vendor->>System: markAsPacked(orderId)
    System-->>Vendor: packingConfirmed
    
    Vendor->>System: generateShippingLabel(orderId)
    System->>Logistics: createShipment(details)
    Logistics-->>System: AWB, label
    System-->>Vendor: shippingLabel(AWB, labelPDF)
    
    Vendor->>System: schedulePickup(orderId, slot)
    System->>Logistics: requestPickup(AWB, slot)
    Logistics-->>System: pickupConfirmed
    System-->>Vendor: pickupScheduled(time)
    
    Logistics-->>System: webhook(pickupComplete)
    System-->>Vendor: notification(shipped)
```

---

## Vendor: Product Management Sequence

```mermaid
sequenceDiagram
    actor Vendor
    participant System as E-Commerce System
    
    Vendor->>System: createProduct(details)
    System-->>Vendor: validationResult
    
    Vendor->>System: uploadImages(productId, images[])
    System-->>Vendor: imageURLs
    
    Vendor->>System: addVariants(productId, variants[])
    System-->>Vendor: variantsCreated
    
    Vendor->>System: setInventory(variantId, quantity)
    System-->>Vendor: inventoryUpdated
    
    Vendor->>System: submitForApproval(productId)
    System-->>Vendor: submissionId, status
    
    System-->>Vendor: notification(approved | rejected)
    
    Vendor->>System: updateProduct(productId, changes)
    System-->>Vendor: productUpdated
```

---

## Admin: Vendor Approval Sequence

```mermaid
sequenceDiagram
    actor Admin
    participant System as E-Commerce System
    
    Admin->>System: getPendingVendors()
    System-->>Admin: vendorList(pending)
    
    Admin->>System: getVendorDetails(vendorId)
    System-->>Admin: vendorDetails(business, documents)
    
    Admin->>System: verifyDocument(docId)
    System-->>Admin: documentPreview
    
    alt Approved
        Admin->>System: approveVendor(vendorId)
        System-->>Admin: vendorActivated
        System-->>Vendor: notification(approved)
    else Rejected
        Admin->>System: rejectVendor(vendorId, reason)
        System-->>Admin: vendorRejected
        System-->>Vendor: notification(rejected, reason)
    else Need More Info
        Admin->>System: requestInfo(vendorId, requirements)
        System-->>Admin: requestSent
        System-->>Vendor: notification(moreInfoNeeded)
    end
```

---

## Logistics: Line Haul Sequence

```mermaid
sequenceDiagram
    actor HubOperator as Origin Hub
    participant System as E-Commerce System
    actor DestHub as Destination Hub
    actor Driver
    
    HubOperator->>System: createManifest(packages[], destination)
    System-->>HubOperator: manifestId, summary
    
    HubOperator->>System: assignVehicle(manifestId, vehicleId)
    System-->>HubOperator: vehicleAssigned
    
    HubOperator->>System: scanPackage(AWB)
    System-->>HubOperator: packageLoaded
    
    HubOperator->>System: dispatchVehicle(manifestId)
    System-->>HubOperator: dispatchConfirmed
    
    loop During Transit
        Driver->>System: updateLocation(GPS)
        System-->>Driver: acknowledged
        
        Driver->>System: reportCheckpoint(location)
        System-->>Driver: checkpointLogged
    end
    
    Driver->>System: reportArrival(hubId)
    System-->>Driver: arrivalConfirmed
    System-->>DestHub: notification(vehicleArrived)
    
    DestHub->>System: startUnloading(manifestId)
    System-->>DestHub: expectedPackages
    
    DestHub->>System: scanInboundPackage(AWB)
    System-->>DestHub: packageReceived
    
    DestHub->>System: completeInbound(manifestId)
    System-->>DestHub: reconciliationReport
```

---

## Logistics: Last Mile Delivery Sequence

```mermaid
sequenceDiagram
    actor Agent as Delivery Agent
    participant System as E-Commerce System
    actor Customer
    
    System-->>Agent: dailyAssignments(packages[])
    
    Agent->>System: startRoute()
    System-->>Agent: optimizedRoute
    
    loop For Each Delivery
        Agent->>System: navigateTo(AWB)
        System-->>Agent: address, customerContact
        
        Agent->>System: markArrived(AWB)
        System-->>Agent: arrivalConfirmed
        System-->>Customer: notification(agentArriving)
        
        alt Successful Delivery
            Agent->>System: captureOTP(AWB, OTP)
            System-->>Agent: OTPVerified
            Agent->>System: markDelivered(AWB, photo)
            System-->>Agent: deliveryConfirmed
            System-->>Customer: notification(delivered)
        else Customer Not Available
            Agent->>System: markAttemptFailed(AWB, reason)
            System-->>Agent: failureRecorded
            System-->>Customer: notification(attemptFailed)
        else Customer Refused
            Agent->>System: markRefused(AWB, reason)
            System-->>Agent: RTOInitiated
        end
    end
    
    Agent->>System: endRoute()
    System-->>Agent: routeSummary
```

---

## Payment: Refund Processing Sequence

```mermaid
sequenceDiagram
    actor Admin
    participant System as E-Commerce System
    participant PaymentGW as Payment Gateway
    actor Customer
    
    System->>System: returnCompleted(returnId)
    System->>System: calculateRefundAmount()
    
    alt Refund to Original Payment
        System->>PaymentGW: initiateRefund(paymentId, amount)
        PaymentGW-->>System: refundId, status
        
        loop Until Settled
            PaymentGW->>System: webhook(refundStatus)
        end
        
        System-->>Customer: notification(refundProcessed)
    else Refund to Wallet
        System->>System: creditWallet(customerId, amount)
        System-->>Customer: notification(walletCredited)
    end
    
    Admin->>System: getRefundReport(dateRange)
    System-->>Admin: refundSummary
```
