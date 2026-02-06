from celery import shared_task
from apps.payments.models import Payment
from django.utils import timezone
from datetime import timedelta

@shared_task
def check_payment_timeout():
    """
    Checks for pending payments older than X minutes and marks them as failed/timeout.
    """
    timeout_threshold = timezone.now() - timedelta(minutes=30)
    pending_payments = Payment.objects.filter(status='PENDING', created_at__lt=timeout_threshold)
    
    count = 0
    for payment in pending_payments:
        payment.status = 'FAILED'
        payment.save()
        count += 1
        print(f"Marked payment {payment.id} as FAILED due to timeout.")
        
    return f"Processed {count} timed-out payments."
