import hashid_field
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from common.models import TimestampedMixin
from common.storages import PublicS3Boto3StorageWithCDN, UniqueFilePathGenerator

class Vendor(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_profile")
    business_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    
    logo = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN, 
        upload_to=UniqueFilePathGenerator("vendors/logos"), 
        null=True, blank=True
    )
    banner = models.ImageField(
        storage=PublicS3Boto3StorageWithCDN, 
        upload_to=UniqueFilePathGenerator("vendors/banners"), 
        null=True, blank=True
    )
    
    gstin = models.CharField(max_length=50, blank=True)
    pan = models.CharField(max_length=50, blank=True)
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    product_count = models.PositiveIntegerField(default=0)
    
    COMMISSION_TIER_CHOICES = (
        ('standard', 'Standard'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    )
    commission_tier = models.CharField(max_length=20, choices=COMMISSION_TIER_CHOICES, default='standard')
    
    approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.business_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.business_name
