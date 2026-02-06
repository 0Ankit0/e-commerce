import hashid_field
from django.db import models
from django.utils.text import slugify
from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator

class Brand(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    logo = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN,
        upload_to=UniqueFilePathGenerator("brands/logos"),
        null=True, blank=True
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
