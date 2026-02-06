from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.vendors.models import Vendor

@receiver(post_save, sender=Vendor)
def vendor_post_save(sender, instance, created, **kwargs):
    if created:
        from apps.vendors.tasks import send_welcome_email, perform_background_checks
        # Trigger background tasks
        send_welcome_email.delay(instance.id)
        perform_background_checks.delay(instance.id)
        print(f"Vendor created: {instance.business_name}. Tasks queued.")
