# Use Case Descriptions

## Customer Use Cases

### UC-CUS-001: Place Order

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-CUS-001 |
| **Name** | Place Order |
| **Actor** | Customer |
| **Description** | Customer completes the checkout process to place an order |
| **Preconditions** | - Customer is logged in<br>- Cart has at least one item<br>- Items are in stock |
| **Postconditions** | - Order is created<br>- Payment is processed<br>- Vendor is notified<br>- Confirmation sent to customer |

**Main Flow:**
1. Customer clicks "Proceed to Checkout"
2. System validates cart items are available
3. System displays saved addresses
4. Customer selects delivery address
5. System calculates shipping charges
6. Customer selects payment method
7. Customer applies coupon (optional)
8. System displays order summary with total
9. Customer confirms order
10. System redirects to payment gateway
11. Customer completes payment
12. System creates order and notifies vendor
13. System displays order confirmation

**Alternative Flows:**

| ID | Condition | Flow |
|----|-----------|------|
| A1 | Item out of stock | System shows error, suggests alternatives |
| A2 | Address not serviceable | System prompts to enter different address |
| A3 | Payment fails | System shows error, allows retry |
| A4 | Coupon invalid | System shows error message |

**Exception Flows:**

| ID | Condition | Flow |
|----|-----------|------|
| E1 | Session expires | Redirect to login, preserve cart |
| E2 | Payment gateway timeout | Show error, allow retry |

---

### UC-CUS-002: Track Order

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-CUS-002 |
| **Name** | Track Order |
| **Actor** | Customer |
| **Description** | Customer views real-time status and location of their order |
| **Preconditions** | - Customer is logged in<br>- Order exists and is not delivered |
| **Postconditions** | - Tracking information displayed |

**Main Flow:**
1. Customer navigates to "My Orders"
2. Customer clicks on specific order
3. System displays order details
4. Customer clicks "Track Order"
5. System shows shipment timeline with milestones
6. System displays current location on map (if in transit)
7. System shows estimated delivery date/time

**Status Milestones:**
- Order Placed
- Order Confirmed by Vendor
- Packed & Ready for Pickup
- Picked Up by Logistics
- In Transit to Hub
- At Local Hub
- Out for Delivery
- Delivered

---

### UC-CUS-003: Request Return

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-CUS-003 |
| **Name** | Request Return |
| **Actor** | Customer |
| **Description** | Customer initiates return for a delivered order |
| **Preconditions** | - Order is delivered<br>- Within return window (e.g., 7 days)<br>- Product is returnable |
| **Postconditions** | - Return request created<br>- Reverse pickup scheduled<br>- Vendor notified |

**Main Flow:**
1. Customer navigates to order details
2. Customer clicks "Return Item"
3. System shows return eligibility
4. Customer selects items to return
5. Customer selects return reason
6. Customer adds photos (if applicable)
7. Customer selects refund method (original/wallet)
8. System creates return request
9. System schedules reverse pickup
10. System sends confirmation email

**Return Reasons:**
- Wrong item delivered
- Damaged product
- Quality not as expected
- Size/fit issue
- Changed mind

---

## Vendor Use Cases

### UC-VEN-001: Add Product

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-VEN-001 |
| **Name** | Add Product |
| **Actor** | Vendor |
| **Description** | Vendor creates a new product listing |
| **Preconditions** | - Vendor is logged in<br>- Vendor account is approved |
| **Postconditions** | - Product is created (pending/active based on approval policy) |

**Main Flow:**
1. Vendor navigates to Products > Add Product
2. System displays product form
3. Vendor enters basic info (name, description)
4. Vendor selects category
5. System shows category-specific attributes
6. Vendor fills attribute values
7. Vendor uploads product images (min 3)
8. Vendor sets pricing (MRP, selling price)
9. Vendor adds variants (size, color, etc.)
10. Vendor sets inventory per variant
11. Vendor sets shipping dimensions/weight
12. Vendor previews listing
13. Vendor submits product
14. System validates and saves product
15. System queues for approval (if required)

**Validation Rules:**
- Minimum 3 images required
- Selling price ≤ MRP
- At least one variant with stock > 0
- Category must be selected

---

### UC-VEN-002: Process Order

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-VEN-002 |
| **Name** | Process Order |
| **Actor** | Vendor |
| **Description** | Vendor accepts and fulfills an incoming order |
| **Preconditions** | - Order is placed<br>- Order status is "Pending with Vendor" |
| **Postconditions** | - Order is packed<br>- Shipping label generated<br>- Pickup scheduled |

**Main Flow:**
1. Vendor receives new order notification
2. Vendor navigates to Orders > New
3. Vendor views order details
4. Vendor clicks "Accept Order"
5. System updates order status to "Processing"
6. Vendor packs the order
7. Vendor clicks "Mark as Packed"
8. System generates shipping label
9. Vendor prints and attaches label
10. Vendor clicks "Schedule Pickup"
11. System schedules pickup with logistics partner
12. System notifies customer of shipment

**Alternative Flows:**

| ID | Condition | Flow |
|----|-----------|------|
| A1 | Item out of stock | Vendor rejects order with reason |
| A2 | Partial availability | Vendor contacts customer for confirmation |

---

### UC-VEN-003: View Analytics

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-VEN-003 |
| **Name** | View Analytics |
| **Actor** | Vendor |
| **Description** | Vendor views sales and performance analytics |
| **Preconditions** | - Vendor is logged in |
| **Postconditions** | - Analytics dashboard displayed |

**Main Flow:**
1. Vendor navigates to Analytics
2. System displays overview dashboard
3. Dashboard shows:
   - Total sales (amount, orders)
   - Sales trend chart
   - Top selling products
   - Low stock alerts
   - Pending orders count
   - Average order value
   - Customer ratings
4. Vendor selects date range filter
5. System updates charts accordingly
6. Vendor can export data as CSV

---

## Admin Use Cases

### UC-ADM-001: Approve Vendor

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-ADM-001 |
| **Name** | Approve Vendor |
| **Actor** | Admin |
| **Description** | Admin reviews and approves vendor application |
| **Preconditions** | - Vendor registration submitted<br>- Documents uploaded |
| **Postconditions** | - Vendor status updated<br>- Notification sent to vendor |

**Main Flow:**
1. Admin navigates to Vendors > Pending Approval
2. System displays list of pending applications
3. Admin clicks on vendor to review
4. System shows vendor details:
   - Business information
   - Owner details
   - Bank account info
   - Uploaded documents (GST, PAN, etc.)
5. Admin verifies documents
6. Admin clicks "Approve"
7. System activates vendor account
8. System sends approval email to vendor
9. Vendor can now add products

**Alternative Flows:**

| ID | Condition | Flow |
|----|-----------|------|
| A1 | Documents unclear | Admin requests re-upload |
| A2 | Details mismatch | Admin rejects with reason |
| A3 | Blacklisted business | Admin rejects application |

---

### UC-ADM-002: Manage Delivery Zones

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-ADM-002 |
| **Name** | Manage Delivery Zones |
| **Actor** | Admin |
| **Description** | Admin configures delivery zones and shipping rates |
| **Preconditions** | - Admin has logistics management permission |
| **Postconditions** | - Zones and rates updated in system |

**Main Flow:**
1. Admin navigates to Logistics > Delivery Zones
2. System displays zone management interface
3. Admin clicks "Add Zone"
4. Admin enters zone details:
   - Zone name
   - Pincodes/areas covered
   - Assigned branch
   - Delivery TAT (turnaround time)
5. Admin sets shipping rates:
   - Base rate
   - Per kg rate
   - COD charges
   - Express delivery premium
6. Admin saves zone configuration
7. System validates pincode uniqueness
8. System activates zone

---

## Delivery Use Cases

### UC-DEL-001: Complete Delivery

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-DEL-001 |
| **Name** | Complete Delivery |
| **Actor** | Delivery Agent |
| **Description** | Delivery agent delivers package and captures proof |
| **Preconditions** | - Delivery assigned to agent<br>- Agent has package |
| **Postconditions** | - Delivery marked complete<br>- POD captured<br>- Customer notified |

**Main Flow:**
1. Agent opens delivery app
2. Agent views assigned deliveries
3. Agent selects delivery to complete
4. App shows customer address and contact
5. Agent navigates to address
6. Agent arrives and clicks "Reached"
7. Agent hands over package
8. Agent clicks "Capture POD"
9. System options:
   - Enter customer OTP
   - Capture photo of delivered package
   - Get customer signature
10. Agent confirms delivery
11. System updates delivery status
12. System notifies customer
13. Agent proceeds to next delivery

**Alternative Flows:**

| ID | Condition | Flow |
|----|-----------|------|
| A1 | Customer unavailable | Agent marks "Customer not available", reschedules |
| A2 | Wrong address | Agent contacts customer or marks exception |
| A3 | Customer refuses | Agent marks "Refused", initiates RTO |

---

### UC-HUB-001: Process Inbound Shipment

| Attribute | Description |
|-----------|-------------|
| **Use Case ID** | UC-HUB-001 |
| **Name** | Process Inbound Shipment |
| **Actor** | Hub Operator |
| **Description** | Hub operator receives and processes incoming shipments |
| **Preconditions** | - Vehicle arrived at hub<br>- Manifest available |
| **Postconditions** | - All packages scanned and verified<br>- Exceptions logged<br>- Packages ready for sorting |

**Main Flow:**
1. Operator receives arrival notification
2. Operator opens inbound processing screen
3. Operator scans manifest barcode
4. System displays expected package list
5. Operator scans each package
6. System marks package as received
7. System shows running count (received/expected)
8. Operator completes scanning
9. System reconciles:
   - Matched packages
   - Missing packages
   - Extra packages
10. Operator confirms exceptions
11. System generates inbound report
12. Packages move to sorting area

**Exception Handling:**

| Exception | Action |
|-----------|--------|
| Missing package | Log as missing, notify origin hub |
| Damaged package | Photo capture, damage report |
| Extra package | Scan and add to inventory |
