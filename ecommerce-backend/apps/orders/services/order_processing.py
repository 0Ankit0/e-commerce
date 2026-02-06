from django.db import transaction
from apps.orders.models import Order, OrderItem, Cart

def create_order_from_cart(cart: Cart, user) -> Order:
    """
    Creates an Order from a Cart.
    Converts cart items to order items, calculates initial total, and clears the cart.
    """
    with transaction.atomic():
        # 1. Create the Order
        order = Order.objects.create(
            user=user,
            total_amount=0.00, # Will be updated by signals/logic or explicitly below
            status='PENDING'
        )
        
        # 2. Copy Items
        cart_items = cart.items.all()
        order_items = []
        current_total = 0.0
        
        for item in cart_items:
            # Check stock availability here if needed (omitted for brevity, relying on inventory service potentially)
            order_item = OrderItem(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                unit_price=item.product_variant.price # Snapshot price
            )
            order_items.append(order_item)
            current_total += float(item.product_variant.price) * item.quantity
            
        OrderItem.objects.bulk_create(order_items)
        
        # 3. Update Order Total (bulk_create doesn't trigger signals, so we update manually or call signal logic)
        order.total_amount = current_total
        order.save(update_fields=['total_amount'])
        
        # 4. Clear Cart
        cart.items.all().delete()
        
        return order
