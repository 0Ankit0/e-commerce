from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.inventory.models import Inventory


@receiver(post_save, sender=Inventory)
def inventory_post_save(sender, instance, **kwargs):
    if instance.quantity <= instance.low_stock_threshold:
        from apps.inventory.tasks import check_low_stock_levels

        # Trigger the check task which sends the digest/alert
        # We use .delay() to offload it
        check_low_stock_levels.delay()
        print(f"Low stock alert for {instance.product_variant}: {instance.quantity} remaining. Task queued.")
