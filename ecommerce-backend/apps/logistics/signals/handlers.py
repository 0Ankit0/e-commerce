from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.logistics.models import Shipment

@receiver(post_save, sender=Shipment)
def shipment_post_save(sender, instance, created, **kwargs):
    if instance.status == 'DELIVERED':
        order = instance.order
        order.status = 'DELIVERED'
        order.save(update_fields=['status'])
    elif instance.status == 'SHIPPED':
        order = instance.order
        order.status = 'SHIPPED'
        order.save(update_fields=['status'])
