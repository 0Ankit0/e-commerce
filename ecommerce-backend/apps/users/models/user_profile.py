from django.db import models

from .user import User
from .user_avatar import UserAvatar


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=40, blank=True, default="")
    last_name = models.CharField(max_length=40, blank=True, default="")
    avatar = models.OneToOneField(
        UserAvatar, on_delete=models.SET_NULL, null=True, blank=True, related_name="user_profile"
    )

    def __str__(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.user.email
