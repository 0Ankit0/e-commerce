from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.orders.models import Order


@shared_task
def send_order_confirmation(order_id):
    try:
        order = Order.objects.select_related("user").get(id=order_id)
        user_email = order.user.email

        subject = f"Order Confirmation - Order #{order.id}"
        message = (
            f"Hi {order.user.get_full_name() or 'Customer'},\n\n"
            f"Thank you for your order! We have received your order #{order.id} "
            f"amounting to {order.total_amount}.\n\n"
            f"We will notify you when your items are shipped.\n\n"
            f"Regards,\nE-Commerce Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_FROM_ADDRESS,
            recipient_list=[user_email],
            fail_silently=False,
        )
        return f"Confirmation sent for Order #{order.id} to {user_email}"
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Failed to send email: {str(e)}"
