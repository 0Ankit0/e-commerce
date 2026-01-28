# WebSocket Integration Guide

## Overview
WebSockets work alongside your REST API to provide real-time bidirectional communication.

## Connection Endpoints
- ws://localhost:8000/ws/notifications/ - User notifications
- ws://localhost:8000/ws/tenant/<tenant_id>/ - Tenant updates

## Frontend Example (JavaScript)
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/notifications/");

ws.onopen = () => {
  console.log("Connected to WebSocket");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);

  if (data.type === "order_update") {
    // Handle order update
  }
};
```

## Send from REST API
```python
from apps.websockets.utils import send_user_notification

# In your REST view
send_user_notification(
    user_id=request.user.id,
    notification_type="order_update",
    data={"order_id": order.id, "status": "shipped"}
)
```

## Message Types
- order_update - Order status changes
- payment_update - Payment notifications
- notification - General notifications
- tenant_update - Tenant changes
