import uuid

def process_payment(amount: float, currency: str = 'USD', source: str = None) -> dict:
    """
    Mock payment processing (mimics Stripe/PayPal).
    """
    # Simulate success
    # In real world, we would use 'source' (token) to charge via API
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "status": "COMPLETED",
        "amount": amount,
        "currency": currency,
        "provider_response": {"code": 200, "message": "Charge successful"}
    }

def process_refund(payment_id: str) -> dict:
    """Mock refund logic."""
    refund_id = f"re_{uuid.uuid4().hex[:12]}"
    return {
        "success": True,
        "refund_id": refund_id,
        "original_payment_id": payment_id,
        "status": "REFUNDED"
    }
