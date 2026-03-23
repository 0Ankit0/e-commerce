from unittest.mock import patch

import pytest
from httpx import Request, Response
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core import security
from src.apps.core.config import settings
from src.apps.iam.models.user import User


@pytest.mark.asyncio
async def test_native_google_login_returns_app_tokens(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GOOGLE_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "google-web-client-id")

    def fake_verify_oauth2_token(id_token: str, _request: object, audience: str) -> dict[str, object]:
        assert id_token == "native-google-id-token"
        assert audience == "google-web-client-id"
        return {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-123",
            "email": "native-google@example.com",
            "email_verified": True,
            "name": "Native Google User",
        }

    with patch(
        "src.apps.iam.api.v1.auth.social.google_id_token.verify_oauth2_token",
        side_effect=fake_verify_oauth2_token,
    ):
        response = await client.post(
            "/api/v1/auth/social/google/native/",
            json={"id_token": "native-google-id-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access"]
    assert payload["refresh"]
    assert payload["token_type"] == "bearer"

    result = await db_session.execute(
        select(User).where(User.email == "native-google@example.com")
    )
    user = result.scalars().first()
    assert user is not None
    assert user.social_provider == "google"
    assert user.social_id == "google-sub-123"
    assert user.is_confirmed is True


@pytest.mark.asyncio
async def test_native_google_login_requires_provider_enabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GOOGLE_ENABLED", False)

    response = await client.post(
        "/api/v1/auth/social/google/native/",
        json={"id_token": "native-google-id-token"},
    )

    assert response.status_code == 400
    assert "not enabled" in response.json()["detail"]


@pytest.mark.asyncio
async def test_social_provider_listing_includes_apple_when_enabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "APPLE_ENABLED", True)

    response = await client.get("/api/v1/auth/social/providers/")

    assert response.status_code == 200
    assert "apple" in response.json()["providers"]


@pytest.mark.asyncio
async def test_apple_social_callback_creates_and_logs_in_user(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "APPLE_ENABLED", True)
    monkeypatch.setattr(settings, "APPLE_CLIENT_ID", "com.example.web")
    monkeypatch.setattr(settings, "APPLE_TEAM_ID", "TEAM123")
    monkeypatch.setattr(settings, "APPLE_KEY_ID", "KEY123")
    monkeypatch.setattr(
        settings,
        "APPLE_PRIVATE_KEY",
        settings.APPLE_PRIVATE_KEY.__class__(
            "-----BEGIN PRIVATE KEY-----\\nTEST\\n-----END PRIVATE KEY-----"
        ),
    )

    async def passthrough_retry(fn):
        return await fn()

    def fake_get_unverified_claims(_token: str) -> dict[str, object]:
        return {
            "iss": "https://appleid.apple.com",
            "aud": "com.example.web",
            "sub": "apple-sub-123",
            "email": "apple-user@example.com",
            "email_verified": "true",
        }

    async def fake_post(self, url, data=None, headers=None, timeout=None):  # noqa: ANN001
        assert url == "https://appleid.apple.com/auth/token"
        assert data["client_id"] == "com.example.web"
        assert data["client_secret"] == "apple-client-secret"
        return Response(
            200,
            json={"id_token": "apple-id-token"},
            request=Request("POST", url),
        )

    state = security.create_oauth_state("apple")

    with patch("src.apps.iam.api.v1.auth.social.retry_async", side_effect=passthrough_retry), patch(
        "src.apps.iam.api.v1.auth.social._build_apple_client_secret",
        return_value="apple-client-secret",
    ), patch(
        "src.apps.iam.api.v1.auth.social.jwt.get_unverified_claims",
        side_effect=fake_get_unverified_claims,
    ), patch("httpx.AsyncClient.post", new=fake_post):
        response = await client.get(
            "/api/v1/auth/social/apple/callback",
            params={"code": "apple-code", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert "provider=apple" in response.headers["location"]

    result = await db_session.execute(select(User).where(User.email == "apple-user@example.com"))
    user = result.scalars().first()
    assert user is not None
    assert user.social_provider == "apple"
    assert user.social_id == "apple-sub-123"
    assert user.is_confirmed is True
