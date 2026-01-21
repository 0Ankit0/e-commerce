# Activity Diagrams

## Overview
Activity diagrams showing the business process flows for key operations in the e-commerce system.

---

## Order Placement Flow

```mermaid
flowchart TD
    Start([Customer opens app]) --> Browse[Browse Products]
    Browse --> Search{Search or<br>Category?}
    Search -->|Search| SearchResults[View Search Results]
    Search -->|Category| CategoryList[View Category Products]
    SearchResults --> SelectProduct[Select Product]
    CategoryList --> SelectProduct
    
    SelectProduct --> ViewDetails[View Product Details]
    ViewDetails --> CheckStock{In Stock?}
    CheckStock -->|No| Notify[Notify When Available]
    Notify --> Browse
    CheckStock -->|Yes| AddCart{Add to Cart?}
    AddCart -->|No| Browse
    AddCart -->|Yes| SelectVariant[Select Variant/Qty]
    SelectVariant --> AddToCart[Add to Cart]
    AddToCart --> Continue{Continue<br>Shopping?}
    Continue -->|Yes| Browse
    Continue -->|No| ViewCart[View Cart]
    
    ViewCart --> ValidateCart{Cart Valid?}
    ValidateCart -->|Items OOS| RemoveOOS[Remove OOS Items]
    RemoveOOS --> ViewCart
    ValidateCart -->|Valid| Checkout[Proceed to Checkout]
    
    Checkout --> LoggedIn{Logged In?}
    LoggedIn -->|No| Login[Login/Register]
    Login --> SelectAddress
    LoggedIn -->|Yes| SelectAddress[Select Delivery Address]
    
    SelectAddress --> HasAddress{Has Saved<br>Address?}
    HasAddress -->|No| AddAddress[Add New Address]
    AddAddress --> Serviceable
    HasAddress -->|Yes| ChooseAddress[Choose Address]
    ChooseAddress --> Serviceable{Serviceable?}
    Serviceable -->|No| AddAddress
    Serviceable -->|Yes| ApplyCoupon{Apply Coupon?}
    
    ApplyCoupon -->|Yes| EnterCoupon[Enter Coupon Code]
    EnterCoupon --> ValidCoupon{Valid?}
    ValidCoupon -->|No| ShowError[Show Error]
    ShowError --> ApplyCoupon
    ValidCoupon -->|Yes| SelectPayment
    ApplyCoupon -->|No| SelectPayment[Select Payment Method]
    
    SelectPayment --> ReviewOrder[Review Order Summary]
    ReviewOrder --> PlaceOrder[Place Order]
    PlaceOrder --> ProcessPayment{Payment<br>Method?}
    
    ProcessPayment -->|COD| CreateOrder[Create Order]
    ProcessPayment -->|Online| RedirectPG[Redirect to Gateway]
    RedirectPG --> PaymentComplete{Payment<br>Success?}
    PaymentComplete -->|No| PaymentFailed[Show Failure]
    PaymentFailed --> SelectPayment
    PaymentComplete -->|Yes| CreateOrder
    
    CreateOrder --> SplitOrder[Split by Vendor]
    SplitOrder --> NotifyVendors[Notify Vendors]
    NotifyVendors --> SendConfirmation[Send Confirmation]
    SendConfirmation --> ShowConfirmation[Show Order Confirmation]
    ShowConfirmation --> End([End])
```

---

## Order Fulfillment Flow (Vendor)

```mermaid
flowchart TD
    Start([New Order Received]) --> Notification[Vendor Notification]
    Notification --> ViewOrder[View Order Details]
    ViewOrder --> CheckInventory{Stock<br>Available?}
    
    CheckInventory -->|No| RejectOrder[Reject Order]
    RejectOrder --> SelectReason[Select Reason]
    SelectReason --> NotifyCustomer[Notify Customer]
    NotifyCustomer --> RefundInitiate[Initiate Refund]
    RefundInitiate --> End1([Order Cancelled])
    
    CheckInventory -->|Yes| AcceptOrder[Accept Order]
    AcceptOrder --> UpdateStatus[Update Order Status]
    UpdateStatus --> PickItems[Pick Items from Inventory]
    PickItems --> PackOrder[Pack Order]
    PackOrder --> QualityCheck{Quality<br>Check OK?}
    
    QualityCheck -->|No| RepackRequired[Repack Required]
    RepackRequired --> PackOrder
    QualityCheck -->|Yes| GenerateLabel[Generate Shipping Label]
    
    GenerateLabel --> PrintLabel[Print & Attach Label]
    PrintLabel --> MarkPacked[Mark as Packed]
    MarkPacked --> SchedulePickup[Schedule Pickup]
    SchedulePickup --> WaitPickup[Wait for Pickup]
    WaitPickup --> PickupArrives[Pickup Agent Arrives]
    PickupArrives --> HandoverPackage[Handover Package]
    HandoverPackage --> ScanConfirm[Scan & Confirm]
    ScanConfirm --> UpdateShipped[Update as Shipped]
    UpdateShipped --> NotifyCustomer2[Notify Customer]
    NotifyCustomer2 --> End2([Shipment Initiated])
```

---

## Payment Processing Flow

```mermaid
flowchart TD
    Start([Initiate Payment]) --> SelectMethod{Payment<br>Method}
    
    SelectMethod -->|Credit/Debit Card| CardFlow[Card Payment Flow]
    SelectMethod -->|UPI| UPIFlow[UPI Payment Flow]
    SelectMethod -->|Net Banking| NBFlow[Net Banking Flow]
    SelectMethod -->|Wallet| WalletFlow[Wallet Flow]
    SelectMethod -->|COD| CODFlow[COD Flow]
    
    subgraph Card["Card Payment"]
        CardFlow --> EnterCard[Enter Card Details]
        EnterCard --> Validate3DS{3DS Required?}
        Validate3DS -->|Yes| OTP3DS[Enter OTP]
        OTP3DS --> AuthCard
        Validate3DS -->|No| AuthCard[Authorize Card]
    end
    
    subgraph UPI["UPI Payment"]
        UPIFlow --> EnterVPA[Enter UPI ID]
        EnterVPA --> SendRequest[Send Payment Request]
        SendRequest --> WaitApproval[Wait for Approval]
        WaitApproval --> UserApproves{Approved?}
        UserApproves -->|Yes| AuthUPI[Payment Authorized]
        UserApproves -->|No| UPIFailed[Payment Failed]
    end
    
    subgraph NB["Net Banking"]
        NBFlow --> SelectBank[Select Bank]
        SelectBank --> RedirectBank[Redirect to Bank]
        RedirectBank --> BankLogin[Bank Login]
        BankLogin --> AuthNB[Authorize Payment]
    end
    
    subgraph Wallet["Wallet"]
        WalletFlow --> CheckBalance{Sufficient<br>Balance?}
        CheckBalance -->|No| AddMoney[Suggest Add Money]
        AddMoney --> SelectMethod
        CheckBalance -->|Yes| DeductWallet[Deduct from Wallet]
        DeductWallet --> AuthWallet[Payment Authorized]
    end
    
    subgraph COD["Cash on Delivery"]
        CODFlow --> ValidateCOD{COD<br>Eligible?}
        ValidateCOD -->|No| SelectMethod
        ValidateCOD -->|Yes| ConfirmCOD[Confirm COD Order]
    end
    
    AuthCard --> PaymentSuccess
    AuthUPI --> PaymentSuccess
    AuthNB --> PaymentSuccess
    AuthWallet --> PaymentSuccess
    ConfirmCOD --> OrderCreation
    
    PaymentSuccess{Success?}
    PaymentSuccess -->|Yes| CapturePayment[Capture Payment]
    PaymentSuccess -->|No| HandleFailure[Handle Failure]
    HandleFailure --> RetryOption{Retry?}
    RetryOption -->|Yes| SelectMethod
    RetryOption -->|No| End1([Order Abandoned])
    
    CapturePayment --> OrderCreation[Create Order]
    OrderCreation --> SendReceipt[Send Receipt]
    SendReceipt --> End2([Payment Complete])
```

---

## Line Haul Transit Flow

```mermaid
flowchart TD
    Start([Packages Ready at Origin]) --> Consolidate[Consolidate Shipments]
    Consolidate --> CreateManifest[Create Manifest]
    CreateManifest --> AssignVehicle[Assign Vehicle]
    AssignVehicle --> LoadVehicle[Load Packages]
    LoadVehicle --> ScanLoad[Scan Each Package]
    ScanLoad --> VerifyCount{Count<br>Matches?}
    
    VerifyCount -->|No| Reconcile[Reconcile Discrepancy]
    Reconcile --> ScanLoad
    VerifyCount -->|Yes| DispatchVehicle[Dispatch Vehicle]
    
    DispatchVehicle --> InTransit[In Transit]
    InTransit --> UpdateLocation[Update GPS Location]
    UpdateLocation --> Checkpoints{Checkpoint?}
    
    Checkpoints -->|Yes| LogCheckpoint[Log Checkpoint]
    LogCheckpoint --> InTransit
    Checkpoints -->|No| ReachedHub{Reached<br>Destination?}
    
    ReachedHub -->|No| CheckException{Any Issues?}
    CheckException -->|Yes| LogException[Log Exception]
    LogException --> NotifyControl[Notify Control Room]
    NotifyControl --> InTransit
    CheckException -->|No| InTransit
    
    ReachedHub -->|Yes| ArriveHub[Arrive at Hub]
    ArriveHub --> UnloadVehicle[Unload Packages]
    UnloadVehicle --> ScanInbound[Scan Inbound]
    ScanInbound --> VerifyManifest{Manifest<br>Match?}
    
    VerifyManifest -->|No| LogMissing[Log Missing/Extra]
    LogMissing --> ProcessException[Process Exceptions]
    ProcessException --> CompleteInbound
    VerifyManifest -->|Yes| CompleteInbound[Complete Inbound]
    
    CompleteInbound --> SortPackages[Sort for Next Leg]
    SortPackages --> End([Ready for Dispatch/Delivery])
```

---

## Last Mile Delivery Flow

```mermaid
flowchart TD
    Start([Packages at Branch]) --> AssignAgent[Assign to Delivery Agent]
    AssignAgent --> OptimizeRoute[Optimize Route]
    OptimizeRoute --> LoadBag[Load Delivery Bag]
    LoadBag --> ScanOut[Scan Outbound]
    ScanOut --> StartRoute[Start Delivery Route]
    
    StartRoute --> NavigateAddress[Navigate to Address]
    NavigateAddress --> ArriveLocation[Arrive at Location]
    ArriveLocation --> ContactCustomer[Contact Customer]
    
    ContactCustomer --> CustomerAvailable{Customer<br>Available?}
    CustomerAvailable -->|No| Attempt2[Second Attempt Call]
    Attempt2 --> Available2{Available?}
    Available2 -->|No| MarkFailed[Mark Failed Attempt]
    MarkFailed --> RescheduleOption{Reschedule?}
    RescheduleOption -->|Yes| SetNewDate[Set New Date]
    SetNewDate --> NextDelivery
    RescheduleOption -->|No| ReturnPackage[Return to Branch]
    ReturnPackage --> NextDelivery
    
    Available2 -->|Yes| HandOver
    CustomerAvailable -->|Yes| HandOver[Hand Over Package]
    
    HandOver --> CapturePOD{POD Method}
    CapturePOD -->|OTP| EnterOTP[Enter Customer OTP]
    CapturePOD -->|Photo| TakePhoto[Take Delivery Photo]
    CapturePOD -->|Signature| GetSignature[Get Signature]
    
    EnterOTP --> VerifyOTP{Valid?}
    VerifyOTP -->|No| EnterOTP
    VerifyOTP -->|Yes| MarkDelivered
    TakePhoto --> MarkDelivered
    GetSignature --> MarkDelivered
    
    MarkDelivered[Mark as Delivered] --> UpdateSystem[Update System]
    UpdateSystem --> NotifyCustomer[Notify Customer]
    NotifyCustomer --> NextDelivery{More<br>Deliveries?}
    
    NextDelivery -->|Yes| NavigateAddress
    NextDelivery -->|No| ReturnBranch[Return to Branch]
    ReturnBranch --> ReconcileDeliveries[Reconcile Deliveries]
    ReconcileDeliveries --> SubmitReport[Submit Daily Report]
    SubmitReport --> End([Shift Complete])
```

---

## Return & Refund Flow

```mermaid
flowchart TD
    Start([Customer Requests Return]) --> CheckEligibility{Return<br>Eligible?}
    
    CheckEligibility -->|No| ShowReason[Show Ineligibility Reason]
    ShowReason --> End1([Cannot Return])
    
    CheckEligibility -->|Yes| SelectItems[Select Items to Return]
    SelectItems --> SelectReason[Select Return Reason]
    SelectReason --> UploadPhotos{Photos<br>Required?}
    
    UploadPhotos -->|Yes| AddPhotos[Upload Product Photos]
    AddPhotos --> SelectRefund
    UploadPhotos -->|No| SelectRefund[Select Refund Method]
    
    SelectRefund --> SubmitRequest[Submit Return Request]
    SubmitRequest --> NotifyVendor[Notify Vendor]
    NotifyVendor --> VendorReview{Vendor<br>Approves?}
    
    VendorReview -->|No| Escalate[Escalate to Admin]
    Escalate --> AdminReview{Admin<br>Decision}
    AdminReview -->|Reject| NotifyRejection[Notify Rejection]
    NotifyRejection --> End2([Return Rejected])
    AdminReview -->|Approve| SchedulePickup
    
    VendorReview -->|Yes| SchedulePickup[Schedule Reverse Pickup]
    SchedulePickup --> NotifySchedule[Notify Customer]
    NotifySchedule --> PickupAgent[Pickup Agent Arrives]
    PickupAgent --> CollectPackage[Collect Package]
    CollectPackage --> ScanReturn[Scan Return AWB]
    ScanReturn --> TransitToVendor[Transit to Vendor]
    
    TransitToVendor --> VendorReceives[Vendor Receives]
    VendorReceives --> QualityCheck{Quality<br>Check}
    
    QualityCheck -->|Fail| DisputeRaise[Raise Dispute]
    DisputeRaise --> AdminResolve[Admin Resolution]
    AdminResolve --> RefundDecision{Refund<br>Approved?}
    RefundDecision -->|No| End3([Refund Denied])
    RefundDecision -->|Yes| ProcessRefund
    
    QualityCheck -->|Pass| ProcessRefund[Process Refund]
    ProcessRefund --> RefundMethod{Refund To}
    
    RefundMethod -->|Original| RefundOriginal[Refund to Original Method]
    RefundMethod -->|Wallet| RefundWallet[Credit to Wallet]
    
    RefundOriginal --> ConfirmRefund[Confirm Refund]
    RefundWallet --> ConfirmRefund
    ConfirmRefund --> NotifyComplete[Notify Customer]
    NotifyComplete --> End4([Return Complete])
```
