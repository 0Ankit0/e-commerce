# State Machine Diagrams

## Overview
State machine diagrams showing object state transitions for key entities.

---

## Order State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending: Order Placed
    
    Pending --> Confirmed: Payment Success
    Pending --> Cancelled: Payment Failed
    Pending --> Cancelled: Customer Cancels
    
    Confirmed --> Processing: Vendor Accepts
    Confirmed --> Cancelled: Customer Cancels (before acceptance)
    Confirmed --> Cancelled: Vendor Rejects
    
    Processing --> Packed: Vendor Packs
    Processing --> Cancelled: Customer Cancels (before packing)
    
    Packed --> Shipped: Pickup Complete
    
    Shipped --> InTransit: Line Haul Started
    
    InTransit --> AtHub: Reached Destination Hub
    
    AtHub --> OutForDelivery: Assigned to Agent
    
    OutForDelivery --> Delivered: Delivery Success
    OutForDelivery --> DeliveryFailed: Attempt Failed
    
    DeliveryFailed --> OutForDelivery: Rescheduled
    DeliveryFailed --> RTOInitiated: Max Attempts Exceeded
    DeliveryFailed --> RTOInitiated: Customer Refused
    
    RTOInitiated --> RTOInTransit: Return Started
    RTOInTransit --> RTODelivered: Returned to Vendor
    
    Delivered --> ReturnRequested: Customer Requests Return
    ReturnRequested --> ReturnApproved: Vendor Approves
    ReturnRequested --> ReturnRejected: Vendor Rejects
    ReturnApproved --> ReturnPickedUp: Reverse Pickup Done
    ReturnPickedUp --> Returned: Return Delivered to Vendor
    
    Cancelled --> [*]
    Delivered --> [*]
    RTODelivered --> [*]
    Returned --> [*]
    ReturnRejected --> [*]
```

---

## Order Status Descriptions

| Status | Description |
|--------|-------------|
| **Pending** | Order created, awaiting payment confirmation |
| **Confirmed** | Payment received, awaiting vendor acceptance |
| **Processing** | Vendor accepted, preparing for shipment |
| **Packed** | Order packed, awaiting pickup |
| **Shipped** | Picked up by logistics partner |
| **InTransit** | In line haul transit between hubs |
| **AtHub** | Arrived at destination hub |
| **OutForDelivery** | With delivery agent for final delivery |
| **Delivered** | Successfully delivered to customer |
| **DeliveryFailed** | Delivery attempt unsuccessful |
| **RTOInitiated** | Return to origin initiated |
| **RTOInTransit** | Returning to vendor |
| **RTODelivered** | Returned to vendor |
| **Cancelled** | Order cancelled |
| **ReturnRequested** | Customer requested return |
| **ReturnApproved** | Return approved by vendor |
| **ReturnPickedUp** | Return pickup completed |
| **Returned** | Item returned to vendor |

---

## Payment State Machine

```mermaid
stateDiagram-v2
    [*] --> Created: Payment Order Created
    
    Created --> Pending: Customer Initiates
    
    Pending --> Authorized: Authorization Success
    Pending --> Failed: Authorization Failed
    Pending --> Expired: Timeout
    
    Authorized --> Captured: Capture Success
    Authorized --> Failed: Capture Failed
    Authorized --> Voided: Order Cancelled
    
    Captured --> PartiallyRefunded: Partial Refund
    Captured --> Refunded: Full Refund
    
    PartiallyRefunded --> Refunded: Remaining Refunded
    
    Failed --> [*]
    Expired --> [*]
    Voided --> [*]
    Captured --> [*]
    Refunded --> [*]
```

---

## Payment Status Transitions

| From | To | Trigger |
|------|-----|--------|
| Created | Pending | Customer initiates payment |
| Pending | Authorized | Gateway authorizes payment |
| Pending | Failed | Authorization fails |
| Pending | Expired | Payment timeout (15 min) |
| Authorized | Captured | Payment captured after order confirm |
| Authorized | Voided | Order cancelled before capture |
| Captured | PartiallyRefunded | Partial return processed |
| Captured | Refunded | Full refund processed |

---

## Shipment State Machine

```mermaid
stateDiagram-v2
    [*] --> Created: Shipment Created
    
    Created --> AwaitingPickup: Label Generated
    
    AwaitingPickup --> PickedUp: Pickup Complete
    AwaitingPickup --> PickupFailed: Pickup Failed
    
    PickupFailed --> AwaitingPickup: Rescheduled
    PickupFailed --> Cancelled: Max Attempts
    
    PickedUp --> InTransitToHub: Line Haul Started
    
    InTransitToHub --> ReceivedAtHub: Hub Inbound
    
    ReceivedAtHub --> InTransitToDestination: Outbound Dispatch
    ReceivedAtHub --> SortingException: Sorting Issue
    
    SortingException --> ReceivedAtHub: Issue Resolved
    
    InTransitToDestination --> AtLocalHub: Local Hub Received
    
    AtLocalHub --> OutForDelivery: Agent Assigned
    
    OutForDelivery --> Delivered: POD Captured
    OutForDelivery --> DeliveryException: Delivery Issue
    
    DeliveryException --> OutForDelivery: Reattempt
    DeliveryException --> HeldAtBranch: Customer Request Hold
    DeliveryException --> RTOInitiated: Max Attempts/Refused
    
    HeldAtBranch --> OutForDelivery: Resume Delivery
    HeldAtBranch --> RTOInitiated: Not Collected
    
    RTOInitiated --> RTOInTransit: RTO Started
    RTOInTransit --> RTOReceivedAtHub: RTO at Hub
    RTOReceivedAtHub --> RTODelivered: Returned to Origin
    
    Delivered --> [*]
    RTODelivered --> [*]
    Cancelled --> [*]
```

---

## Vendor State Machine

```mermaid
stateDiagram-v2
    [*] --> Draft: Registration Started
    
    Draft --> PendingApproval: Documents Submitted
    
    PendingApproval --> DocumentsRequired: More Info Needed
    PendingApproval --> Approved: Admin Approves
    PendingApproval --> Rejected: Admin Rejects
    
    DocumentsRequired --> PendingApproval: Documents Resubmitted
    
    Approved --> Active: Store Setup Complete
    
    Active --> Suspended: Policy Violation
    Active --> Inactive: Vendor Request
    
    Suspended --> Active: Suspension Lifted
    Suspended --> Terminated: Severe Violation
    
    Inactive --> Active: Vendor Reactivates
    Inactive --> Terminated: No Activity (1 year)
    
    Rejected --> Draft: Reapply Allowed
    
    Terminated --> [*]
```

---

## Vendor Order State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending: Order Received
    
    Pending --> Accepted: Vendor Accepts
    Pending --> Rejected: Vendor Rejects
    Pending --> AutoCancelled: SLA Breach
    
    Accepted --> Processing: Start Processing
    
    Processing --> Packed: Packing Complete
    
    Packed --> AwaitingPickup: Pickup Scheduled
    
    AwaitingPickup --> Shipped: Pickup Done
    AwaitingPickup --> PickupFailed: Pickup Issue
    
    PickupFailed --> AwaitingPickup: Rescheduled
    
    Shipped --> Delivered: Delivery Confirmed
    Shipped --> RTO: Return to Origin
    
    RTO --> RTOReceived: RTO Complete
    
    Delivered --> PartialReturn: Partial Return
    Delivered --> FullReturn: Full Return
    
    PartialReturn --> Completed: Settled
    FullReturn --> Completed: Settled
    
    RTOReceived --> Completed: Settled
    Rejected --> [*]
    AutoCancelled --> [*]
    Completed --> [*]
```

---

## Return State Machine

```mermaid
stateDiagram-v2
    [*] --> Requested: Customer Requests
    
    Requested --> PendingApproval: Auto-eligible
    Requested --> UnderReview: Manual Review Required
    
    UnderReview --> PendingApproval: Approved
    UnderReview --> Rejected: Denied
    
    PendingApproval --> Approved: Vendor Approves
    PendingApproval --> Rejected: Vendor Rejects
    PendingApproval --> EscalatedToAdmin: Dispute
    
    EscalatedToAdmin --> Approved: Admin Approves
    EscalatedToAdmin --> Rejected: Admin Denies
    
    Approved --> PickupScheduled: Pickup Created
    
    PickupScheduled --> PickedUp: Reverse Pickup Done
    PickupScheduled --> PickupFailed: Pickup Issue
    
    PickupFailed --> PickupScheduled: Rescheduled
    PickupFailed --> Cancelled: Max Attempts
    
    PickedUp --> InTransit: Return Shipped
    
    InTransit --> ReceivedByVendor: Vendor Receives
    
    ReceivedByVendor --> QCPassed: Quality Check OK
    ReceivedByVendor --> QCFailed: Quality Issue
    
    QCFailed --> DisputeRaised: Vendor Disputes
    DisputeRaised --> QCPassed: Admin Rules for Customer
    DisputeRaised --> Rejected: Admin Rules for Vendor
    
    QCPassed --> RefundInitiated: Refund Started
    
    RefundInitiated --> Completed: Refund Processed
    
    Rejected --> [*]
    Cancelled --> [*]
    Completed --> [*]
```

---

## Cart State Machine

```mermaid
stateDiagram-v2
    [*] --> Empty: Cart Created
    
    Empty --> Active: Item Added
    
    Active --> Active: Item Added/Updated
    Active --> Empty: All Items Removed
    Active --> CheckingOut: Checkout Started
    
    CheckingOut --> Active: Checkout Abandoned
    CheckingOut --> PaymentPending: Order Created
    
    PaymentPending --> Converted: Payment Success
    PaymentPending --> Active: Payment Failed
    
    Converted --> [*]
    
    note right of Active: Auto-expires after 7 days of inactivity
    
    Active --> Expired: No Activity (7 days)
    Expired --> [*]
```

---

## Delivery Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> Offline: Account Created
    
    Offline --> Available: Agent Logs In
    
    Available --> OnRoute: Route Started
    Available --> OnBreak: Break Started
    
    OnBreak --> Available: Break Ended
    OnBreak --> Offline: Log Out
    
    OnRoute --> AtDelivery: Reached Location
    OnRoute --> Available: Route Completed
    
    AtDelivery --> OnRoute: Delivery Done
    AtDelivery --> OnRoute: Skip/Failed
    
    Available --> Offline: Log Out
    OnRoute --> Offline: Emergency Log Out
    
    Offline --> [*]
```
