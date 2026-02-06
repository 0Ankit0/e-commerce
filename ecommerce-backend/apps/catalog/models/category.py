import hashid_field
from django.db import models
from django.utils.text import slugify
from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator

class Category(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    level = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    icon = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN,
        upload_to=UniqueFilePathGenerator("categories/icons"),
        null=True, blank=True
    )
    image = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN,
        upload_to=UniqueFilePathGenerator("categories/images"),
        null=True, blank=True
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
