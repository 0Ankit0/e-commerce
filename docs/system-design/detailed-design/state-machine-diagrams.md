# State Machine Diagrams

## Overview
State machines for the implemented backend entities and lifecycle transitions.

---

## Order State Machine

```mermaid
stateDiagram-v2
    [*] --> PendingPayment: Checkout created

    PendingPayment --> Confirmed: COD or wallet confirmation
    PendingPayment --> Confirmed: Payment captured or verified
    PendingPayment --> Cancelled: Payment failed or expired

    Confirmed --> Processing: Vendor accepts
    Confirmed --> Cancelled: Customer or admin cancellation allowed

    Processing --> Packed: Vendor packs
    Packed --> Shipped: Shipment handed to logistics
    Shipped --> OutForDelivery: Agent assigned
    OutForDelivery --> Delivered: Proof of delivery recorded

    OutForDelivery --> DeliveryException: Attempt failed
    DeliveryException --> OutForDelivery: Rescheduled
    DeliveryException --> RTOInitiated: Refused or max attempts
    RTOInitiated --> ReturnedToOrigin: RTO completed

    Delivered --> ReturnRequested: Customer requests return
    ReturnRequested --> Returned: Return received and closed

    Cancelled --> [*]
    Delivered --> [*]
    ReturnedToOrigin --> [*]
    Returned --> [*]
```

---

## Payment State Machine

```mermaid
stateDiagram-v2
    [*] --> Initiated: Payment record created
    Initiated --> Pending: Redirect or provider intent created
    Pending --> Authorized: Provider authorization success
    Pending --> Captured: Immediate capture success
    Pending --> Failed: Provider failure
    Pending --> Expired: Timeout or abandoned

    Authorized --> Captured: Capture confirmed
    Authorized --> Voided: Order cancelled before capture
    Captured --> PartiallyRefunded: Partial refund
    Captured --> Refunded: Full refund
    PartiallyRefunded --> Refunded: Remaining amount refunded

    Failed --> [*]
    Expired --> [*]
    Voided --> [*]
    Refunded --> [*]
```

---

## Shipment State Machine

```mermaid
stateDiagram-v2
    [*] --> Confirmed: Shipment created
    Confirmed --> Processing: Label generated and pickup prepared
    Processing --> Shipped: Pickup completed
    Shipped --> OutForDelivery: Assigned to agent
    OutForDelivery --> Delivered: Delivery proof accepted

    OutForDelivery --> FailedDelivery: Delivery exception recorded
    FailedDelivery --> OutForDelivery: Rescheduled
    FailedDelivery --> RTOInitiated: Refused or max attempts
    RTOInitiated --> RTODelivered: Returned to origin

    Delivered --> [*]
    RTODelivered --> [*]
```

---

## Return State Machine

```mermaid
stateDiagram-v2
    [*] --> Requested: Customer creates return
    Requested --> Approved: Vendor or admin approves
    Requested --> Rejected: Vendor or admin rejects

    Approved --> ReversePickupAssigned: Reverse pickup created
    ReversePickupAssigned --> PickedUp: Agent pickup completed
    PickedUp --> Received: Warehouse or vendor receives item
    Received --> Refunded: Refund processed

    Rejected --> [*]
    Refunded --> [*]
```

---

## Vendor Onboarding State Machine

```mermaid
stateDiagram-v2
    [*] --> Draft: Registration started
    Draft --> PendingReview: Documents submitted
    PendingReview --> ResubmissionRequired: Documents or bank details need changes
    ResubmissionRequired --> PendingReview: Vendor resubmits
    PendingReview --> Approved: Admin approves
    PendingReview --> Rejected: Admin rejects
    Approved --> Active: Store setup completed
    Active --> Suspended: Compliance or policy issue
    Suspended --> Active: Restored
    Rejected --> [*]
```

---

## Cart State Machine

```mermaid
stateDiagram-v2
    [*] --> Empty: Cart created
    Empty --> Active: Item added
    Active --> Active: Items updated
    Active --> QuoteReady: Checkout quote requested
    QuoteReady --> Active: Cart changed
    QuoteReady --> PendingCheckout: Checkout submitted
    PendingCheckout --> Converted: Order created
    PendingCheckout --> Active: Validation or payment failure
    Active --> Empty: All items removed
    Converted --> [*]
```

---

## Admin OTP Readiness State Machine

```mermaid
stateDiagram-v2
    [*] --> NotEnabled: Privileged account without OTP
    NotEnabled --> SetupStarted: QR/secret generated
    SetupStarted --> EnabledAndVerified: OTP verified
    EnabledAndVerified --> NotEnabled: OTP disabled
```

---

## Status Notes

| Entity | Important Notes |
|--------|-----------------|
| Orders | `PendingPayment` is the starting state for online payments; reservations are committed on payment success and released on failure/expiry |
| Shipments | Shipping-label generation happens during `Processing` and can be reused idempotently |
| Returns | The implemented lifecycle emphasizes `Requested`, `Approved`, `ReversePickupAssigned`, `PickedUp`, `Received`, and `Refunded` |
| Admin OTP | OTP is optional for admins in this pass, but readiness and audit visibility are implemented |
