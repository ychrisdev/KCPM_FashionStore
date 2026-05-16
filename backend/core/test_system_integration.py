"""
Luồng API xuyên suốt nhiều app: catalog → đăng ký/JWT → giỏ → checkout → wishlist → liên hệ → đánh giá.

Chạy: python manage.py test core.test_system_integration
Hoặc: python manage.py test (Django tự discover file test*.py trong app core).
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Color, Product, ProductVariant, Size


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ORDER_CONFIRMATION_EMAIL_ENABLED=False,
)
class SystemApiIntegrationTests(TestCase):
    """Kiểm tra các endpoint chính hoạt động cùng nhau trên một DB test."""

    def setUp(self):
        mail.outbox.clear()
        self.client = APIClient()
        self.category = Category.objects.create(name="Test Cat", description="")
        self.color = Color.objects.create(name="Black", code="#000000")
        self.size = Size.objects.create(name="M")
        self.product = Product.objects.create(
            name="Integration Tee",
            description="",
            category=self.category,
            price=Decimal("199000"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=20,
        )

    def test_public_catalog_endpoints(self):
        r = self.client.get("/api/products/categories/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.get("/api/products/", {"search": "Integration"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        payload = r.data
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
        self.assertGreaterEqual(len(rows), 1)

    def test_discount_codes_active_public(self):
        r = self.client.get("/api/orders/discount-codes/active/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsInstance(r.data, list)

    def test_contact_meta_and_anonymous_contact_create(self):
        r = self.client.get("/api/contact/meta/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data.get("brand"), "FashionStore")

        r = self.client.post(
            "/api/contact/contacts/",
            {
                "name": "Nguyen A",
                "email": "a@example.com",
                "phone": "0900000000",
                "subject": "order",
                "message": "Hello from integration test",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", r.data)

    def test_register_jwt_cart_checkout_wishlist_review_flow(self):
        # Đăng ký
        reg = self.client.post(
            "/api/auth/registration/",
            {
                "username": "flow_user",
                "email": "flow_user@example.com",
                "password": "SecretPass1",
                "password_confirm": "SecretPass1",
            },
            format="json",
        )
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED, reg.data)
        user = User.objects.get(username="flow_user")

        # JWT (endpoint gốc project)
        tok = self.client.post(
            "/api/auth/token/",
            {"username": "flow_user", "password": "SecretPass1"},
            format="json",
        )
        self.assertEqual(tok.status_code, status.HTTP_200_OK, tok.data)
        self.assertIn("access", tok.data)
        self.assertIn("refresh", tok.data)

        refresh = tok.data["refresh"]
        ref = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(ref.status_code, status.HTTP_200_OK)
        self.assertIn("access", ref.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok.data['access']}")

        me = self.client.get("/api/auth/user/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data.get("username"), "flow_user")

        # Giỏ hàng
        add = self.client.post(
            "/api/cart/cart-items/",
            {"product_variant_id": self.variant.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(add.status_code, status.HTTP_201_CREATED, add.data)

        carts = self.client.get("/api/cart/carts/")
        self.assertEqual(carts.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(carts.data), 1)

        cart_item_id = add.data["id"]

        # Checkout
        co = self.client.post(
            "/api/orders/orders/checkout/",
            {
                "name": "Flow User",
                "phone": "0912345678",
                "address": "1 Test Street",
                "cart_item_ids": [cart_item_id],
                "payment_method": "cod",
            },
            format="json",
        )
        self.assertEqual(co.status_code, status.HTTP_201_CREATED, co.data)
        order_id = co.data.get("id")
        self.assertIsNotNone(order_id)

        orders = self.client.get("/api/orders/orders/")
        self.assertEqual(orders.status_code, status.HTTP_200_OK)

        # Wishlist
        wl_ids = self.client.get("/api/wishlist/items/")
        self.assertEqual(wl_ids.status_code, status.HTTP_200_OK)
        self.assertEqual(wl_ids.data.get("product_ids"), [])

        tg = self.client.post(
            "/api/wishlist/toggle/",
            {"product_id": self.product.id},
            format="json",
        )
        self.assertEqual(tg.status_code, status.HTTP_200_OK)
        self.assertTrue(tg.data.get("in_wishlist"))
        self.assertIn(self.product.id, tg.data.get("product_ids", []))

        # Đánh giá (cần đăng nhập)
        rv = self.client.post(
            "/api/reviews/reviews/",
            {
                "product": self.variant.id,
                "rating": 5,
                "feedback_type": "quality",
                "content": "Good",
            },
            format="json",
        )
        self.assertEqual(rv.status_code, status.HTTP_201_CREATED, rv.data)

        self.variant.refresh_from_db()
        self.assertLessEqual(self.variant.stock, 18)

        user.refresh_from_db()
        self.assertTrue(user.check_password("SecretPass1"))


class SystemApiAuthzSmokeTests(TestCase):
    """Một vài kiểm tra quyền cơ bản (không cần dữ liệu catalog)."""

    def test_anonymous_cannot_access_cart(self):
        c = APIClient()
        r = c.get("/api/cart/carts/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_post_review(self):
        c = APIClient()
        r = c.post(
            "/api/reviews/reviews/",
            {"product": 1, "rating": 4, "feedback_type": "quality"},
            format="json",
        )
        self.assertIn(
            r.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
