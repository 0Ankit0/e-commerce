from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from apps.orders.models import Order
from apps.orders.tasks import send_order_confirmation

User = get_user_model()


class OrderTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="customer@example.com", password="password123", first_name="John")
        self.order = Order.objects.create(user=self.user, total_amount=100)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_order_confirmation(self):
        result = send_order_confirmation.delay(self.order.id)
        self.assertTrue(result.successful())

        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"Order Confirmation - Order #{self.order.id}", mail.outbox[0].subject)
        self.assertIn("John", mail.outbox[0].body)
