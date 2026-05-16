"""
Custom decorators for views
"""
from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def validate_cart_item(func):
    """
    Decorator to validate cart item before adding/updating.
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'error': 'quantity must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return func(self, request, *args, **kwargs)
    return wrapper


def require_cart(func):
    """
    Decorator to ensure user has an active cart.
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        from cart.models import Cart
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response(
                {'error': 'No active cart found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return func(self, request, *args, **kwargs)
    return wrapper
