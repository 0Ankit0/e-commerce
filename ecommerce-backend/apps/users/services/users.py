from typing import TYPE_CHECKING

from rest_framework import serializers

if TYPE_CHECKING:
    from apps.users.models import User
else:
    from django.contrib.auth import get_user_model

    User = get_user_model()


def get_role_names(user: "User") -> list[str]:
    return [group.name for group in user.groups.all()]


def get_user_avatar_url(user: "User") -> str:
    field = serializers.FileField(default="")
    if user.profile.avatar:
        return str(field.to_representation(user.profile.avatar.thumbnail))
    return ""
