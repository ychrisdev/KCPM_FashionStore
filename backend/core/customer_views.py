"""Dashboard tóm tắt cho khách hàng (role customer) — chỉ dữ liệu của chính user."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart, CartItem
from core.permissions import RoleChoices, get_user_role
from orders.models import Order, ReturnRequest
from wishlist.models import WishlistItem


class CustomerDashboardView(APIView):
    """
    GET — thống kê cá nhân: đơn hàng gần đây, giỏ, yêu thích, trả hàng.
    Chỉ role *customer* (không phải staff/admin).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if get_user_role(user) != RoleChoices.CUSTOMER:
            return Response(
                {"detail": "Dashboard này chỉ dành cho tài khoản khách hàng."},
                status=status.HTTP_403_FORBIDDEN,
            )

        order_qs = Order.objects.filter(user=user)
        orders_total = order_qs.count()

        status_rows = order_qs.values("status").annotate(c=Count("id"))
        orders_by_status = {row["status"]: row["c"] for row in status_rows}
        for key in ("pending", "shipping", "returning", "completed", "cancelled"):
            orders_by_status.setdefault(key, 0)

        recent_qs = order_qs.order_by("-created_at")[:5]
        recent_orders = []
        for o in recent_qs:
            item_count = o.orderitem_set.count()
            recent_orders.append(
                {
                    "id": o.id,
                    "status": o.status,
                    "total_price": str(o.total_price),
                    "created_at": o.created_at.isoformat(),
                    "item_count": item_count,
                }
            )

        wishlist_count = WishlistItem.objects.filter(user=user).count()

        cart_item_count = 0
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_item_count = (
                CartItem.objects.filter(cart=cart).aggregate(s=Sum("quantity"))["s"] or 0
            )

        pending_returns = ReturnRequest.objects.filter(user=user, status="pending").count()
        active_returns = ReturnRequest.objects.filter(user=user, status__in=("approved",)).count()

        today = timezone.localdate()
        orders_daily_7d = []
        for offset in range(6, -1, -1):
            d = today - timedelta(days=offset)
            oc = order_qs.filter(created_at__date=d).count()
            orders_daily_7d.append(
                {
                    "date": d.isoformat(),
                    "label": d.strftime("%d/%m"),
                    "orders": oc,
                }
            )

        return Response(
            {
                "orders_total": orders_total,
                "orders_by_status": orders_by_status,
                "recent_orders": recent_orders,
                "wishlist_count": wishlist_count,
                "cart_item_count": int(cart_item_count),
                "pending_returns": pending_returns,
                "active_returns": active_returns,
                "orders_daily_7d": orders_daily_7d,
            }
        )
