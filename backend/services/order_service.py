"""
Order Service - Business logic for order processing
"""
from decimal import Decimal
from typing import Optional

from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from products.models import Product


class OrderService:
    """Service class for handling order-related business logic"""

    @staticmethod
    def create_order_from_cart(user, shipping_info: dict) -> Order:
        """
        Create an order from the user's cart items.

        Args:
            user: The user placing the order
            shipping_info: Dict containing shipping details (name, phone, address)

        Returns:
            Created Order instance
        """
        cart = Cart.objects.filter(user=user).first()
        if not cart or not cart.items.exists():
            raise ValueError("Cart is empty")

        # Calculate total price
        total_price = Decimal('0.00')
        for item in cart.items.all():
            total_price += item.product.price * item.quantity

        # Create order
        order = Order.objects.create(
            user=user,
            total_price=total_price,
            status='pending'
        )

        # Create order items from cart items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Clear the cart
        cart.items.all().delete()

        return order

    @staticmethod
    def update_order_status(order_id: int, status: str) -> Optional[Order]:
        """
        Update order status.

        Args:
            order_id: The order ID
            status: New status (pending, shipping, completed)

        Returns:
            Updated Order or None if not found
        """
        valid_statuses = ['pending', 'shipping', 'completed']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        try:
            order = Order.objects.get(id=order_id)
            order.status = status
            order.save()
            return order
        except Order.DoesNotExist:
            return None
