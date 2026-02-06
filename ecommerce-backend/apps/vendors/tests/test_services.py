from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.vendors.models import Vendor, VendorDocument
from apps.vendors.services.onboarding import verify_vendor

User = get_user_model()


class VendorServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="vendor@example.com", password="password123")
        self.vendor = Vendor.objects.create(user=self.user, business_name="Acme Corp")

    def test_verify_vendor_success(self):
        # Create required docs
        VendorDocument.objects.create(
            vendor=self.vendor, doc_type="gst", file=SimpleUploadedFile("gst.pdf", b"file_content")
        )
        VendorDocument.objects.create(
            vendor=self.vendor, doc_type="pan", file=SimpleUploadedFile("pan.pdf", b"file_content")
        )

        success = verify_vendor(self.vendor)
        self.assertTrue(success)
        self.vendor.refresh_from_db()
        self.assertTrue(self.vendor.is_verified)

    def test_verify_vendor_fail_missing_docs(self):
        success = verify_vendor(self.vendor)
        self.assertFalse(success)
        self.assertFalse(self.vendor.is_verified)
