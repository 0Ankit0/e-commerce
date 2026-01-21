# User Stories

## Customer User Stories

### Account Management

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| CUS-001 | As a customer, I want to register with my email so that I can create an account | - Email validation<br>- OTP verification<br>- Profile creation |
| CUS-002 | As a customer, I want to login with social accounts so that I can access quickly | - Google login works<br>- Facebook login works<br>- Account linking |
| CUS-003 | As a customer, I want to reset my password so that I can recover my account | - Reset link sent<br>- Link expires in 24h<br>- Password updated |
| CUS-004 | As a customer, I want to manage my profile so that my info stays current | - Edit name/phone<br>- Upload avatar<br>- Save changes |

### Shopping Experience

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| CUS-005 | As a customer, I want to search products so that I can find items quickly | - Instant results<br>- Typo tolerance<br>- Relevant sorting |
| CUS-006 | As a customer, I want to filter products so that I can narrow options | - Price range filter<br>- Brand filter<br>- Rating filter |
| CUS-007 | As a customer, I want to view product details so that I can make informed decisions | - Images zoom<br>- Specifications visible<br>- Reviews shown |
| CUS-008 | As a customer, I want to add items to cart so that I can purchase later | - Quantity selection<br>- Variant selection<br>- Price shown |
| CUS-009 | As a customer, I want to save items to wishlist so that I can buy later | - Add to wishlist<br>- View wishlist<br>- Move to cart |

### Checkout & Payment

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| CUS-010 | As a customer, I want to add delivery address so that I can receive orders | - Address form<br>- Validation<br>- Save multiple |
| CUS-011 | As a customer, I want to apply coupons so that I can save money | - Enter coupon code<br>- Discount applied<br>- Error if invalid |
| CUS-012 | As a customer, I want to pay using multiple methods so that I have flexibility | - Card payment<br>- UPI payment<br>- Wallet payment |
| CUS-013 | As a customer, I want to receive order confirmation so that I have proof | - Confirmation screen<br>- Email sent<br>- Order ID shown |

### Order Management

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| CUS-014 | As a customer, I want to track my order so that I know delivery status | - Real-time status<br>- Map tracking<br>- ETA shown |
| CUS-015 | As a customer, I want to cancel orders so that I can change my mind | - Cancel button<br>- Reason selection<br>- Refund initiated |
| CUS-016 | As a customer, I want to return items so that I can get refunds | - Return request<br>- Pickup scheduled<br>- Refund processed |
| CUS-017 | As a customer, I want to rate products so that I can share feedback | - Star rating<br>- Text review<br>- Photo upload |

---

## Vendor User Stories

### Onboarding

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| VEN-001 | As a vendor, I want to register my business so that I can sell products | - Business details form<br>- Document upload<br>- Bank details |
| VEN-002 | As a vendor, I want to track verification status so that I know approval progress | - Status visible<br>- Rejection reasons<br>- Resubmit option |
| VEN-003 | As a vendor, I want to set up my store profile so that customers know my brand | - Store name<br>- Logo upload<br>- Description |

### Product Management

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| VEN-004 | As a vendor, I want to add products so that I can sell them | - Product form<br>- Image upload<br>- Pricing set |
| VEN-005 | As a vendor, I want to manage variants so that I can offer options | - Size variants<br>- Color variants<br>- Pricing per variant |
| VEN-006 | As a vendor, I want to bulk upload products so that I can save time | - CSV template<br>- Validation errors<br>- Success report |
| VEN-007 | As a vendor, I want to update inventory so that stock is accurate | - Stock count update<br>- Low stock alert<br>- Out of stock flag |

### Order Fulfillment

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| VEN-008 | As a vendor, I want to view orders so that I can fulfill them | - Order list<br>- Filter by status<br>- Order details |
| VEN-009 | As a vendor, I want to accept/reject orders so that I can manage capacity | - Accept button<br>- Reject with reason<br>- Auto-notify customer |
| VEN-010 | As a vendor, I want to mark orders packed so that pickup can be arranged | - Pack button<br>- Generate label<br>- Schedule pickup |
| VEN-011 | As a vendor, I want to handle returns so that I can process them | - Return requests list<br>- Accept/reject<br>- Refund trigger |

### Financials

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| VEN-012 | As a vendor, I want to view earnings so that I can track revenue | - Daily/monthly view<br>- Order-wise breakdown<br>- Commission deducted |
| VEN-013 | As a vendor, I want to request payouts so that I receive payments | - Payout request<br>- Bank transfer<br>- Transaction history |
| VEN-014 | As a vendor, I want to view analytics so that I can improve sales | - Sales charts<br>- Top products<br>- Customer insights |

---

## Admin User Stories

### Dashboard & Analytics

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ADM-001 | As an admin, I want to view dashboard so that I can monitor platform | - Key metrics<br>- Real-time updates<br>- Trend charts |
| ADM-002 | As an admin, I want to generate reports so that I can analyze data | - Custom date range<br>- Export to CSV<br>- Scheduled reports |
| ADM-003 | As an admin, I want to view live orders so that I can monitor activity | - Order feed<br>- Geographic view<br>- Issue alerts |

### User Management

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ADM-004 | As an admin, I want to manage customers so that I can support them | - Customer list<br>- Account status<br>- Order history |
| ADM-005 | As an admin, I want to approve vendors so that quality is maintained | - Pending list<br>- Document review<br>- Approve/reject |
| ADM-006 | As an admin, I want to manage admin roles so that access is controlled | - Role creation<br>- Permission matrix<br>- Assign to users |

### Catalog Management

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ADM-007 | As an admin, I want to manage categories so that products are organized | - Add category<br>- Edit hierarchy<br>- Set attributes |
| ADM-008 | As an admin, I want to moderate products so that quality is ensured | - Product queue<br>- Approve/reject<br>- Flag violations |
| ADM-009 | As an admin, I want to manage promotions so that sales increase | - Create banners<br>- Set coupons<br>- Schedule offers |

### Logistics Management

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ADM-010 | As an admin, I want to manage delivery zones so that coverage is defined | - Zone mapping<br>- Pincode assignment<br>- Rate configuration |
| ADM-011 | As an admin, I want to monitor line haul so that transit is tracked | - Vehicle tracking<br>- Route status<br>- Delay alerts |
| ADM-012 | As an admin, I want to manage branches so that last-mile is efficient | - Branch list<br>- Agent assignment<br>- Performance metrics |

---

## Delivery Agent User Stories

### Daily Operations

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| DEL-001 | As a delivery agent, I want to view assigned deliveries so that I know my tasks | - Delivery list<br>- Route map<br>- Priority order |
| DEL-002 | As a delivery agent, I want to update delivery status so that tracking works | - Status buttons<br>- Location capture<br>- Timestamp logged |
| DEL-003 | As a delivery agent, I want to capture POD so that delivery is confirmed | - Customer OTP<br>- Photo capture<br>- Signature option |
| DEL-004 | As a delivery agent, I want to report issues so that exceptions are handled | - Cannot deliver reason<br>- Reschedule option<br>- Return to branch |

### Performance

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| DEL-005 | As a delivery agent, I want to view my performance so that I can improve | - Completed count<br>- Success rate<br>- Earnings |
| DEL-006 | As a delivery agent, I want to manage my availability so that I control workload | - Toggle availability<br>- Set working hours<br>- Leave request |

---

## Hub Operator User Stories

### Hub Operations

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| HUB-001 | As hub operator, I want to receive inbound shipments so that I can process them | - Scan manifest<br>- Count verification<br>- Exception logging |
| HUB-002 | As hub operator, I want to sort shipments so that they're routed correctly | - Scan package<br>- Show destination bin<br>- Confirm sorted |
| HUB-003 | As hub operator, I want to dispatch outbound so that transit continues | - Load manifest<br>- Vehicle assignment<br>- Dispatch confirmation |
| HUB-004 | As hub operator, I want to handle exceptions so that issues are resolved | - Exception list<br>- Action buttons<br>- Resolution notes |
