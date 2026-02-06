from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.tasks import check_payment_timeout

User = get_user_model()

class PaymentTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='customer@example.com', password='p')
        self.order = Order.objects.create(user=self.user, total_amount=100)
        
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_payment_timeout(self):
        # Create stale payment
        old_time = timezone.now() - timedelta(minutes=40)
        payment = Payment.objects.create(
            order=self.order,
            amount=100,
            status='PENDING',
            payment_method='credit_card'
        )
        Payment.objects.filter(id=payment.id).update(created_at=old_time) # Force old timestamp
        
        check_payment_timeout.delay()
        
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'FAILED')

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_payment_no_timeout_recent(self):
        # Create recent payment
        payment = Payment.objects.create(
            order=self.order,
            amount=100,
            status='PENDING',
            payment_method='credit_card'
        )
        
        check_payment_timeout.delay()
        
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'PENDING')
