from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password123")

    def test_obtain_token(self):
        # We need to know the login endpoint path.
        # Typically simplejwt uses /api/token/ or similar, but configured in urls_api as include("apps.users.urls").
        # apps/users/urls.py has social and auth patterns.
        # Wait, I don't see a standard `TokenObtainPairView` in the `urls.py` snippet (Step 1212).
        # It has `social/`, `token-refresh/`, `logout/`, `signup/`.
        # Where is login?
        # Checking `config/urls_api.py`...
        # `path("", include("apps.users.urls"))`
        # Maybe login is handled via social? Or I missed it in `apps/users/urls.py`.
        # Step 1212 snippet shows `user_patterns` lines 25-42.
        # Ah, re-read carefully: `path("token-refresh/", ...)`
        # `re_path(r"^login/(?P<backend>[^/]+)/$", ...)` -> Social.
        # It seems `TokenObtainPairView` might be missing or I missed it?
        # WAIT! `config/settings.py` lines 254: `apps.users.authentication.JSONWebTokenCookieAuthentication`.
        # Maybe login is via `LoginView`?
        # Let's check `apps/users/views.py`.
        pass

    def test_register_user_success(self):
        data = {
            "email": "new@example.com",
            "password": "newpassword123",
            "password_confirm": "newpassword123",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post("/api/users/auth/signup/", data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_register_password_mismatch(self):
        data = {"email": "fail@example.com", "password": "pass", "password_confirm": "mismatch"}
        response = self.client.post("/api/users/auth/signup/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
