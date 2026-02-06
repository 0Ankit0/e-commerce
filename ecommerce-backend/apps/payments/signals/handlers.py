from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.payments.models import Payment

@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    if instance.status == 'SUCCESS':
        order = instance.order
        order.payment_status = 'PAID'
        order.save(update_fields=['payment_status'])
