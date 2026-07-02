from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Profile
from core.permissions import RoleChoices
from products.models import Category, Color, Product, ProductVariant, Size

import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from accounts.models import Profile
from core.permissions import RoleChoices
from products.models import Category, Color, Product, ProductImage, ProductVariant, Promotion, Size
from products.serializers import (
    CategorySerializer,
    ProductImageSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    PromotionSerializer,
    SizeSerializer,
    normalize_size_name,
)

# Thư mục media tạm dùng riêng cho test, tránh ghi file thật vào MEDIA_ROOT của dự án
MEDIA_ROOT = tempfile.mkdtemp()

# Ảnh PNG 1x1 hợp lệ (đủ để ImageField/Pillow decode được) dùng chung cho mọi test upload
PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


def make_image(name="test.png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


def tearDownModule():
    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)


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


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ModelStrAndPropertyTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Áo", description="d")
        self.product = Product.objects.create(
            name="Áo thun", description="d", price=100000, category=self.category
        )
        self.color = Color.objects.create(name="Đỏ", code="#f00")
        self.size = Size.objects.create(name="L", order=1)

    def test_category_str(self):
        self.assertEqual(str(self.category), "Áo")

    def test_product_str(self):
        self.assertEqual(str(self.product), "Áo thun")

    def test_product_image_str(self):
        img = ProductImage.objects.create(product=self.product, image=make_image())
        self.assertEqual(str(img), self.product.name)

    def test_color_str(self):
        self.assertEqual(str(self.color), "Đỏ")

    def test_size_str(self):
        self.assertEqual(str(self.size), "L")

    def test_variant_str_and_price_with_explicit_price(self):
        variant = ProductVariant.objects.create(
            product=self.product, color=self.color, size=self.size,
            stock=5, price=50000,
        )
        self.assertEqual(variant.get_price(), 50000)
        self.assertIn(self.product.name, str(variant))

    def test_variant_price_falls_back_to_product_price(self):
        variant = ProductVariant.objects.create(
            product=self.product, color=self.color, size=self.size,
            stock=5, price=None,
        )
        self.assertEqual(variant.get_price(), self.product.price)

    def test_promotion_is_active_true(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        self.assertTrue(promo.is_active)
        self.assertEqual(str(promo), "Sale")

    def test_promotion_is_active_false_expired(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Old", discount_percent=10,
            start_date=today - timedelta(days=10), end_date=today - timedelta(days=1),
        )
        self.assertFalse(promo.is_active)

    def test_promotion_is_active_false_future(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Future", discount_percent=10,
            start_date=today + timedelta(days=1), end_date=today + timedelta(days=5),
        )
        self.assertFalse(promo.is_active)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class CategorySerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_to_representation_placeholder_when_no_image(self):
        cat = Category.objects.create(name="Quần", description="")
        data = CategorySerializer(cat).data
        self.assertIn("placeholder", data["image"])

    def test_to_representation_with_image_and_request(self):
        cat = Category.objects.create(name="Giày", description="", image=make_image())
        request = self.factory.get("/api/products/categories/")
        data = CategorySerializer(cat, context={"request": request}).data
        self.assertTrue(data["image"].startswith("http"))

    def test_to_representation_with_image_no_request(self):
        cat = Category.objects.create(name="Túi", description="", image=make_image())
        data = CategorySerializer(cat).data
        self.assertNotIn("placeholder", data["image"])


class PromotionSerializerTests(TestCase):
    def test_validate_discount_percent_too_low(self):
        s = PromotionSerializer(data={
            "name": "P", "discount_percent": 0,
            "start_date": "2026-01-01", "end_date": "2026-01-10",
        })
        self.assertFalse(s.is_valid())
        self.assertIn("discount_percent", s.errors)

    def test_validate_discount_percent_too_high(self):
        s = PromotionSerializer(data={
            "name": "P", "discount_percent": 150,
            "start_date": "2026-01-01", "end_date": "2026-01-10",
        })
        self.assertFalse(s.is_valid())
        self.assertIn("discount_percent", s.errors)

    def test_validate_end_before_start(self):
        s = PromotionSerializer(data={
            "name": "P", "discount_percent": 10,
            "start_date": "2026-01-10", "end_date": "2026-01-01",
        })
        self.assertFalse(s.is_valid())

    def test_valid_promotion(self):
        s = PromotionSerializer(data={
            "name": "P", "discount_percent": 10,
            "start_date": "2026-01-01", "end_date": "2026-01-10",
        })
        self.assertTrue(s.is_valid(), s.errors)
        promo = s.save()
        self.assertFalse(promo.is_active)


class SizeSerializerTests(TestCase):
    def test_normalize_size_name_helper(self):
        self.assertEqual(normalize_size_name("  m "), "M")

    def test_validate_name_empty(self):
        s = SizeSerializer(data={"name": "   ", "order": 0})
        self.assertFalse(s.is_valid())

    def test_validate_name_duplicate(self):
        Size.objects.create(name="XL", order=0)
        s = SizeSerializer(data={"name": "xl", "order": 1})
        self.assertFalse(s.is_valid())

    def test_validate_name_ok_and_representation_normalized(self):
        s = SizeSerializer(data={"name": "sm", "order": 0})
        self.assertTrue(s.is_valid(), s.errors)
        size = s.save()
        self.assertEqual(SizeSerializer(size).data["name"], "SM")

    def test_validate_name_excludes_self_on_update(self):
        size = Size.objects.create(name="XS", order=0)
        s = SizeSerializer(size, data={"name": "xs", "order": 1}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)


class ProductVariantSerializerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Cat", description="")
        self.product = Product.objects.create(
            name="SP", description="", price=100000, category=self.category
        )
        self.color = Color.objects.create(name="Xanh", code="#00f")
        self.size = Size.objects.create(name="M")

    def test_effective_price_without_promotion(self):
        variant = ProductVariant.objects.create(
            product=self.product, color=self.color, size=self.size, stock=1, price=100000
        )
        data = ProductVariantSerializer(variant).data
        self.assertEqual(data["effective_price"], 100000)

    def test_effective_price_with_active_promotion(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        self.product.promotion = promo
        self.product.save()
        variant = ProductVariant.objects.create(
            product=self.product, color=self.color, size=self.size, stock=1, price=100000
        )
        data = ProductVariantSerializer(variant).data
        self.assertEqual(data["effective_price"], 90000)

    def test_validate_price_negative(self):
        s = ProductVariantSerializer(data={
            "product_id": self.product.id, "color_id": self.color.id,
            "size_id": self.size.id, "stock": 1, "price": 0,
        })
        self.assertFalse(s.is_valid())

    def test_validate_price_none_allowed(self):
        s = ProductVariantSerializer(data={
            "product_id": self.product.id, "color_id": self.color.id,
            "size_id": self.size.id, "stock": 1,
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_validate_duplicate_variant(self):
        ProductVariant.objects.create(
            product=self.product, color=self.color, size=self.size, stock=1, price=100000
        )
        s = ProductVariantSerializer(data={
            "product_id": self.product.id, "color_id": self.color.id,
            "size_id": self.size.id, "stock": 2, "price": 90000,
        })
        self.assertFalse(s.is_valid())

    def test_validate_update_excludes_self(self):
        variant = ProductVariant.objects.create(
            product=self.product, color=self.color, size=self.size, stock=1, price=100000
        )
        s = ProductVariantSerializer(variant, data={"stock": 5}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ProductImageSerializerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Cat", description="")
        self.product = Product.objects.create(
            name="SP", description="", price=100000, category=self.category
        )
        self.factory = APIRequestFactory()

    def test_get_image_with_request(self):
        img = ProductImage.objects.create(product=self.product, image=make_image())
        request = self.factory.get("/")
        data = ProductImageSerializer(img, context={"request": request}).data
        self.assertTrue(data["image"].startswith("http"))

    def test_get_image_without_request(self):
        img = ProductImage.objects.create(product=self.product, image=make_image())
        data = ProductImageSerializer(img).data
        self.assertIsNotNone(data["image"])

    def test_get_image_none_when_no_file(self):
        img = ProductImage(product=self.product)
        data = ProductImageSerializer(img).data
        self.assertIsNone(data["image"])


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ProductSerializerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Cat", description="")
        self.factory = APIRequestFactory()

    def _base_payload(self, **overrides):
        payload = {
            "name": "SP mới", "description": "mô tả",
            "price": 100000, "category_id": self.category.id,
        }
        payload.update(overrides)
        return payload

    def test_create_without_images(self):
        s = ProductSerializer(data=self._base_payload())
        self.assertTrue(s.is_valid(), s.errors)
        product = s.save()
        self.assertEqual(ProductImage.objects.filter(product=product).count(), 0)

    def test_create_with_upload_images_and_size_chart(self):
        s = ProductSerializer(data=self._base_payload())
        self.assertTrue(s.is_valid(), s.errors)
        product = s.save(
            upload_images=[make_image("a.png"), make_image("b.png")],
            size_chart_upload=make_image("chart.png"),
        )
        self.assertEqual(ProductImage.objects.filter(product=product).count(), 2)
        self.assertTrue(product.size_chart)

    def test_update_clears_promotion_and_size_chart(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        product = Product.objects.create(
            name="SP", description="d", price=100000, category=self.category,
            promotion=promo, size_chart=make_image(),
        )
        s = ProductSerializer(product, data={"name": "SP sửa"}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        updated = s.save(clear_promotion=True, clear_size_chart=True)
        self.assertIsNone(updated.promotion)
        self.assertFalse(updated.size_chart)

    def test_update_with_new_size_chart_and_images(self):
        product = Product.objects.create(
            name="SP", description="d", price=100000, category=self.category,
        )
        s = ProductSerializer(product, data={"name": "SP sửa"}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        updated = s.save(
            upload_images=[make_image()],
            size_chart_upload=make_image("c.png"),
        )
        self.assertTrue(updated.size_chart)
        self.assertEqual(ProductImage.objects.filter(product=updated).count(), 1)

    def test_get_image_placeholder_when_no_images(self):
        product = Product.objects.create(
            name="SP không ảnh", description="d", price=100000, category=self.category,
        )
        data = ProductSerializer(product).data
        self.assertIn("placeholder", data["image"])

    def test_get_image_with_request(self):
        product = Product.objects.create(
            name="SP", description="d", price=100000, category=self.category,
        )
        ProductImage.objects.create(product=product, image=make_image())
        request = self.factory.get("/")
        data = ProductSerializer(product, context={"request": request}).data
        self.assertTrue(data["image"].startswith("http"))

    def test_get_image_without_request_uses_media_url(self):
        product = Product.objects.create(
            name="SP", description="d", price=100000, category=self.category,
        )
        ProductImage.objects.create(product=product, image=make_image())
        data = ProductSerializer(product).data
        self.assertNotIn("placeholder", data["image"])

    def test_get_old_price_none_without_promotion(self):
        product = Product.objects.create(
            name="SP", description="d", price=100000, category=self.category,
        )
        data = ProductSerializer(product).data
        self.assertIsNone(data["old_price"])

    def test_get_old_price_with_active_promotion(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=20,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        product = Product.objects.create(
            name="SP", description="d", price=80000, category=self.category, promotion=promo,
        )
        data = ProductSerializer(product).data
        self.assertEqual(data["old_price"], 100000)
        self.assertIsNotNone(data["promotion"])

    def test_get_old_price_none_with_expired_promotion(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Old", discount_percent=20,
            start_date=today - timedelta(days=10), end_date=today - timedelta(days=1),
        )
        product = Product.objects.create(
            name="SP", description="d", price=80000, category=self.category, promotion=promo,
        )
        data = ProductSerializer(product).data
        self.assertIsNone(data["old_price"])
        self.assertIsNone(data["promotion"])

    def test_get_variants_effective_price_with_promo(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        product = Product.objects.create(
            name="SP", description="d", price=100000, category=self.category, promotion=promo,
        )
        color = Color.objects.create(name="Đen", code="#000")
        size = Size.objects.create(name="M")
        ProductVariant.objects.create(product=product, color=color, size=size, stock=1, price=100000)
        data = ProductSerializer(product).data
        self.assertEqual(data["variants"][0]["effective_price"], 90000)

    def test_validate_price_rejects_non_positive(self):
        s = ProductSerializer(data=self._base_payload(price=0))
        self.assertFalse(s.is_valid())

    def test_validate_promotion_id_rejects_inactive(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Old", discount_percent=10,
            start_date=today - timedelta(days=10), end_date=today - timedelta(days=1),
        )
        s = ProductSerializer(data=self._base_payload(promotion_id=promo.id))
        self.assertFalse(s.is_valid())

    def test_validate_promotion_id_accepts_active(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        s = ProductSerializer(data=self._base_payload(promotion_id=promo.id))
        self.assertTrue(s.is_valid(), s.errors)


class ProductCatalogViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(username="adm_cat", email="a@e.com", password="secret12345")
        self.admin.is_staff = True
        self.admin.save()
        Profile.objects.filter(user=self.admin).update(role=RoleChoices.ADMIN)

        self.staff = User.objects.create_user(username="staff_cat", email="s@e.com", password="secret12345")
        Profile.objects.filter(user=self.staff).update(role=RoleChoices.STAFF)

        self.active_cat = Category.objects.create(name="Active", description="", is_active=True)
        self.inactive_cat = Category.objects.create(name="Inactive", description="", is_active=False)

        self.product1 = Product.objects.create(
            name="Áo thun trắng", description="mô tả trắng",
            price=100000, category=self.active_cat,
        )
        self.product2 = Product.objects.create(
            name="Quần jean", description="mô tả jean",
            price=200000, category=self.active_cat,
        )
        self.color = Color.objects.create(name="Đen", code="#000")
        self.size = Size.objects.create(name="M")
        ProductVariant.objects.create(
            product=self.product1, color=self.color, size=self.size, stock=2,
        )

    @staticmethod
    def _rows(response_data):
        return response_data.get("results", response_data) if isinstance(response_data, dict) else response_data

    def test_anonymous_sees_only_active_categories(self):
        r = self.client.get("/api/products/categories/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        names = [c["name"] for c in self._rows(r.data)]
        self.assertIn("Active", names)
        self.assertNotIn("Inactive", names)

    def test_admin_sees_all_categories(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.get("/api/products/categories/")
        names = [c["name"] for c in self._rows(r.data)]
        self.assertIn("Inactive", names)

    def test_category_products_action(self):
        r = self.client.get(f"/api/products/categories/{self.active_cat.id}/products/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data), 2)

    def test_promotion_active_action(self):
        today = timezone.localdate()
        Promotion.objects.create(
            name="Đang chạy", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        Promotion.objects.create(
            name="Hết hạn", discount_percent=10,
            start_date=today - timedelta(days=10), end_date=today - timedelta(days=1),
        )
        r = self.client.get("/api/products/promotions/active/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in self._rows(r.data)]
        self.assertIn("Đang chạy", names)
        self.assertNotIn("Hết hạn", names)

    def test_product_search_filter(self):
        r = self.client.get("/api/products/", {"search": "trắng"})
        rows = self._rows(r.data)
        self.assertTrue(any("trắng" in p["name"] for p in rows))

    def test_product_category_filter(self):
        r = self.client.get("/api/products/", {"category": self.active_cat.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_product_promotion_filter(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        self.product1.promotion = promo
        self.product1.save()
        r = self.client.get("/api/products/", {"promotion": promo.id})
        rows = self._rows(r.data)
        self.assertEqual(len(rows), 1)

    def test_product_has_promotion_filter(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        self.product1.promotion = promo
        self.product1.save()
        r = self.client.get("/api/products/", {"has_promotion": "true"})
        rows = self._rows(r.data)
        self.assertEqual(len(rows), 1)

    def test_product_price_range_filter(self):
        r = self.client.get("/api/products/", {"min_price": 150000, "max_price": 250000})
        rows = self._rows(r.data)
        self.assertTrue(all(p["price"] >= 150000 for p in rows))

    def test_product_low_stock_filter(self):
        r = self.client.get("/api/products/", {"low_stock": "true", "stock_threshold": 5})
        rows = self._rows(r.data)
        self.assertTrue(any(p["id"] == self.product1.id for p in rows))

    def test_product_sort_rating_desc(self):
        r = self.client.get("/api/products/", {"sort": "rating-desc"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_product_sort_popular(self):
        r = self.client.get("/api/products/", {"sort": "popular"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_featured_action(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        self.product1.promotion = promo
        self.product1.save()
        r = self.client.get("/api/products/featured/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_hot_deals_action(self):
        today = timezone.localdate()
        promo = Promotion.objects.create(
            name="Sale", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
        )
        self.product1.promotion = promo
        self.product1.save()
        r = self.client.get("/api/products/hot_deals/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_new_arrivals_action(self):
        r = self.client.get("/api/products/new_arrivals/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_related_action(self):
        r = self.client.get(f"/api/products/{self.product1.id}/related/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [p["id"] for p in r.data]
        self.assertNotIn(self.product1.id, ids)

    def test_variant_queryset_filtered_by_product(self):
        r = self.client.get("/api/products/variants/", {"product": self.product1.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_variant_queryset_unfiltered(self):
        r = self.client.get("/api/products/variants/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_image_queryset_filtered_by_product(self):
        r = self.client.get("/api/products/images/", {"product": self.product1.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_image_queryset_unfiltered(self):
        r = self.client.get("/api/products/images/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_write_category(self):
        r = self.client.post("/api/products/categories/", {"name": "X", "description": ""})
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_staff_can_write_category(self):
        self.client.force_authenticate(user=self.staff)
        r = self.client.post("/api/products/categories/", {"name": "X staff", "description": ""})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_admin_can_write_category(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post("/api/products/categories/", {"name": "X", "description": ""})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
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
