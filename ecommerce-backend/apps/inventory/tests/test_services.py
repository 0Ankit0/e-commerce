from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from apps.catalog.models import Product, ProductVariant, Category
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.stock_control import reserve_stock, release_stock

User = get_user_model()

class InventoryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='vendor@example.com', password='password123')
        self.vendor = Vendor.objects.create(user=self.user, business_name='Acme Corp')
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(vendor=self.vendor, category=self.category, name='Test Product')
        self.variant = ProductVariant.objects.create(product=self.product, sku='TEST', name='Test', mrp=100, selling_price=90)
        self.warehouse = Warehouse.objects.create(vendor=self.vendor, name='Main')
        self.inventory = Inventory.objects.create(variant=self.variant, warehouse=self.warehouse, quantity=100)

    def test_reserve_stock_success(self):
        success = reserve_stock(self.variant, 5)
        self.assertTrue(success)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)
        self.assertEqual(self.inventory.reserved_qty, 5)

    def test_reserve_stock_fail_insufficient(self):
        success = reserve_stock(self.variant, 101)
        self.assertFalse(success)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 100) # Unchanged

    def test_release_stock(self):
        reserve_stock(self.variant, 10) # 90 avail, 10 reserved
        self.inventory.refresh_from_db()
        
        # Test Release
        release_stock(self.variant, 5)
        self.inventory.refresh_from_db()
        
        # Expectation depends on implementation.
        # If Release puts it back to sellable:
        self.assertEqual(self.inventory.quantity, 95) 
        self.assertEqual(self.inventory.reserved_qty, 5)
