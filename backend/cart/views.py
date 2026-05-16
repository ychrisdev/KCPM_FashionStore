from rest_framework import permissions, viewsets, status
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).order_by("-created_at")


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).select_related(
            "cart", "product", "product__product", "product__product__category", "product__color", "product__size"
        )

    def create(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "cart": cart},
        )
        serializer.is_valid(raise_exception=True)
        variant = serializer.validated_data.get("product")
        quantity = serializer.validated_data.get("quantity", 1)

        if variant:
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=variant,
                defaults={"quantity": quantity},
            )
            if not created:
                item.quantity += quantity
                item.save()
        else:
            item = serializer.save(cart=cart)

        return Response(
            CartItemSerializer(item, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )