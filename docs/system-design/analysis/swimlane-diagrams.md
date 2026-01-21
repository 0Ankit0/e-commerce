# Swimlane Diagrams (BPMN)

## Overview
Cross-department workflow diagrams showing responsibilities and handoffs between different actors and systems.

---

## Order-to-Delivery Workflow

```mermaid
flowchart TB
    subgraph Customer["👤 Customer"]
        C1[Place Order]
        C2[Make Payment]
        C3[Track Order]
        C4[Receive Delivery]
        C5[Provide Feedback]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Validate Order]
        P2[Process Payment]
        P3[Split by Vendor]
        P4[Send Notifications]
        P5[Update Tracking]
    end
    
    subgraph Vendor["🏪 Vendor"]
        V1[Receive Order]
        V2[Accept Order]
        V3[Pack Order]
        V4[Generate Label]
        V5[Handover to Pickup]
    end
    
    subgraph Logistics["🚚 Logistics"]
        L1[Pickup from Vendor]
        L2[Line Haul Transit]
        L3[Hub Processing]
        L4[Last Mile Delivery]
        L5[Capture POD]
    end
    
    C1 --> P1
    P1 --> C2
    C2 --> P2
    P2 --> P3
    P3 --> V1
    P3 --> P4
    V1 --> V2
    V2 --> V3
    V3 --> V4
    V4 --> V5
    V5 --> L1
    L1 --> P5
    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> C4
    L4 --> L5
    L5 --> P5
    P5 --> C3
    C4 --> C5
```

---

## Vendor Onboarding Workflow

```mermaid
flowchart TB
    subgraph Vendor["🏪 Vendor"]
        V1[Submit Application]
        V2[Upload Documents]
        V3[Add Bank Details]
        V4[Resubmit if Rejected]
        V5[Setup Store]
        V6[Add Products]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Receive Application]
        P2[Validate Documents]
        P3[Queue for Review]
        P4[Send Status Notification]
        P5[Activate Account]
    end
    
    subgraph Admin["👨‍💼 Admin"]
        A1[Review Application]
        A2[Verify Business Details]
        A3[Verify Documents]
        A4[Decision]
        A5[Approve/Reject]
    end
    
    subgraph Finance["💰 Finance"]
        F1[Verify Bank Account]
        F2[Setup Payout Method]
    end
    
    V1 --> P1
    P1 --> V2
    V2 --> P2
    P2 --> V3
    V3 --> F1
    F1 --> P3
    P3 --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 -->|Reject| P4
    P4 --> V4
    V4 --> V2
    A4 -->|Approve| A5
    A5 --> F2
    F2 --> P5
    P5 --> V5
    V5 --> V6
```

---

## Return Processing Workflow

```mermaid
flowchart TB
    subgraph Customer["👤 Customer"]
        C1[Request Return]
        C2[Pack Item]
        C3[Handover to Agent]
        C4[Receive Refund]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Validate Return Request]
        P2[Create Return Order]
        P3[Schedule Pickup]
        P4[Track Return]
        P5[Process Refund]
    end
    
    subgraph Vendor["🏪 Vendor"]
        V1[Review Return Request]
        V2[Approve/Reject]
        V3[Receive Returned Item]
        V4[Quality Check]
        V5[Confirm Refund]
    end
    
    subgraph Logistics["🚚 Logistics"]
        L1[Pickup from Customer]
        L2[Transit to Vendor]
        L3[Deliver to Vendor]
    end
    
    subgraph Finance["💰 Finance"]
        F1[Initiate Refund]
        F2[Process Payment Reversal]
        F3[Update Settlement]
    end
    
    C1 --> P1
    P1 --> P2
    P2 --> V1
    V1 --> V2
    V2 -->|Approve| P3
    V2 -->|Reject| C1
    P3 --> C2
    C2 --> L1
    L1 --> C3
    C3 --> L2
    L2 --> P4
    L2 --> L3
    L3 --> V3
    V3 --> V4
    V4 -->|Pass| V5
    V4 -->|Fail| P1
    V5 --> P5
    P5 --> F1
    F1 --> F2
    F2 --> F3
    F2 --> C4
```

---

## Payment & Settlement Workflow

```mermaid
flowchart TB
    subgraph Customer["👤 Customer"]
        C1[Initiate Payment]
        C2[Complete Payment]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Create Payment Order]
        P2[Redirect to Gateway]
        P3[Receive Callback]
        P4[Verify Payment]
        P5[Create Order]
        P6[Calculate Commission]
    end
    
    subgraph PaymentGateway["💳 Payment Gateway"]
        PG1[Display Payment Page]
        PG2[Process Payment]
        PG3[Send Callback]
        PG4[Settle to Platform]
    end
    
    subgraph Finance["💰 Finance"]
        F1[Record Transaction]
        F2[Hold for Settlement]
        F3[Calculate Vendor Share]
        F4[Schedule Payout]
        F5[Execute Payout]
    end
    
    subgraph Vendor["🏪 Vendor"]
        V1[View Earnings]
        V2[Request Payout]
        V3[Receive Payout]
    end
    
    subgraph Bank["🏦 Bank"]
        B1[Receive Transfer Request]
        B2[Process Transfer]
        B3[Confirm Transfer]
    end
    
    C1 --> P1
    P1 --> P2
    P2 --> PG1
    PG1 --> C2
    C2 --> PG2
    PG2 --> PG3
    PG3 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
    P6 --> F1
    PG4 --> F2
    F2 --> F3
    F3 --> V1
    V1 --> V2
    V2 --> F4
    F4 --> F5
    F5 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> V3
```

---

## Line Haul Operations Workflow

```mermaid
flowchart TB
    subgraph OriginHub["📦 Origin Hub"]
        O1[Receive Packages]
        O2[Sort by Destination]
        O3[Create Manifest]
        O4[Load Vehicle]
        O5[Dispatch]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Track Shipments]
        P2[Update Status]
        P3[Handle Exceptions]
        P4[Calculate ETAs]
    end
    
    subgraph Transit["🚛 Transit"]
        T1[Start Journey]
        T2[Checkpoint Updates]
        T3[Report Issues]
        T4[Arrive at Destination]
    end
    
    subgraph DestinationHub["📦 Destination Hub"]
        D1[Receive Vehicle]
        D2[Unload Packages]
        D3[Scan & Verify]
        D4[Reconcile Manifest]
        D5[Sort for Delivery]
    end
    
    subgraph LastMile["🛵 Last Mile"]
        L1[Assign to Agent]
        L2[Route Optimization]
        L3[Out for Delivery]
    end
    
    O1 --> O2
    O2 --> O3
    O3 --> P1
    O3 --> O4
    O4 --> O5
    O5 --> T1
    T1 --> T2
    T2 --> P2
    T2 --> T3
    T3 --> P3
    T2 --> T4
    T4 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> P2
    D4 --> D5
    D5 --> L1
    L1 --> P4
    L1 --> L2
    L2 --> L3
```

---

## Customer Support Escalation Workflow

```mermaid
flowchart TB
    subgraph Customer["👤 Customer"]
        C1[Raise Issue]
        C2[Provide Details]
        C3[Receive Resolution]
        C4[Rate Support]
    end
    
    subgraph Support["🎧 Support Team"]
        S1[Receive Ticket]
        S2[Categorize Issue]
        S3[Attempt Resolution]
        S4[Escalate if Needed]
        S5[Close Ticket]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Create Ticket]
        P2[Auto-categorize]
        P3[Route to Agent]
        P4[Track SLA]
        P5[Send Updates]
    end
    
    subgraph Vendor["🏪 Vendor"]
        V1[Receive Escalation]
        V2[Investigate]
        V3[Provide Response]
    end
    
    subgraph Admin["👨‍💼 Admin"]
        A1[Review Escalation]
        A2[Make Decision]
        A3[Override if Needed]
    end
    
    C1 --> P1
    P1 --> C2
    C2 --> P2
    P2 --> P3
    P3 --> S1
    S1 --> S2
    S2 --> S3
    S3 -->|Resolved| S5
    S3 -->|Vendor Issue| S4
    S4 --> V1
    V1 --> V2
    V2 --> V3
    V3 --> S3
    S3 -->|Admin Needed| A1
    A1 --> A2
    A2 --> A3
    A3 --> S5
    S5 --> P5
    P5 --> C3
    C3 --> C4
    P4 --> S1
```

---

## Inventory Sync Workflow

```mermaid
flowchart TB
    subgraph Vendor["🏪 Vendor"]
        V1[Update Stock in ERP]
        V2[Manual Update on Platform]
        V3[Receive Low Stock Alert]
        V4[Restock Items]
    end
    
    subgraph VendorERP["📊 Vendor ERP"]
        E1[Stock Changed]
        E2[Send Webhook]
    end
    
    subgraph Platform["🖥️ Platform"]
        P1[Receive Stock Update]
        P2[Validate Update]
        P3[Update Inventory DB]
        P4[Check Thresholds]
        P5[Send Alerts]
        P6[Update Product Availability]
    end
    
    subgraph Orders["📦 Orders"]
        O1[New Order Placed]
        O2[Reserve Stock]
        O3[Confirm Stock Deduction]
    end
    
    V1 --> E1
    E1 --> E2
    E2 --> P1
    V2 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 -->|Low Stock| P5
    P5 --> V3
    V3 --> V4
    V4 --> V1
    P4 --> P6
    O1 --> O2
    O2 --> P3
    P3 --> O3
```
