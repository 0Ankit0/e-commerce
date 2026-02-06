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
