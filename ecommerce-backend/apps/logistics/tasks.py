import random

from celery import shared_task

from apps.logistics.models import Shipment


@shared_task
def poll_shipment_status(shipment_id):
    """
    Polls an external API for the latest status of a shipment.
    """
    try:
        shipment = Shipment.objects.get(id=shipment_id)

        # In a real app, this would be requests.get(f"https://api.fedex.com/track/{shipment.tracking_number}")
        # For a "working" demo without credentials, we simulate state progression

        current_status = shipment.status
        new_status = current_status

        # Simple state machine simulation
        if current_status == "PENDING":
            new_status = "SHIPPED"
        elif current_status == "SHIPPED" and random.choice([True, False]):  # 50% chance to deliver
            new_status = "DELIVERED"

        if new_status != current_status:
            shipment.status = new_status
            shipment.save(update_fields=["status"])
            return f"Shipment {shipment.id} updated to {new_status}"

        return f"Shipment {shipment.id} status remains {current_status}"
    except Shipment.DoesNotExist:
        return f"Shipment {shipment_id} not found"
