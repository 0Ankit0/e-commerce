from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Review


def update_product_rating(product):
    reviews = Review.objects.filter(product=product, is_approved=True)
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"] or 0.0
    review_count = reviews.count()

    product.avg_rating = round(avg_rating, 2)
    product.review_count = review_count
    product.save(update_fields=["avg_rating", "review_count"])


@receiver(post_save, sender=Review)
def review_post_save(sender, instance, created, **kwargs):
    if instance.is_approved:
        update_product_rating(instance.product)


@receiver(post_delete, sender=Review)
def review_post_delete(sender, instance, **kwargs):
    if instance.is_approved:
        update_product_rating(instance.product)
