from datetime import timedelta, datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
import pyotp
import qrcode
from io import BytesIO
import base64
from src.apps.core.config import settings
from src.apps.core import security
from src.apps.core.security import TokenType
from src.apps.core.cookies import auth_cookie_options
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.models.login_attempt import LoginAttempt
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import VerifyOTPRequest, DisableOTPRequest, StepUpOTPRequest
from src.apps.core.cache import RedisCache
from src.apps.iam.utils.ip_access import revoke_tokens_for_ip, get_client_ip
from src.apps.iam.utils.hashid import encode_id
from src.apps.iam.security import PrivilegedAction, issue_step_up_token
from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import AuthEvents
from src.apps.observability.models import ObservabilityLogEntry
from src.apps.observability.service import (
    create_log_entry,
    record_failed_login_event,
    record_privileged_action_audit,
    record_successful_login_event,
    record_token_event,
)

router = APIRouter()


async def _record_admin_otp_audit(
    *,
    db: AsyncSession,
    user: User,
    action: str,
) -> None:
    if not user.is_superuser:
        return
    await create_log_entry(
        db,
        level="INFO",
        logger_name="auth.otp",
        source="auth",
        message=f"Admin OTP {action}",
        event_code=f"auth.admin_otp.{action}",
        user_id=user.id,
        metadata={
            "otp_enabled": user.otp_enabled,
            "otp_verified": user.otp_verified,
            "username": user.username,
        },
    )


@router.post("/otp/enable/")
async def enable_otp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Enable 2FA/OTP for the user account
    """
    try:
        if current_user.otp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP is already enabled"
            )
        
        # Generate OTP secret
        otp_base32 = pyotp.random_base32()
        otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
            name=current_user.email,
            issuer_name=settings.PROJECT_NAME
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to pillow image
        pill_img = img.get_image()

        # Convert to base64
        buffered = BytesIO()
        pill_img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Save OTP settings (but don't enable yet, wait for verification)
        current_user.otp_base32 = otp_base32
        current_user.otp_auth_url = otp_auth_url
        current_user.otp_verified = False
        await _record_admin_otp_audit(db=db, user=current_user, action="setup_started")
        await db.commit()
        
        return {
            "otp_base32": otp_base32,
            "otp_auth_url": otp_auth_url,
            "qr_code": f"data:image/png;base64,{qr_code_base64}"
        }
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred enabling OTP"
        )


@router.post("/otp/verify/")
async def verify_otp(
    otp_data: VerifyOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> dict[str, str]:
    """
    Verify and activate OTP for the user
    """
    try:
        if not current_user.otp_base32:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP not set up. Please enable OTP first"
            )
        
        totp = pyotp.TOTP(current_user.otp_base32)
        if not totp.verify(otp_data.otp_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )
        
        current_user.otp_enabled = True
        current_user.otp_verified = True
        await _record_admin_otp_audit(db=db, user=current_user, action="verified")
        await db.commit()
        
        # Invalidate user cache
        await RedisCache.delete(f"user:profile:{current_user.id}")

        await analytics.capture(str(current_user.id), AuthEvents.OTP_ENABLED)

        return {"message": "OTP verified and enabled successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred verifying OTP"
        )


@router.post("/otp/disable/")
async def disable_otp(
    otp_data: DisableOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> dict[str, str]:
    """
    Disable 2FA/OTP for the user account
    """
    try:
        if not current_user.otp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP is not enabled"
            )
        
        
        # Verify password before disabling
        if not security.verify_password(otp_data.password, current_user.hashed_password): # type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )
        
        current_user.otp_enabled = False
        current_user.otp_verified = False
        current_user.otp_base32 = ""
        current_user.otp_auth_url = ""
        await _record_admin_otp_audit(db=db, user=current_user, action="disabled")
        await db.commit()
        
        # Invalidate user cache
        await RedisCache.delete(f"user:profile:{current_user.id}")

        await analytics.capture(str(current_user.id), AuthEvents.OTP_DISABLED)

        return {"message": "OTP disabled successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred disabling OTP"
        )


@router.post("/otp/validate/")
async def validate_otp_login(
    otp_data: VerifyOTPRequest,
    request: Request,
    response: Response,
    set_cookie: bool = False,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> Token | dict[str, Any]:
    """
    Validate OTP during login process (called after username/password validation).
    Pass set_cookie=true to receive the access token via HttpOnly cookie instead of JSON.
    """
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    user = None

    try:
        # Get user from temporary session or token
        # temp_token = request.headers.get("X-Temp-Auth-Token")
        temp_token = otp_data.temp_token
        if not temp_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Temporary authentication token required"
            )
        
        try:
            payload = security.verify_token(temp_token, token_type=TokenType.TEMP_AUTH)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid temporary token"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid temporary token"
            )
        
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid temporary token"
            )

        if settings.MAX_LOGIN_ATTEMPTS > 0 and settings.ACCOUNT_LOCKOUT_DURATION_MINUTES > 0:
            window_start = datetime.now() - timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
            result = await db.execute(
                select(LoginAttempt)
                .where(
                    LoginAttempt.user_id == user.id,
                    LoginAttempt.success == False,
                    LoginAttempt.timestamp >= window_start,
                )
                .order_by(LoginAttempt.timestamp.desc())
            )
            failures = result.scalars().all()
            if len(failures) >= settings.MAX_LOGIN_ATTEMPTS:
                last_attempt = failures[0]
                lockout_expires = last_attempt.timestamp + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
                remaining_seconds = int((lockout_expires - datetime.now()).total_seconds())
                if remaining_seconds > 0:
                    remaining_minutes = (remaining_seconds + 59) // 60
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many login attempts. Try again in {remaining_minutes} minutes."
                    )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.otp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP not enabled for this account"
            )
        
        totp = pyotp.TOTP(user.otp_base32)
        if not totp.verify(otp_data.otp_code):
            login_attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=user.username,
                user_agent=user_agent,
                success=False,
                failure_reason="Invalid OTP code"
            )
            db.add(login_attempt)
            await db.commit()
            await record_failed_login_event(
                db,
                username=user.username,
                ip_address=ip_address,
                failure_reason="Invalid OTP code",
                request=request,
                subject_user_id=user.id,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )
        
        # Successful OTP validation - log successful login
        login_attempt = LoginAttempt(
            user_id=user.id,
            ip_address=ip_address,
            attempted_username=user.username,
            user_agent=user_agent,
            success=True,
            failure_reason=""
        )
        db.add(login_attempt)
        
        # Generate actual access tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        refresh_token = security.create_refresh_token(user.id)
        
        # Decode tokens to get JTI
        access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])

        # Revoke any existing active tokens for this user+IP before issuing new ones
        await revoke_tokens_for_ip(db, user.id, ip_address)

        # Track access token
        access_token_tracking = TokenTracking(
            user_id=user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)
        )
        db.add(access_token_tracking)
        
        # Track refresh token
        refresh_token_tracking = TokenTracking(
            user_id=user.id,
            token_jti=refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        )
        db.add(refresh_token_tracking)
        await db.commit()
        await record_successful_login_event(
            db,
            user_id=user.id,
            ip_address=ip_address,
            request=request,
            method="otp",
        )
        await record_token_event(
            db,
            user_id=user.id,
            ip_address=ip_address,
            action="issued",
            request=request,
            metadata={"issued_tokens": 2, "auth_method": "otp"},
        )
        await db.commit()

        await analytics.capture(
            str(user.id),
            AuthEvents.OTP_VALIDATED,
            {"ip_address": ip_address, "user_agent": user_agent},
        )

        if set_cookie:
            response.set_cookie(
                key=settings.ACCESS_TOKEN_COOKIE,
                value=access_token,
                **auth_cookie_options(max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
            )
            return {"message": "OTP validated successfully"}
        
        return Token(
            access=access_token,
            refresh=refresh_token,
            token_type=TokenType.BEARER.value
        )
    except HTTPException:
        raise
    except Exception as ex:
        if user:
            login_attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=user.username,
                user_agent=user_agent,
                success=False,
                failure_reason=f"Server error during OTP validation: {str(ex)}"
            )
            db.add(login_attempt)
            await db.commit()
            await record_failed_login_event(
                db,
                username=user.username,
                ip_address=ip_address,
                failure_reason=f"Server error during OTP validation: {str(ex)}",
                request=request,
                subject_user_id=user.id,
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during OTP validation"
        )


@router.post("/otp/step-up/verify")
async def verify_otp_step_up(
    payload: StepUpOTPRequest,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        action = PrivilegedAction(payload.action)
    except ValueError:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=payload.action,
            outcome="failure",
            request=request,
            metadata={"reason": "invalid_action"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported privileged action")

    if not current_user.otp_enabled or not current_user.otp_verified:
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="failure",
            request=request,
            metadata={"reason": "otp_not_enabled"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OTP must be enabled for this account")

    totp = pyotp.TOTP(current_user.otp_base32)
    if not totp.verify(payload.otp_code):
        await record_privileged_action_audit(
            db,
            actor_user_id=current_user.id,
            action=action.value,
            outcome="failure",
            request=request,
            metadata={"reason": "invalid_otp"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")

    token_payload = await issue_step_up_token(user_id=current_user.id, action=action)
    await record_privileged_action_audit(
        db,
        actor_user_id=current_user.id,
        action=action.value,
        outcome="success",
        request=request,
        metadata={"expires_at": token_payload["expires_at"]},
    )
    await db.commit()
    return token_payload


@router.get("/admin/security/admin-otp-status")
async def list_admin_otp_status(
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    await create_log_entry(
        db,
        level="INFO",
        logger_name="auth.otp",
        source="admin",
        message="Admin OTP readiness report viewed",
        event_code="auth.admin_otp.status_viewed",
        user_id=current_user.id,
        request=request,
        metadata={"viewer": current_user.username},
    )
    await db.commit()
    admin_users = (
        await db.execute(select(User).where(User.is_superuser == True).order_by(User.username.asc()))  # noqa: E712
    ).scalars().all()
    items: list[dict[str, Any]] = []
    for admin_user in admin_users:
        latest_audit = (
            await db.execute(
                select(ObservabilityLogEntry)
                .where(
                    ObservabilityLogEntry.user_id == admin_user.id,
                    ObservabilityLogEntry.event_code.like("auth.admin_otp.%"),
                )
                .order_by(ObservabilityLogEntry.timestamp.desc())
            )
        ).scalars().first()
        if admin_user.otp_enabled and admin_user.otp_verified:
            last_verified_state = "verified"
        elif admin_user.otp_base32:
            last_verified_state = "pending_verification"
        else:
            last_verified_state = "not_enabled"
        items.append(
            {
                "user_id": encode_id(admin_user.id or 0),
                "username": admin_user.username,
                "email": admin_user.email,
                "otp_enabled": admin_user.otp_enabled,
                "otp_verified": admin_user.otp_verified,
                "last_verified_state": last_verified_state,
                "last_otp_event_code": latest_audit.event_code if latest_audit else None,
                "last_otp_event_at": latest_audit.timestamp.isoformat() if latest_audit else None,
            }
        )
    return {"items": items, "total": len(items)}
