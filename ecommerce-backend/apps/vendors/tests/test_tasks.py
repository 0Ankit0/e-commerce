from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from apps.vendors.models import Vendor
from apps.vendors.tasks import send_welcome_email

User = get_user_model()


class VendorTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="vendor@example.com", password="password123")
        self.vendor = Vendor.objects.create(user=self.user, business_name="Acme Corp")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_welcome_email(self):
        result = send_welcome_email.delay(self.vendor.id)
        self.assertTrue(result.successful())

        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to E-Commerce", mail.outbox[0].subject)
