from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from apps.catalog.models import Product, ProductVariant, Category
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.tasks import check_low_stock_levels

User = get_user_model()

class InventoryTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='vendor@example.com', password='password123')
        self.vendor = Vendor.objects.create(user=self.user, business_name='Acme Corp')
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(vendor=self.vendor, category=self.category, name='Test Product')
        self.variant = ProductVariant.objects.create(product=self.product, sku='TEST', name='Test', mrp=100, selling_price=90)
        self.warehouse = Warehouse.objects.create(vendor=self.vendor, name='Main')
        
        # Create low stock item
        self.inventory = Inventory.objects.create(
            variant=self.variant, 
            warehouse=self.warehouse, 
            quantity=5, 
            low_stock_threshold=10
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_low_stock_alert(self):
        check_low_stock_levels.delay()
        
        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Low Stock Alert', mail.outbox[0].subject)
        self.assertIn('TEST', mail.outbox[0].body)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_alert_if_sufficient_stock(self):
        self.inventory.quantity = 20
        self.inventory.save()
        mail.outbox = [] # Clear outbox
        
        check_low_stock_levels.delay()
        self.assertEqual(len(mail.outbox), 0)
