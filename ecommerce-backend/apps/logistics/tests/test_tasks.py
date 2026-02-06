from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.logistics.models import Shipment
from apps.logistics.tasks import poll_shipment_status
from apps.orders.models import Order

User = get_user_model()


class LogisticsTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="c@c.com", password="p")
        self.order = Order.objects.create(user=self.user, total_amount=100)
        self.shipment = Shipment.objects.create(order=self.order, tracking_number="TRK123", status="PENDING")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_poll_shipment_status(self):
        # Logic is randomized, so we just check it runs without error and potentially changes state
        result = poll_shipment_status.delay(self.shipment.id)
        self.assertTrue(result.successful())

        self.shipment.refresh_from_db()
        # Status might match PENDING or update to SHIPPED
        self.assertIn(self.shipment.status, ["PENDING", "SHIPPED", "DELIVERED"])
