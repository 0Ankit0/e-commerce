import hashid_field
from django.db import models
from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator
from .product import Product

class ProductImage(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN,
        upload_to=UniqueFilePathGenerator("products/images")
    )
    thumbnail = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN,
        upload_to=UniqueFilePathGenerator("products/thumbnails"),
        null=True, blank=True
    )
    alt_text = models.CharField(max_length=255, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"Image for {self.product.name}"
