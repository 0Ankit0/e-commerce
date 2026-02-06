from django.utils.translation import gettext as _
from hashid_field import rest
from rest_framework import exceptions, serializers

from apps.users import models
from apps.users.services.users import get_role_names

UPLOADED_AVATAR_SIZE_LIMIT = 1 * 1024 * 1024


class UserProfileSerializer(serializers.ModelSerializer):
    id = rest.HashidSerializerCharField(source_field="users.User.id", source="user.id", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    roles = serializers.SerializerMethodField()
    avatar = serializers.FileField(required=False)

    class Meta:
        model = models.UserProfile
        fields = ("id", "first_name", "last_name", "email", "roles", "avatar")

    @staticmethod
    def validate_avatar(avatar):
        if avatar and avatar.size > UPLOADED_AVATAR_SIZE_LIMIT:
            raise exceptions.ValidationError({"avatar": _("Too large file")}, "too_large")

        return avatar

    def get_roles(self, obj):
        return get_role_names(obj.user)

    def to_representation(self, instance):
        self.fields["avatar"] = serializers.FileField(source="avatar.thumbnail", default="")
        return super().to_representation(instance)

    def update(self, instance, validated_data):
        avatar = validated_data.pop("avatar", None)
        if avatar:
            if not instance.avatar:
                instance.avatar = models.UserAvatar()
            instance.avatar.original = avatar
            instance.avatar.save()
        return super().update(instance, validated_data)
