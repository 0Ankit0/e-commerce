from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

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
