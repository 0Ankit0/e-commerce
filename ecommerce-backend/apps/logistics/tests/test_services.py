from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.logistics.models import DeliveryAgent, Shipment
from apps.logistics.services.shipment_scheduling import assign_delivery_agent
from apps.orders.models import Order

User = get_user_model()


class LogisticsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="c@c.com", password="p")
        self.order = Order.objects.create(user=self.user, total_amount=100)
        self.shipment = Shipment.objects.create(order=self.order, tracking_number="TRK123")

        self.agent1 = DeliveryAgent.objects.create(name="Agent 1", is_active=True)
        self.agent2 = DeliveryAgent.objects.create(name="Agent 2", is_active=True)

    def test_assign_agent_load_balancing(self):
        # Assign agent1 to another shipment
        _ = Shipment.objects.create(
            order=self.order, tracking_number="TRK2", delivery_agent=self.agent1, status="PENDING"
        )

        # Should pick agent2 (0 shipments) over agent1 (1 shipment)
        assign_delivery_agent(self.shipment)

        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.delivery_agent, self.agent2)
