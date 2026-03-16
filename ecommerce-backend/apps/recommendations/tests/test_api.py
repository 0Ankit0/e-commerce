from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.recommendations.models import RecommendationEvent
from apps.vendors.models import Vendor

User = get_user_model()


class RecommendationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="customer@example.com", password="password123")
        self.vendor_user = User.objects.create_user(email="vendor@example.com", password="password123")
        self.vendor = Vendor.objects.create(user=self.vendor_user, business_name="Acme Corp")
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.target_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name="Phone",
            status="published",
        )
        self.other_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name="Tablet",
            status="published",
        )

    def test_get_recommendations_response_shape(self):
        response = self.client.get(f"/api/v1/recommendations/?type=similar&productId={self.target_product.id}&limit=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("type", response.data)
        self.assertIn("productId", response.data)
        self.assertIn("recommendations", response.data)
        self.assertEqual(response.data["type"], "similar")
        self.assertEqual(response.data["productId"], self.target_product.id)
        self.assertEqual(len(response.data["recommendations"]), 1)

    def test_get_recommendations_schema_validation(self):
        response = self.client.get("/api/v1/recommendations/?type=unknown")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("type", response.data)

    def test_post_event_requires_authentication(self):
        payload = {"productId": self.target_product.id, "eventType": "view"}
        response = self.client.post("/api/v1/recommendations/events", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.recommendations.services.recommendation_service.process_recommendation_event.delay")
    def test_post_event_captures_telemetry(self, mock_delay):
        self.client.force_authenticate(user=self.user)

        payload = {
            "productId": self.target_product.id,
            "eventType": "click",
            "metadata": {"source": "home_page"},
        }
        response = self.client.post("/api/v1/recommendations/events", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        event = RecommendationEvent.objects.get(product=self.target_product)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.event_type, "click")
        self.assertEqual(event.metadata["source"], "home_page")
        mock_delay.assert_called_once_with(event.id)
