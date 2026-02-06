from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.vendors.models import Vendor
from apps.catalog.models import Product, ProductVariant, Category
from apps.catalog.services.product_management import publish_product

User = get_user_model()

class ProductServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='vendor@example.com', password='password123')
        self.vendor = Vendor.objects.create(user=self.user, business_name='Acme Corp')
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Test Product',
            status='draft'
        )

    def test_publish_product_success(self):
        # Create variant
        ProductVariant.objects.create(
            product=self.product,
            sku='TEST-SKU',
            name='Test Variant',
            mrp=100,
            selling_price=90
        )
        
        publish_product(self.product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'published')

    def test_publish_product_fail_no_variants(self):
        with self.assertRaises(ValidationError):
            publish_product(self.product)
            
    def test_publish_product_fail_zero_price(self):
        ProductVariant.objects.create(
            product=self.product,
            sku='TEST-SKU',
            name='Test Variant',
            mrp=100,
            selling_price=0 # Invalid
        )
        with self.assertRaises(ValidationError):
            publish_product(self.product)
