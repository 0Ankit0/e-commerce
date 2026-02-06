from django.db import transaction

from apps.inventory.models import Inventory


def reserve_stock(inventory: Inventory, quantity: int) -> bool:
    """
    Attempts to reserve stock. Returns True if successful, False if insufficient stock.
    Using atomic transaction for safety.
    """
    with transaction.atomic():
        # Lock the row for update
        locked_inv = Inventory.objects.select_for_update().get(pk=inventory.pk)
        if locked_inv.quantity >= quantity:
            locked_inv.quantity -= quantity
            locked_inv.reserved_qty += quantity
            locked_inv.save()
            return True
        return False


def release_stock(inventory: Inventory, quantity: int) -> None:
    """Releases reserved stock back to available quantity."""
    with transaction.atomic():
        locked_inv = Inventory.objects.select_for_update().get(pk=inventory.pk)
        if locked_inv.reserved_qty >= quantity:
            locked_inv.reserved_qty -= quantity
            locked_inv.quantity += quantity
            locked_inv.save()
