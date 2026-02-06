import os
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from apps.catalog.models import Product, Category
from apps.catalog.tasks import process_bulk_upload

User = get_user_model()

class CatalogTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='vendor@example.com', password='password123')
        self.vendor = Vendor.objects.create(user=self.user, business_name='Acme Corp')
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        
        # Create temp CSV file
        self.file_path = "products.csv"
        with open(self.file_path, "w") as f:
            f.write("name,category_slug,sku,price,stock,description\n")
            f.write("iPhone 15,electronics,IP15,999,100,New iPhone\n")
            
    def tearDown(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_process_bulk_upload(self):
        result = process_bulk_upload.delay(self.file_path, self.vendor.id)
        self.assertTrue(result.successful())
        
        # Verify Product Created
        self.assertTrue(Product.objects.filter(name='iPhone 15').exists())
        product = Product.objects.get(name='iPhone 15')
        self.assertEqual(product.vendor, self.vendor)
        self.assertEqual(product.category, self.category)
        
        # Verify Variant
        self.assertTrue(product.variants.exists())
        variant = product.variants.first()
        self.assertEqual(variant.sku, 'IP15')
        self.assertEqual(variant.selling_price, 999)
        
        # Verify Inventory
        self.assertTrue(variant.inventory.exists())
        self.assertEqual(variant.inventory.first().quantity, 100)
