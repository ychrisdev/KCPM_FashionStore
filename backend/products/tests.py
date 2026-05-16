from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Profile
from core.permissions import RoleChoices
from products.models import Category, Color, Product, ProductVariant, Size


class ProductVariantStockPermissionTests(TestCase):
    """Chỉ admin ghi biến thể/tồn; staff GET được danh sách để theo dõi."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_var",
            email="adm_var@example.com",
            password="secret12345",
        )
        Profile.objects.filter(user=self.admin).update(role=RoleChoices.ADMIN)

        self.staff = User.objects.create_user(
            username="staff_var",
            email="staff_var@example.com",
            password="secret12345",
        )
        Profile.objects.filter(user=self.staff).update(role=RoleChoices.STAFF)

        cat = Category.objects.create(name="Cat", description="")
        self.product = Product.objects.create(
            name="SP test",
            description="",
            price="100000",
            category=cat,
        )
        self.color = Color.objects.create(name="Đen", code="#111111")
        self.size = Size.objects.create(name="M")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=10,
        )

    def test_staff_can_list_variants(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.get(
            "/api/products/variants/",
            {"product": self.product.id},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        payload = r.data
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
        self.assertGreaterEqual(len(rows), 1)

    def test_staff_cannot_patch_variant_stock(self):
        self.client.force_authenticate(user=self.staff)
        url = f"/api/products/variants/{self.variant.id}/"
        r = self.client.patch(url, {"stock": 99}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_admin_can_patch_variant_stock(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/products/variants/{self.variant.id}/"
        r = self.client.patch(url, {"stock": 42}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 42)
