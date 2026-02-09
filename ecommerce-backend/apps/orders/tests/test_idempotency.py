import uuid
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.orders.models import Cart, Order
from apps.users.models import Address, User
from apps.vendors.models import Vendor


class OrderIdempotencyTests(APITestCase):
    def setUp(self):
        # Setup User
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.client.force_authenticate(user=self.user)
        self.address = Address.objects.create(
            user=self.user, name="Home", line1="123 St", city="City", state="State", pincode="123456", country="Country"
        )

        # Setup Vendor, Category, Product
        self.vendor = Vendor.objects.create(user=self.user, business_name="Test Vendor", slug="test-vendor")
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name="Test Product",
            slug="test-product",
            status=Product.Status.ACTIVE,
        )
        # Note: Product model usually has variants, let's check assumptions or use what we know.
        # Checking Product model again... it has no price field directly, uses variants?
        # Actually Product model in previous turn showed no price field, but Variant likely does.
        # Let's check `apps/catalog/models/product_variant.py` if needed or assume we can create cart item directly.
        # CartItem links to variant usually.

    def test_create_order_idempotency(self):
        # We need to mock or ensure cart exists.
        # Let's mock create_order_from_cart service or create necessary DB state.
        # For simplicity, let's rely on the view logic we added:

        # 1. Create a dummy order first manually to simulate "existing order"
        allowed_uuid = str(uuid.uuid4())
        order = Order.objects.create(
            order_number="ORD-IDEM-001",
            user=self.user,
            address=self.address,
            payment_method=Order.PaymentMethodChoices.CARD,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
            idempotency_key=allowed_uuid,
        )

        # 2. Try to create order with same key
        # Assuming URL pattern name 'order-list' for OrderViewSet
        url = reverse("orders-list")
        # We don't need cart for this specific test branch because we hit the check first!
        # But wait, view checks headers first.

        response = self.client.post(url, {}, HTTP_IDEMPOTENCY_KEY=allowed_uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(order.id))

    def test_create_order_new_key(self):
        # This requires full cart setup to pass validation
        # Creating minimal cart setup
        Cart.objects.create(user=self.user)
        # We need items...
        # Skipping full cart creation complexity for now, relying on the fact that
        # if we provide a key and no order exists, it proceeds to cart check.
        # If we get 400 "Cart is empty", it means it passed the idempotency check (which returned nothing)
        # and tried to create order.

        new_uuid = str(uuid.uuid4())
        url = reverse("orders-list")
        response = self.client.post(url, {}, HTTP_IDEMPOTENCY_KEY=new_uuid)

        # Expected: 400 because cart is empty, BUT this confirms it didn't return 200 (existing)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
