"""
Ma trận kiểm tra quyền theo role (customer / staff / admin) trên các API chính.
Chạy: python manage.py test core.test_role_matrix
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Profile
from contact.models import Contact
from core.permissions import RoleChoices
from orders.models import Order, ReturnRequest
from products.models import Category, Color, Product, ProductVariant, Size


def _rows(payload):
    """DRF trả list hoặc { results: [...] }."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("results") or []
    return list(payload)


class RoleMatrixIntegrationTests(TestCase):
    """
    Một lần tạo user + dữ liệu mẫu; kiểm tra từng role không lộ/không chặn sai.
    """

    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            username="rm_customer",
            email="rm_c@example.com",
            password="secret12345",
        )
        Profile.objects.filter(user=self.customer).update(role=RoleChoices.CUSTOMER)

        self.staff = User.objects.create_user(
            username="rm_staff",
            email="rm_s@example.com",
            password="secret12345",
        )
        Profile.objects.filter(user=self.staff).update(role=RoleChoices.STAFF)

        self.admin = User.objects.create_user(
            username="rm_admin",
            email="rm_a@example.com",
            password="secret12345",
        )
        Profile.objects.filter(user=self.admin).update(role=RoleChoices.ADMIN)

        self.cat = Category.objects.create(name="RM Cat", description="")
        self.product = Product.objects.create(
            name="RM Product",
            description="",
            price=Decimal("120000"),
            category=self.cat,
        )
        self.color = Color.objects.create(name="RM Đen", code="#111111")
        self.size = Size.objects.create(name="RM_M")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=7,
        )

        # Đơn + trả hàng để thử approve (staff được, customer không)
        self.order = Order.objects.create(
            user=self.customer,
            subtotal=Decimal("120000"),
            shipping_fee=Decimal("0"),
            total_price=Decimal("120000"),
            status="shipping",
        )
        self.return_req = ReturnRequest.objects.create(
            order=self.order,
            user=self.customer,
            reason="other",
            description="test",
            status="pending",
        )

        Contact.objects.create(
            name="Người gửi",
            email="x@y.com",
            phone="0900000000",
            subject="other",
            message="hello",
            handled=False,
        )

    # --- /api/auth/user/ ---
    def test_current_user_flags(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/auth/user/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data.get("can_access_admin"))
        self.assertFalse(r.data.get("is_admin"))

        self.client.force_authenticate(user=self.staff)
        r = self.client.get("/api/auth/user/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data.get("can_access_admin"))
        self.assertFalse(r.data.get("is_admin"))

        self.client.force_authenticate(user=self.admin)
        r = self.client.get("/api/auth/user/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data.get("can_access_admin"))
        self.assertTrue(r.data.get("is_admin"))

    # --- Dashboard admin (stats) & customer ---
    def test_dashboard_stats_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/core/dashboard/stats/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_stats_staff_vs_admin_scope(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.get("/api/core/dashboard/stats/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data.get("role_scope"), "staff")
        self.assertNotIn("revenue_today", r.data)

        self.client.force_authenticate(user=self.admin)
        r = self.client.get("/api/core/dashboard/stats/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data.get("role_scope"), "admin")
        self.assertIn("revenue_today", r.data)

    def test_customer_dashboard_only_customer_role(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/core/dashboard/customer/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("orders_total", r.data)

        for u in (self.staff, self.admin):
            self.client.force_authenticate(user=u)
            r = self.client.get("/api/core/dashboard/customer/")
            self.assertEqual(
                r.status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"user {u.username} should not access customer dashboard",
            )

    # --- Sản phẩm: staff/admin ghi; customer không ---
    def test_product_create_customer_forbidden_staff_admin_ok(self):
        body = {
            "name": "SP role test",
            "description": "d",
            "price": "99000",
            "category_id": self.cat.id,
        }
        self.client.force_authenticate(user=self.customer)
        r = self.client.post("/api/products/", body, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        r = self.client.post("/api/products/", body, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    # --- Biến thể / tồn: chỉ admin ghi ---
    def test_variant_get_public_patch_roles(self):
        r = self.client.get(
            "/api/products/variants/",
            {"product": self.product.id},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        url = f"/api/products/variants/{self.variant.id}/"
        self.client.force_authenticate(user=self.customer)
        self.assertEqual(
            self.client.patch(url, {"stock": 1}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(user=self.staff)
        self.assertEqual(
            self.client.patch(url, {"stock": 2}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(user=self.admin)
        r = self.client.patch(url, {"stock": 5}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5)

    # --- Mã giảm giá: staff/admin; customer không ---
    def test_discount_code_create_roles(self):
        today = timezone.localdate()
        body = {
            "name": "Mã test role",
            "code": "ROLEM1",
            "discount_percent": 5,
            "min_order_value": "0",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
            "is_active": True,
        }
        self.client.force_authenticate(user=self.customer)
        r = self.client.post("/api/orders/discount-codes/", body, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        r = self.client.post("/api/orders/discount-codes/", body, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    # --- Profiles: chỉ admin thấy toàn bộ ---
    def test_profiles_list_scope(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_rows(r.data)), 1)

        self.client.force_authenticate(user=self.staff)
        r = self.client.get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_rows(r.data)), 1)

        self.client.force_authenticate(user=self.admin)
        r = self.client.get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_rows(r.data)), 3)

    # --- Liên hệ: khách không list; staff list được ---
    def test_contact_list_staff_sees_customer_empty(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/contact/contacts/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_rows(r.data)), 0)

        self.client.force_authenticate(user=self.staff)
        r = self.client.get("/api/contact/contacts/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_rows(r.data)), 1)

    # --- Trả hàng: duyệt chỉ staff+ (API is_staff) ---
    def test_return_approve_staff_ok_customer_forbidden(self):
        url = f"/api/orders/returns/{self.return_req.id}/approve/"
        self.client.force_authenticate(user=self.customer)
        self.assertEqual(
            self.client.post(url, {}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.return_req.status = "pending"
        self.return_req.save(update_fields=["status"])
        self.order.status = "shipping"
        self.order.save(update_fields=["status"])

        self.client.force_authenticate(user=self.staff)
        r = self.client.post(url, {"admin_note": "ok"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    # --- Order items: xóa dòng đơn chỉ staff+ ---
    def test_order_item_delete_requires_staff(self):
        from orders.models import OrderItem

        oi = OrderItem.objects.create(
            order=self.order,
            product=self.variant,
            quantity=1,
            price=Decimal("120000"),
        )
        url = f"/api/orders/order-items/{oi.id}/"
        self.client.force_authenticate(user=self.customer)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
