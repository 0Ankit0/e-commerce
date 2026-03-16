from decimal import Decimal

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.orders.models import Cart, CartItem, Coupon, Order, OrderItem, VendorOrder
from apps.orders.serializers import (
    CartItemSerializer,
    CartSerializer,
    CouponApplySerializer,
    OrderActionResponseSerializer,
    OrderInvoiceSerializer,
    OrderItemSerializer,
    OrderSerializer,
    OrderTrackingSerializer,
    VendorOrderSerializer,
)
from apps.orders.services import (
    OrderActionError,
    build_invoice_payload,
    calculate_coupon_discount,
    cancel_order,
    get_order_tracking,
    initiate_return,
)
from apps.orders.services.order_processing import create_order_from_cart


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="clear-cart")
    def clear_cart(self, request, pk=None):
        cart = self.get_object()
        deleted_count, _ = cart.items.all().delete()
        return Response({"status": "ok", "items_removed": deleted_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="apply-coupon")
    def apply_coupon(self, request, pk=None):
        cart = self.get_object()
        serializer = CouponApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"].strip()
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon or not coupon.is_valid():
            return Response({"error": "Invalid or expired coupon."}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = sum(Decimal(item.price_at_add) * item.quantity for item in cart.items.all())
        if subtotal < coupon.min_order_value:
            return Response(
                {"error": f"Coupon requires minimum order value of {coupon.min_order_value}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        discount = calculate_coupon_discount(subtotal, coupon)
        total = max(Decimal("0"), subtotal - discount)
        return Response(
            {
                "status": "applied",
                "coupon": coupon.code,
                "subtotal": str(subtotal),
                "discount": str(discount),
                "total": str(total),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="remove-coupon")
    def remove_coupon(self, request, pk=None):
        self.get_object()
        payload = {"status": "removed", "message": "Coupon removed from cart pricing context."}
        serializer = OrderActionResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get("reason", "")
        try:
            order = cancel_order(order, reason=reason)
        except OrderActionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = {"status": order.status, "message": "Order cancelled successfully."}
        serializer = OrderActionResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        order = self.get_object()
        payload = get_order_tracking(order)
        serializer = OrderTrackingSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="request-return")
    def request_return(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get("reason", "")
        try:
            order = initiate_return(order, reason=reason)
        except OrderActionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = {"status": order.status, "message": "Return requested successfully."}
        serializer = OrderActionResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):
        order = self.get_object()
        payload = build_invoice_payload(order)
        serializer = OrderInvoiceSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VendorOrderViewSet(viewsets.ModelViewSet):
    queryset = VendorOrder.objects.all()
    serializer_class = VendorOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
