from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="password123")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="password123")
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_create_user_invalid_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="password123")

    def test_string_representation(self):
        user = User.objects.create_user(email="test@example.com", password="password123")
        self.assertEqual(str(user), "test@example.com")

    def test_user_type_defaults(self):
        user = User.objects.create_user(email="customer@example.com", password="password123")
        self.assertEqual(user.user_type, User.UserType.CUSTOMER)
        self.assertEqual(user.status, User.Status.ACTIVE)

    def test_create_vendor_user(self):
        user = User.objects.create_user(email="vendor@example.com", password="password123")
        user.user_type = User.UserType.VENDOR
        user.save()
        self.assertEqual(user.user_type, User.UserType.VENDOR)

    def test_phone_field(self):
        user = User.objects.create_user(email="phone@example.com", password="password123")
        user.phone = "+1234567890"
        user.save()
        self.assertEqual(user.phone, "+1234567890")
