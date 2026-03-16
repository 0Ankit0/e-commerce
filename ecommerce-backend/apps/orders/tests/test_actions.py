from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Cart, CartItem, Coupon, Order
from apps.users.models import Address
from apps.vendors.models import Vendor

User = get_user_model()


class OrderCartActionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="customer@example.com", password="password123")
        self.other_user = User.objects.create_user(email="other@example.com", password="password123")
        self.vendor_user = User.objects.create_user(email="vendor@example.com", password="password123")
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name="Acme Corp",
            display_name="Acme",
        )
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name="Phone",
            slug="phone",
            status=Product.Status.ACTIVE,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="PHONE-001",
            name="Phone 128GB",
            selling_price=Decimal("100.00"),
            mrp=Decimal("120.00"),
        )

        self.address = Address.objects.create(
            user=self.user,
            name="Home",
            phone="9999999999",
            line1="123 Street",
            city="Metropolis",
            state="State",
            pincode="123456",
            country="Country",
        )

        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            variant=self.variant,
            quantity=2,
            price_at_add=Decimal("100.00"),
        )

        self.order = Order.objects.create(
            order_number="ORD-1001",
            user=self.user,
            address=self.address,
            status=Order.Status.PENDING,
            payment_method=Order.PaymentMethodChoices.CARD,
            subtotal=Decimal("200.00"),
            discount=Decimal("0.00"),
            shipping_charge=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=Decimal("200.00"),
        )

        self.client.force_authenticate(user=self.user)

    def test_clear_cart_action(self):
        response = self.client.post(f"/api/orders/carts/{self.cart.id}/clear-cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["items_removed"], 1)
        self.assertFalse(self.cart.items.exists())

    def test_apply_coupon_action(self):
        coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            min_order_value=Decimal("100.00"),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        response = self.client.post(
            f"/api/orders/carts/{self.cart.id}/apply-coupon/",
            {"code": coupon.code},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["coupon"], "SAVE10")
        self.assertEqual(response.data["discount"], "20.0000")
        self.assertEqual(response.data["total"], "180.0000")

    def test_remove_coupon_action(self):
        response = self.client.post(f"/api/orders/carts/{self.cart.id}/remove-coupon/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "removed")

    def test_cancel_order_action_updates_state(self):
        response = self.client.post(f"/api/orders/orders/{self.order.id}/cancel/", {"reason": "changed mind"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_cancel_order_action_rejects_invalid_transition(self):
        self.order.status = Order.Status.DELIVERED
        self.order.save(update_fields=["status"])

        response = self.client.post(f"/api/orders/orders/{self.order.id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be cancelled", response.data["error"])

    def test_track_order_action(self):
        self.order.status = Order.Status.SHIPPED
        self.order.save(update_fields=["status"])

        response = self.client.get(f"/api/orders/orders/{self.order.id}/track/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Order.Status.SHIPPED)
        self.assertEqual(response.data["phase"], "Shipped")

    def test_request_return_action_updates_state(self):
        self.order.status = Order.Status.DELIVERED
        self.order.save(update_fields=["status"])

        response = self.client.post(
            f"/api/orders/orders/{self.order.id}/request-return/",
            {"reason": "defective"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.RETURN_REQUESTED)

    def test_request_return_action_rejects_invalid_transition(self):
        response = self.client.post(f"/api/orders/orders/{self.order.id}/request-return/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Return cannot be requested", response.data["error"])

    def test_invoice_action(self):
        response = self.client.get(f"/api/orders/orders/{self.order.id}/invoice/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoice_number"], f"INV-{self.order.order_number}")
        self.assertEqual(response.data["order_number"], self.order.order_number)

    def test_actions_require_authentication(self):
        self.client.force_authenticate(user=None)

        cart_clear = self.client.post(f"/api/orders/carts/{self.cart.id}/clear-cart/")
        cart_apply = self.client.post(f"/api/orders/carts/{self.cart.id}/apply-coupon/", {"code": "SAVE10"}, format="json")
        cart_remove = self.client.post(f"/api/orders/carts/{self.cart.id}/remove-coupon/")
        cancel = self.client.post(f"/api/orders/orders/{self.order.id}/cancel/")
        track = self.client.get(f"/api/orders/orders/{self.order.id}/track/")
        request_return = self.client.post(f"/api/orders/orders/{self.order.id}/request-return/")
        invoice = self.client.get(f"/api/orders/orders/{self.order.id}/invoice/")

        self.assertEqual(cart_clear.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(cart_apply.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(cart_remove.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(cancel.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(track.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(request_return.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(invoice.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_actions_are_scoped_to_order_owner(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(f"/api/orders/orders/{self.order.id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
