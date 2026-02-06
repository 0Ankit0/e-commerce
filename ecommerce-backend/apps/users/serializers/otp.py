from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework_simplejwt import exceptions as jwt_exceptions
from rest_framework_simplejwt import tokens as jwt_tokens
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users import models
from apps.users.services import otp as otp_services
from common.decorators import context_user_required


@context_user_required
class GenerateOTPSerializer(serializers.Serializer):
    base32 = serializers.CharField(read_only=True)
    otpauth_url = serializers.CharField(read_only=True)

    def create(self, validated_data):
        otp_base32, otp_auth_url = otp_services.generate_otp(self.context_user)
        return {"base32": otp_base32, "otpauth_url": otp_auth_url}


@context_user_required
class VerifyOTPSerializer(serializers.Serializer):
    otp_verified = serializers.BooleanField(read_only=True)
    otp_token = serializers.CharField(write_only=True)

    def create(self, validated_data):
        otp_services.verify_otp(self.context_user, validated_data.get("otp_token", ""))
        return {"otp_verified": True}


class ValidateOTPSerializer(serializers.Serializer):
    user: models.User

    otp_token = serializers.CharField(write_only=True)
    otp_auth_token = serializers.CharField(required=False, write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    default_error_messages = {
        "invalid_token": _(f"No valid token found in cookie '{settings.OTP_AUTH_TOKEN_COOKIE}'"),
    }

    def validate(self, attrs):
        request = self.context["request"]

        if not (
            raw_otp_auth_token := request.COOKIES.get(settings.OTP_AUTH_TOKEN_COOKIE) or attrs.get("otp_auth_token")
        ):
            self.fail("invalid_token")

        try:
            otp_auth_token = jwt_tokens.AccessToken(raw_otp_auth_token)
        except (jwt_exceptions.InvalidToken, jwt_exceptions.TokenError):
            self.fail("invalid_token")

        if not (user_id := otp_auth_token.get("user_id")):
            self.fail("invalid_token")

        try:
            self.user = models.User.objects.get(id=user_id)
        except models.User.DoesNotExist:
            self.fail("invalid_token")

        otp_services.validate_otp(self.user, attrs.get("otp_token", ""))

        return attrs

    def create(self, validated_data):
        refresh = RefreshToken.for_user(self.user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


@context_user_required
class DisableOTPSerializer(serializers.Serializer):
    ok = serializers.BooleanField(read_only=True)

    def create(self, validated_data):
        otp_services.disable_otp(self.context_user)
        return {"ok": True}
