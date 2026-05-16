"""API thống kê dashboard — staff: vận hành; admin: thêm tài chính & người dùng."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from contact.models import Contact, Feedback
from core.permissions import RoleChoices, is_admin, is_staff
from orders.models import Order, OrderItem, ReturnRequest
from products.models import Category, Product, ProductVariant


def _orders_by_status(order_qs):
    status_rows = order_qs.values("status").annotate(c=Count("id")).order_by("status")
    out = {row["status"]: row["c"] for row in status_rows}
    for key in ("pending", "shipping", "returning", "completed", "cancelled"):
        out.setdefault(key, 0)
    return out


class AdminDashboardStatsView(APIView):
    """GET — staff: vận hành; admin: đầy đủ doanh thu + biểu đồ + user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_staff(request.user):
            return Response(
                {"detail": "Chỉ nhân viên mới truy cập được."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if is_admin(request.user):
            return Response(self._build_admin_payload())
        return Response(self._build_staff_payload())

    def _build_staff_payload(self):
        now = timezone.now()
        today = now.date()
        stale_before = now - timedelta(days=2)

        order_qs = Order.objects.all()
        pending_count = order_qs.filter(status="pending").count()
        stale_pending_ids = list(
            order_qs.filter(status="pending", created_at__lt=stale_before)
            .order_by("created_at")
            .values_list("id", flat=True)[:15]
        )

        low_threshold = 5
        low_stock_variants = ProductVariant.objects.filter(stock__lte=low_threshold).count()
        low_stock_products = (
            Product.objects.filter(productvariant__stock__lte=low_threshold).distinct().count()
        )

        pending_returns = ReturnRequest.objects.filter(status="pending").count()

        return {
            "role_scope": "staff",
            "orders_today": order_qs.filter(created_at__date=today).count(),
            "pending_orders": pending_count,
            "shipping_orders": order_qs.filter(status="shipping").count(),
            "stale_pending_order_ids": stale_pending_ids,
            "pending_returns": pending_returns,
            "unhandled_contacts": Contact.objects.filter(handled=False).count(),
            "unhandled_feedbacks": Feedback.objects.filter(handled=False).count(),
            "low_stock_threshold": low_threshold,
            "low_stock_variants": low_stock_variants,
            "low_stock_products": low_stock_products,
            "catalog": {
                "products": Product.objects.count(),
                "variants": ProductVariant.objects.count(),
                "categories": Category.objects.count(),
            },
            "orders_by_status": _orders_by_status(order_qs),
        }

    def _build_admin_payload(self):
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        stale_before = now - timedelta(days=2)

        order_qs = Order.objects.all()

        revenue_today = order_qs.filter(created_at__date=today).exclude(status="cancelled").aggregate(
            s=Sum("total_price")
        )["s"] or Decimal("0")

        revenue_week = order_qs.filter(created_at__gte=week_ago).exclude(status="cancelled").aggregate(
            s=Sum("total_price")
        )["s"] or Decimal("0")

        pending_count = order_qs.filter(status="pending").count()
        stale_pending_ids = list(
            order_qs.filter(status="pending", created_at__lt=stale_before)
            .order_by("created_at")
            .values_list("id", flat=True)[:15]
        )

        low_threshold = 5
        low_stock_variants = ProductVariant.objects.filter(stock__lte=low_threshold).count()
        low_stock_products = (
            Product.objects.filter(productvariant__stock__lte=low_threshold).distinct().count()
        )

        month_start = date(today.year, today.month, 1)
        revenue_month = order_qs.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=today,
        ).exclude(status="cancelled").aggregate(s=Sum("total_price"))["s"] or Decimal("0")

        orders_total = order_qs.count()

        revenue_series = []
        for offset in range(13, -1, -1):
            d = today - timedelta(days=offset)
            rev = (
                order_qs.filter(created_at__date=d)
                .exclude(status="cancelled")
                .aggregate(s=Sum("total_price"))["s"]
                or Decimal("0")
            )
            oc = order_qs.filter(created_at__date=d).count()
            revenue_series.append(
                {
                    "date": d.isoformat(),
                    "label": d.strftime("%d/%m"),
                    "revenue": str(rev),
                    "orders": oc,
                }
            )

        top_products_rows = list(
            OrderItem.objects.filter(~Q(order__status="cancelled"))
            .values("product__product__id", "product__product__name")
            .annotate(revenue=Sum(F("price") * F("quantity")))
            .order_by("-revenue")[:8]
        )
        top_products = [
            {
                "id": row["product__product__id"],
                "name": row["product__product__name"] or "—",
                "revenue": str(row["revenue"] or Decimal("0")),
            }
            for row in top_products_rows
        ]

        role_rows = Profile.objects.values("role").annotate(c=Count("id")).order_by("role")
        users_by_role = {row["role"]: row["c"] for row in role_rows}

        customers_inactive = User.objects.filter(
            is_active=False,
            profile__role=RoleChoices.CUSTOMER,
        ).count()

        return {
            "role_scope": "admin",
            "revenue_today": str(revenue_today),
            "revenue_week": str(revenue_week),
            "revenue_month": str(revenue_month),
            "orders_today": order_qs.filter(created_at__date=today).count(),
            "orders_total": orders_total,
            "pending_orders": pending_count,
            "shipping_orders": order_qs.filter(status="shipping").count(),
            "stale_pending_order_ids": stale_pending_ids,
            "pending_returns": ReturnRequest.objects.filter(status="pending").count(),
            "low_stock_threshold": low_threshold,
            "low_stock_variants": low_stock_variants,
            "low_stock_products": low_stock_products,
            "unhandled_contacts": Contact.objects.filter(handled=False).count(),
            "unhandled_feedbacks": Feedback.objects.filter(handled=False).count(),
            "catalog": {
                "products": Product.objects.count(),
                "variants": ProductVariant.objects.count(),
                "categories": Category.objects.count(),
            },
            "users_total": User.objects.filter(is_active=True).count(),
            "users_by_role": users_by_role,
            "customers_inactive": customers_inactive,
            "revenue_series": revenue_series,
            "orders_by_status": _orders_by_status(order_qs),
            "top_products": top_products,
        }
