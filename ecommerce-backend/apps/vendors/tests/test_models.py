from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor

User = get_user_model()

class VendorModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='vendor@example.com', password='password123')

    def test_create_vendor(self):
        vendor = Vendor.objects.create(
            user=self.user,
            business_name='Acme Corp',
            display_name='Acme',
            gstin='29ABCDE1234F1Z5',
            pan='ABCDE1234F'
        )
        self.assertEqual(vendor.business_name, 'Acme Corp')
        self.assertEqual(vendor.status, 'pending')
        self.assertTrue(vendor.slug) # Auto-generated
        self.assertEqual(vendor.slug, 'acme-corp')
