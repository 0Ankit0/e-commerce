from apps.logistics.models import Shipment

from apps.logistics.models import Shipment, DeliveryAgent
from django.db.models import Count, Q

def assign_delivery_agent(shipment: Shipment) -> bool:

def assign_delivery_agent(shipment: Shipment) -> bool:
    """
    Assigns a delivery agent to the shipment.
    Logic: Finds active agent with least number of active shipments (Load Balancing).
    """
    # Find active agents annotated with current shipment count
    candidate = DeliveryAgent.objects.filter(is_active=True).annotate(
        active_shipment_count=Count('assigned_shipments', filter=models.Q(assigned_shipments__status__in=['PENDING', 'SHIPPED']))
    ).order_by('active_shipment_count').first()
    
    if candidate:
        shipment.delivery_agent = candidate
        shipment.save(update_fields=['delivery_agent'])
        print(f"Assigned shipment {shipment.id} to agent {candidate.name}")
        return True
        
    print(f"No active agents found for shipment {shipment.id}")
    return False

def track_shipment(tracking_number: str) -> dict:
    """
    Returns tracking info.
    """
    return {
        "status": "In Transit",
        "location": "Central Hub",
        "estimated_delivery": "2023-12-25"
    }
