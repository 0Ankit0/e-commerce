from django.db.models import QuerySet
from apps.catalog.models import Product

def get_featured_products() -> QuerySet[Product]:
    """Returns a queryset of featured products."""
    return Product.objects.filter(is_featured=True, status='published')

from django.core.exceptions import ValidationError

def publish_product(product: Product) -> None:
    """
    Publishes a product if it meets criteria.
    Criteria: Must have at least one variant and one image (if applicable models used).
    """
    # Validation logic
    if not product.variants.exists():
        raise ValidationError(f"Cannot publish product {product.name}: No variants found.")
        
    # Check for price consistency via variants
    if not product.variants.filter(selling_price__gt=0).exists():
        raise ValidationError(f"Cannot publish product {product.name}: No valid price set on variants.")

    product.status = 'published'
    product.save(update_fields=['status'])
