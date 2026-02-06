import time

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.vendors.models import Vendor


@shared_task
def send_welcome_email(vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        subject = f"Welcome to E-Commerce, {vendor.business_name}!"
        message = (
            f"Dear {vendor.owner.get_full_name() or vendor.business_name},\n\n"
            f"Welcome to our platform! We are thrilled to have you onboard.\n"
            f"Your vendor account is currently under review. We will notify you once verified.\n\n"
            f"Best regards,\nThe Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_FROM_ADDRESS,
            recipient_list=[vendor.contact_email],
            fail_silently=False,
        )
        return f"Welcome email sent to {vendor.contact_email}"
    except Vendor.DoesNotExist:
        return f"Vendor {vendor_id} not found"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@shared_task
def perform_background_checks(vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        # Simulate a real API call delay
        time.sleep(2)

        # Real logic: Check if documents are uploaded
        from apps.vendors.services.onboarding import verify_vendor

        if verify_vendor(vendor):
            return f"Vendor {vendor.business_name} verified successfully."
        else:
            return f"Vendor {vendor.business_name} failed check: Missing required documents."

    except Vendor.DoesNotExist:
        return f"Vendor {vendor_id} not found"
