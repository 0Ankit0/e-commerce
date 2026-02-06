from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F
from apps.orders.models import OrderItem, Order

def update_order_total(order):
    # Calculate sum of (unit_price * quantity)
    total = OrderItem.objects.filter(order=order).aggregate(
        total_amount=Sum(F('unit_price') * F('quantity'))
    )['total_amount'] or 0.00
    
    order.total_amount = total
    order.save(update_fields=['total_amount'])

@receiver(post_save, sender=OrderItem)
def order_item_post_save(sender, instance, created, **kwargs):
    update_order_total(instance.order)

@receiver(post_delete, sender=OrderItem)
def order_item_post_delete(sender, instance, **kwargs):
    update_order_total(instance.order)
