import hashid_field
from django.db import models
from django.utils.text import slugify
from common.models import TimestampedMixin
from apps.vendors.models import Vendor
from .category import Category
from .brand import Brand

class Product(TimestampedMixin, models.Model):
    id = hashid_field.HashidAutoField(primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deleted', 'Deleted'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    seo_data = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
