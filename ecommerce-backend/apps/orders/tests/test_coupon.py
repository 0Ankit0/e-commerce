from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.orders.models import Coupon, Order


class CouponModelTest(TestCase):
    def setUp(self):
        self.coupon = Coupon.objects.create(
            code="TEST10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=5),
            quota=100,
        )

    def test_coupon_validity(self):
        self.assertTrue(self.coupon.is_valid())

    def test_coupon_expired(self):
        self.coupon.end_date = timezone.now() - timedelta(days=1)
        self.coupon.save()
        self.assertFalse(self.coupon.is_valid())

    def test_coupon_usage_limit(self):
        self.coupon.usage_limit = 1
        self.coupon.usage_count = 1
        self.coupon.save()
        self.assertFalse(self.coupon.is_valid())

    def test_apply_coupon_to_order(self):
        # Need user and address for order
        from apps.users.models import Address, User

        user = User.objects.create_user(email="order@test.com", password="password")
        address = Address.objects.create(
            user=user, name="Home", line1="123 St", city="City", state="State", pincode="123456", country="Country"
        )

        order = Order.objects.create(
            order_number="ORD-TEST-001",
            user=user,
            address=address,
            payment_method=Order.PaymentMethodChoices.CARD,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )

        order.coupon = self.coupon
        order.coupon_code = self.coupon.code
        # calculate discount
        discount = (order.subtotal * self.coupon.discount_value) / 100
        order.coupon_discount = discount
        order.total = order.subtotal - discount + order.tax + order.shipping_charge
        order.save()

        self.assertEqual(order.coupon, self.coupon)
        self.assertEqual(order.coupon_discount, Decimal("10.00"))
        self.assertEqual(order.total, Decimal("90.00"))
