from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor

User = get_user_model()

class VendorAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='p')
        self.vendor_user = User.objects.create_user(email='vendor@example.com', password='p')
        self.vendor = Vendor.objects.create(user=self.vendor_user, business_name='Vendor Inc')
        self.client.force_authenticate(user=self.vendor_user)

    def test_vendor_list(self):
        response = self.client.get('/api/vendors/vendors/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should verify if user sees all vendors or just themselves depending on permission logic.
        # Assuming admin/public read or owner read. 
        # If it's a marketplace, public might see vendors.
        self.assertTrue(len(response.data.get('results', response.data)) >= 1)

    def test_vendor_update_permission(self):
        # Vendor updates own profile
        url = f'/api/vendors/vendors/{self.vendor.slug}/' # Assuming lookup is slug
        data = {'business_name': 'Vendor Updated'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.business_name, 'Vendor Updated')

    def test_create_bank_account(self):
        # Create bank account for vendor
        data = {
            'vendor': self.vendor.id,
            'account_holder_name': 'Me',
            'account_number': '1234567890',
            'bank_name': 'Bank',
            'ifsc_code': 'BANK001'
        }
        response = self.client.post('/api/vendors/bank-accounts/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
