from celery import shared_task
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings
from apps.inventory.models import Inventory

@shared_task
def check_low_stock_levels():
    """
    Periodic task to check for items below low_stock_threshold.
    Sends a digest email to the admin if low stock items are found.
    """
    low_stock_items = Inventory.objects.filter(quantity__lte=F('low_stock_threshold'))
    count = low_stock_items.count()
    
    if count > 0:
        item_details = "\n".join([f"- {item.product_variant} (Qty: {item.quantity})" for item in low_stock_items])
        
        subject = f"Low Stock Alert: {count} Items"
        message = (
            f"The following items have dropped below their stock threshold:\n\n"
            f"{item_details}\n\n"
            f"Please restock immediately."
        )
        
        # Send to admin email configured in settings, fallback to standard from_email
        recipient = settings.EMAIL_HOST_USER if settings.EMAIL_HOST_USER else settings.EMAIL_FROM_ADDRESS
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_FROM_ADDRESS,
            recipient_list=[recipient],
            fail_silently=False,
        )
        
        return f"Alert sent for {count} low stock items."
    
    return "Checked stock. No low items found."

# Need to import models properly to avoid CheckError if F expression is used directly in filter without F import or validation? 
# Actually F is standard django.db.models.F. Let me fix imports.
