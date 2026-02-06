import hashid_field
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, PermissionsMixin
from django.db import models

from apps.multitenancy.models import TenantMembership
from common.acl.helpers import CommonGroups


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")

        normalized_email = self.normalize_email(email)
        user = self.model(
            email=normalized_email,
        )
        user.set_password(password)
        user_group = Group.objects.get(name=CommonGroups.User)
        user.save(using=self._db)

        user.groups.add(user_group)

        # Import here to avoid circular dependency
        from .user_profile import UserProfile

        UserProfile.objects.create(user=user)

        TenantMembership.objects.associate_invitations_with_user(normalized_email, user)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(
            email,
            password=password,
        )
        user.is_superuser = True
        user.save(using=self._db)

        return user

    def filter_admins(self):
        return self.filter(groups__name=CommonGroups.Admin)


class User(AbstractBaseUser, PermissionsMixin):
    id = hashid_field.HashidAutoField(primary_key=True)
    created = models.DateTimeField(editable=False, auto_now_add=True)
    email = models.EmailField(
        db_collation="case_insensitive",
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    is_confirmed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    otp_enabled = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)
    otp_base32 = models.CharField(max_length=255, blank=True, default="")
    otp_auth_url = models.CharField(max_length=255, blank=True, default="")

    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self) -> str:
        return self.email

    @property
    def is_staff(self):
        return self.is_superuser

    def has_group(self, name):
        return self.groups.filter(name=name).exists()
