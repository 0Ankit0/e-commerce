from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.orders.models import Cart, CartItem, Order, OrderItem, VendorOrder
from apps.orders.serializers import (
    CartItemSerializer,
    CartSerializer,
    OrderItemSerializer,
    OrderSerializer,
    VendorOrderSerializer,
)
from apps.orders.services.order_processing import create_order_from_cart


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Ideally restrict to user's cart, but for now simple
    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Check for Idempotency-Key
        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key:
            # Check if order already exists for this user and key
            existing_order = Order.objects.filter(user=request.user, idempotency_key=idempotency_key).first()
            if existing_order:
                serializer = self.get_serializer(existing_order)
                return Response(serializer.data, status=status.HTTP_200_OK)

        # Checkout flow: convert Cart to Order
        # We assume the user has a cart.
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"error": "No active cart found"}, status=status.HTTP_400_BAD_REQUEST)

        if not cart.items.exists():
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Call service
        try:
            # Pass idempotency_key to service if needed, or set it on order after creation
            order = create_order_from_cart(cart, request.user)

            if idempotency_key:
                order.idempotency_key = idempotency_key
                order.save(update_fields=["idempotency_key"])

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VendorOrderViewSet(viewsets.ModelViewSet):
    queryset = VendorOrder.objects.all()
    serializer_class = VendorOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
