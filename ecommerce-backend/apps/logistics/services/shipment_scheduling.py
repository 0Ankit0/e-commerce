from typing import TYPE_CHECKING, Any, cast

from django.db.models import Count, Q

from apps.logistics.models import DeliveryAgent, Shipment

if TYPE_CHECKING:
    pass


def assign_delivery_agent(shipment: Shipment) -> bool:
    """
    Assigns a delivery agent to the shipment.
    Logic: Finds available agent with least number of active shipments (Load Balancing).
    """
    # Find available agents annotated with current shipment count
    # Default related_name for agent is shipment_set
    active_statuses = [
        Shipment.Status.CREATED,
        Shipment.Status.AWAITING_PICKUP,
        Shipment.Status.PICKED_UP,
        Shipment.Status.IN_TRANSIT,
        Shipment.Status.AT_HUB,
        Shipment.Status.OUT_FOR_DELIVERY,
    ]

    candidate = (
        DeliveryAgent.objects.filter(status=DeliveryAgent.Status.AVAILABLE)
        .annotate(active_shipment_count=Count("shipment", filter=Q(shipment__status__in=active_statuses)))
        .order_by("active_shipment_count")
        .first()
    )

    if candidate:
        # Cast to Any to access annotated field or use a more specific type
        candidate_obj = cast(Any, candidate)
        shipment.agent = candidate_obj
        shipment.save(update_fields=["agent"])
        print(f"Assigned shipment {shipment.id} to agent {candidate_obj}")
        return True

    print(f"No available agents found for shipment {shipment.id}")
    return False


def track_shipment(tracking_number: str) -> dict:
    """
    Returns tracking info.
    """
    return {"status": "In Transit", "location": "Central Hub", "estimated_delivery": "2023-12-25"}
