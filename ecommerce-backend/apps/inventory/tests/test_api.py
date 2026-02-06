from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from apps.catalog.models import Product, ProductVariant, Category
from apps.inventory.models import Inventory, Warehouse

User = get_user_model()

class InventoryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='v@example.com', password='p')
        self.vendor = Vendor.objects.create(user=self.user, business_name='V')
        self.cat = Category.objects.create(name='C', slug='c')
        self.prod = Product.objects.create(vendor=self.vendor, category=self.cat, name='P')
        self.var = ProductVariant.objects.create(product=self.prod, sku='S', mrp=10, selling_price=10)
        self.wh = Warehouse.objects.create(vendor=self.vendor, name='W')
        self.inv = Inventory.objects.create(variant=self.var, warehouse=self.wh, quantity=100)
        
        self.client.force_authenticate(user=self.user)

    def test_update_inventory_stock(self):
        url = f'/api/inventory/inventory/{self.inv.id}/'
        data = {'quantity': 150}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, 150)

    def test_create_warehouse(self):
        data = {'name': 'New Warehouse', 'address': '123 St', 'vendor': self.vendor.id}
        response = self.client.post('/api/inventory/warehouses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
