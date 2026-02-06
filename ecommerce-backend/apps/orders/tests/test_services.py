from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from apps.catalog.models import Product, ProductVariant, Category
from apps.orders.models import Cart, CartItem, Order
from apps.orders.services.order_processing import create_order_from_cart

User = get_user_model()

class OrderProcessingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='customer@example.com', password='password123')
        self.vendor = Vendor.objects.create(user=User.objects.create_user(email='v@v.com', password='p'), business_name='Acme')
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(vendor=self.vendor, category=self.category, name='P')
        self.variant = ProductVariant.objects.create(product=self.product, sku='SKU', name='V', mrp=100, selling_price=50)
        
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product_variant=self.variant, quantity=2)

    def test_create_order_from_cart(self):
        order = create_order_from_cart(self.cart, self.user)
        
        # Verify Order Created
        self.assertTrue(Order.objects.filter(id=order.id).exists())
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(order.total_amount, 100) # 50 * 2
        
        # Verify Items Copied
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.product_variant, self.variant)
        self.assertEqual(item.quantity, 2)
        
        # Verify Cart Cleared
        self.assertEqual(self.cart.items.count(), 0)
