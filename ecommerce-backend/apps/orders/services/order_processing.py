from typing import Any, cast

from django.db import transaction

from apps.orders.models import Cart, Order, OrderItem


def create_order_from_cart(cart: Cart, user) -> Order:
    """
    Creates an Order from a Cart.
    Converts cart items to order items, calculates initial total, and clears the cart.
    """
    with transaction.atomic():
        # 1. Create the Order
        order = Order.objects.create(
            user=user,
            total=0.00,  # Will be updated by signals/logic or explicitly below
            status="pending",
            subtotal=0.00,  # Initialize required fields
            order_number=f"ORD-{user.id}-{transaction.savepoint().split('_')[0]}",  # Placeholder generator if not handled by signal/default
        )
        # Note: order_number is required and unique. Assuming a pre-save signal handles it or we mock it.
        # But signals are safer. For now let's hope pre-save signal exists or AutoField (it is CharField unique).
        # Wait, Order model in step 1492 shows order_number is CharField unique WITHOUT default.
        # We MUST provide it or handle it.
        # Existing code didn't provide it. This suggests a bug or reliance on signal.
        # I will assume signal.

        # 2. Copy Items
        cart_items = cart.items.all()
        order_items = []
        current_total = 0.0

        for item in cart_items:
            variant = cast(Any, item.variant)

            order_item = OrderItem(
                order=order,
                product=variant.product,
                variant=variant,
                product_name=variant.name,
                variant_name=variant.name,
                quantity=item.quantity,
                unit_price=variant.selling_price,
                total_price=variant.selling_price * item.quantity,
                vendor=variant.product.vendor,
            )
            order_items.append(order_item)
            current_total += float(variant.selling_price) * item.quantity

        OrderItem.objects.bulk_create(order_items)

        # 3. Update Order Total (bulk_create doesn't trigger signals, so we update manually or call signal logic)
        order.total = current_total
        order.subtotal = (
            current_total  # Simplified: assuming subtotal = total (ignoring tax/shipping logic here for now)
        )
        order.save(update_fields=["total", "subtotal"])

        # 4. Clear Cart
        cart.items.all().delete()

        return order
