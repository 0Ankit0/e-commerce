"""Social OAuth2 login endpoints — browser OAuth plus native Google token exchange."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from jose import jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode

from src.apps.core import security
from src.apps.core.config import OAUTH_PROVIDERS, settings
from src.apps.core.cookies import auth_cookie_options
from src.apps.core.http import default_timeout, retry_async
from src.apps.core.security import TokenType
from src.apps.iam.api.deps import get_db
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token import Token
from src.apps.iam.utils.ip_access import revoke_tokens_for_ip, get_client_ip
from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import AuthEvents
from src.apps.observability.service import record_successful_login_event, record_token_event
from src.apps.iam.utils.social import (
    extract_user_info,
    find_or_create_social_user,
    get_callback_url,
    get_provider_credentials,
)

router = APIRouter()
APPLE_AUDIENCE = "https://appleid.apple.com"
APPLE_CLIENT_SECRET_LIFETIME_SECONDS = 60 * 60 * 24 * 180

def _provider_enabled_map() -> dict[str, bool]:
    return {
        "google": settings.GOOGLE_ENABLED,
        "github": settings.GITHUB_ENABLED,
        "facebook": settings.FACEBOOK_ENABLED,
        "apple": settings.APPLE_ENABLED,
    }


class NativeGoogleLoginRequest(BaseModel):
    id_token: str


def _normalize_apple_private_key() -> str:
    raw_key = settings.APPLE_PRIVATE_KEY.get_secret_value()
    normalized = raw_key.replace("\\n", "\n").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Apple Sign In is enabled but the private key is not configured.",
        )
    return normalized


def _build_apple_client_secret() -> str:
    if not settings.APPLE_CLIENT_ID or not settings.APPLE_TEAM_ID or not settings.APPLE_KEY_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Apple Sign In is enabled but required configuration is missing.",
        )

    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "iss": settings.APPLE_TEAM_ID,
        "iat": now,
        "exp": now + APPLE_CLIENT_SECRET_LIFETIME_SECONDS,
        "aud": APPLE_AUDIENCE,
        "sub": settings.APPLE_CLIENT_ID,
    }
    return jwt.encode(
        payload,
        _normalize_apple_private_key(),
        algorithm="ES256",
        headers={"kid": settings.APPLE_KEY_ID},
    )


def _resolve_provider_credentials(provider: str) -> tuple[str, str]:
    client_id, client_secret = get_provider_credentials(provider)
    if provider == "apple":
        return client_id, _build_apple_client_secret()
    return client_id, client_secret


def _extract_apple_user_info(id_token: str, client_id: str) -> dict[str, Any]:
    try:
        claims = jwt.get_unverified_claims(id_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apple Sign In did not return a valid ID token.",
        ) from exc

    if claims.get("iss") != APPLE_AUDIENCE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple Sign In issuer could not be verified.",
        )

    audience = claims.get("aud")
    if audience != client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple Sign In audience could not be verified.",
        )

    if str(claims.get("email_verified", "true")).lower() == "false":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple Sign In did not return a verified email address.",
        )

    return {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name"),
    }


async def _issue_app_tokens_for_social_user(
    *,
    user,
    provider: str,
    request: Request,
    db: AsyncSession,
    analytics: AnalyticsService,
) -> Token:
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    refresh_token = security.create_refresh_token(user.id)

    access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
    refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])

    await revoke_tokens_for_ip(db, user.id, ip_address)

    db.add(TokenTracking(
        user_id=user.id,
        token_jti=access_payload["jti"],
        token_type=TokenType.ACCESS,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc),
    ))
    db.add(TokenTracking(
        user_id=user.id,
        token_jti=refresh_payload["jti"],
        token_type=TokenType.REFRESH,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
    ))
    await db.commit()
    await record_successful_login_event(
        db,
        user_id=user.id,
        ip_address=ip_address,
        request=request,
        method=f"social:{provider}",
    )
    await record_token_event(
        db,
        user_id=user.id,
        ip_address=ip_address,
        action="issued",
        request=request,
        metadata={"issued_tokens": 2, "auth_method": f"social:{provider}"},
    )
    await db.commit()

    await analytics.capture(
        str(user.id),
        AuthEvents.LOGGED_IN_SOCIAL,
        {"provider": provider, "ip_address": ip_address, "user_agent": user_agent},
    )

    return Token(
        access=access_token,
        refresh=refresh_token,
        token_type=TokenType.BEARER.value,
    )


def _assert_provider_enabled(provider: str) -> None:
    """Raise 400 if the provider is disabled or unknown."""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' is not supported. Supported: {list(OAUTH_PROVIDERS.keys())}",
        )
    if not _provider_enabled_map().get(provider, False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Social login with '{provider}' is not enabled.",
        )


@router.get(
    "/social/providers/",
    summary="List enabled social auth providers",
    description="Returns a list of social OAuth2 providers that are currently enabled.",
)
async def list_social_providers() -> dict:
    enabled = [p for p, on in _provider_enabled_map().items() if on]
    return {"providers": enabled}


@router.get(
    "/social/{provider}/",
    summary="Initiate social login",
    description="Redirects the browser to the OAuth2 provider's login page. Supported: google, github, facebook, apple.",
)
async def social_login(provider: str) -> RedirectResponse:
    _assert_provider_enabled(provider)
    config = OAUTH_PROVIDERS[provider]
    client_id, _ = _resolve_provider_credentials(provider)
    params: dict[str, Any] = {
        "client_id": client_id,
        "redirect_uri": get_callback_url(provider),
        "scope": config["scope"],
        "state": security.create_oauth_state(provider),
        **config.get("extra_params", {}),
    }
    return RedirectResponse(url=f"{config['authorize_url']}?{urlencode(params)}")


@router.get(
    "/social/{provider}/callback",
    summary="Handle OAuth2 callback",
    description=(
        "Exchanges the authorization code for tokens, retrieves user info, "
        "and issues JWT access/refresh tokens. Pass set_cookie=true to receive "
        "tokens via HttpOnly cookie instead of JSON."
    ),
)
async def social_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    set_cookie: bool = False,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> RedirectResponse:
    _assert_provider_enabled(provider)

    if not security.verify_oauth_state(state, provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please try again.",
        )

    config = OAUTH_PROVIDERS[provider]
    client_id, client_secret = _resolve_provider_credentials(provider)
    callback_url = get_callback_url(provider)

    async with httpx.AsyncClient() as http:
        # Exchange authorization code for provider access token
        try:
            token_resp = await retry_async(
                lambda: http.post(
                    config["token_url"],
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "redirect_uri": callback_url,
                        "grant_type": "authorization_code",
                    },
                    headers={"Accept": "application/json"},
                    timeout=default_timeout(),
                )
            )
            token_resp.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to obtain access token from {provider}",
            )

        token_payload = token_resp.json()
        if provider == "apple":
            id_token = token_payload.get("id_token")
            if not id_token:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Apple Sign In did not return an ID token.",
                )
            user_info = _extract_apple_user_info(id_token, client_id)
        else:
            provider_token: Optional[str] = token_payload.get("access_token")
            if not provider_token:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No access token returned by {provider}",
                )

            # Fetch user profile from provider
            try:
                info_resp = await retry_async(
                    lambda: http.get(
                        config["userinfo_url"],
                        headers={
                            "Authorization": f"Bearer {provider_token}",
                            "Accept": "application/json",
                            "User-Agent": "FastAPI-Template/1.0",
                        },
                        timeout=default_timeout(),
                    )
                )
                info_resp.raise_for_status()
                user_info = info_resp.json()
            except httpx.HTTPError:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch user info from {provider}",
                )

        # GitHub may keep email private — fetch it from the dedicated emails endpoint
        if provider == "github" and not user_info.get("email"):
            try:
                emails_resp = await retry_async(
                    lambda: http.get(
                        config["emails_url"],
                        headers={
                            "Authorization": f"Bearer {provider_token}",
                            "Accept": "application/json",
                            "User-Agent": "FastAPI-Template/1.0",
                        },
                        timeout=default_timeout(),
                    )
                )
                emails_resp.raise_for_status()
                primary = next(
                    (e["email"] for e in emails_resp.json() if e.get("primary") and e.get("verified")),
                    None,
                )
                if primary:
                    user_info["email"] = primary
            except Exception:
                pass

        if provider == "apple" and not user_info.get("name"):
            raw_user = request.query_params.get("user")
            if raw_user:
                try:
                    user_payload = json.loads(raw_user)
                    full_name = " ".join(
                        part
                        for part in [
                            user_payload.get("name", {}).get("firstName"),
                            user_payload.get("name", {}).get("lastName"),
                        ]
                        if part
                    ).strip()
                    if full_name:
                        user_info["name"] = full_name
                except json.JSONDecodeError:
                    pass

    social_id, email, display_name = extract_user_info(provider, user_info)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not retrieve email from {provider}. Please grant email permission and try again.",
        )

    user = await find_or_create_social_user(db, provider, social_id, email, display_name)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account has been deactivated.")

    issued_tokens = await _issue_app_tokens_for_social_user(
        user=user,
        provider=provider,
        request=request,
        db=db,
        analytics=analytics,
    )

    # Redirect the popup back to the frontend auth-callback page with tokens as
    # query params. The /auth-callback page stores the tokens and continues the flow.
    frontend_callback = f"{settings.FRONTEND_URL}/auth-callback"

    if set_cookie:
        redirect_resp = RedirectResponse(url=frontend_callback, status_code=302)
        redirect_resp.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE,
            value=issued_tokens.access,
            **auth_cookie_options(max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        )
        return redirect_resp

    return RedirectResponse(
        url=f"{frontend_callback}?access={issued_tokens.access}&refresh={issued_tokens.refresh}&provider={provider}",
        status_code=302,
    )


@router.post(
    "/social/google/native/",
    response_model=Token,
    summary="Exchange a native Google sign-in token for application JWTs",
    description=(
        "Used by native mobile clients after a device-level Google sign-in. "
        "The mobile app sends a Google ID token and receives app access/refresh tokens."
    ),
)
async def social_google_native_login(
    payload: NativeGoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> Token:
    _assert_provider_enabled("google")

    if not payload.id_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token is required.",
        )

    try:
        google_claims = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            payload.id_token,
            GoogleRequest(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired Google sign-in token.",
        ) from exc

    if google_claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sign-in issuer could not be verified.",
        )
    if google_claims.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sign-in did not return a verified email address.",
        )

    social_id, email, display_name = extract_user_info("google", google_claims)
    if not social_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sign-in did not return a verified email address.",
        )

    user = await find_or_create_social_user(db, "google", social_id, email, display_name)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has been deactivated.",
        )

    return await _issue_app_tokens_for_social_user(
        user=user,
        provider="google",
        request=request,
        db=db,
        analytics=analytics,
    )
