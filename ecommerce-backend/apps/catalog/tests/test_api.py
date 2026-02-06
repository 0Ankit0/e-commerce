from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.vendors.models import Vendor

User = get_user_model()


class CatalogAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="p")
        self.vendor_user = User.objects.create_user(email="vendor@example.com", password="p")
        self.vendor = Vendor.objects.create(user=self.vendor_user, business_name="Vendor Inc")
        self.category = Category.objects.create(name="Gadgets", slug="gadgets")

        # Public data
        self.p1 = Product.objects.create(
            vendor=self.vendor, category=self.category, name="iPhone 13", slug="iphone-13", status="published"
        )
        self.p2 = Product.objects.create(
            vendor=self.vendor, category=self.category, name="Galaxy S21", slug="galaxy-s21", status="published"
        )

    def test_public_read_access(self):
        response = self.client.get("/api/catalog/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", response.data)), 2)

    def test_search_filter(self):
        # Search for 'iPhone'
        response = self.client.get("/api/catalog/products/?search=iPhone")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "iPhone 13")

    def test_create_permission_auth_required(self):
        # Anon try create -> 401
        data = {"name": "New", "category": self.category.id}
        response = self.client.post("/api/catalog/products/", data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Auth try create -> 201 (assuming generic create allows it, though logic might require specific fields like vendor)
        self.client.force_authenticate(user=self.user)
        # Assuming serializer handles vendor assignment or we pass it
        invalid_data = {"name": "New"}  # Missing vendor/category
        response = self.client.post("/api/catalog/products/", invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
