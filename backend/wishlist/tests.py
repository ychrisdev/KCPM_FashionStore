from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Product
from wishlist.models import WishlistItem


class WishlistProductIdsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="wishuser", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Váy", description="")
        self.product1 = Product.objects.create(
            name="Váy hoa", description="", category=category, price=300000
        )
        self.product2 = Product.objects.create(
            name="Váy đen", description="", category=category, price=350000
        )

    def test_get_wishlist_items_empty(self):
        """Wishlist rỗng trả về danh sách trống"""
        res = self.client.get("/api/wishlist/items/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_get_wishlist_items_with_data(self):
        """Trả về đúng product_ids trong wishlist"""
        WishlistItem.objects.create(user=self.user, product=self.product1)
        res = self.client.get("/api/wishlist/items/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(self.product1.id, res.data.get("product_ids", []))

    def test_get_wishlist_unauthenticated(self):
        """User chưa đăng nhập bị từ chối"""
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/wishlist/items/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_wishlist_only_own_items(self):
        """User chỉ thấy wishlist của mình"""
        other_user = User.objects.create_user(username="other3", password="123456")
        WishlistItem.objects.create(user=other_user, product=self.product1)
        res = self.client.get("/api/wishlist/items/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.product1.id, res.data.get("product_ids", []))


class WishlistToggleViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="toggleuser", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Áo khoác", description="")
        self.product = Product.objects.create(
            name="Áo khoác test", description="", category=category, price=500000
        )

    def test_toggle_add_to_wishlist(self):
        """Toggle product chưa có → thêm vào wishlist"""
        res = self.client.post("/api/wishlist/toggle/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(
            WishlistItem.objects.filter(user=self.user, product=self.product).exists()
        )

    def test_toggle_remove_from_wishlist(self):
        """Toggle product đã có → xóa khỏi wishlist"""
        WishlistItem.objects.create(user=self.user, product=self.product)
        self.client.post("/api/wishlist/toggle/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertFalse(
            WishlistItem.objects.filter(user=self.user, product=self.product).exists()
        )

    def test_toggle_unauthenticated(self):
        """User chưa đăng nhập bị từ chối"""
        self.client.force_authenticate(user=None)
        res = self.client.post("/api/wishlist/toggle/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class WishlistSyncViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="syncuser", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Phụ kiện", description="")
        self.product1 = Product.objects.create(
            name="Túi xách", description="", category=category, price=600000
        )
        self.product2 = Product.objects.create(
            name="Thắt lưng", description="", category=category, price=150000
        )

    def test_sync_replaces_wishlist(self):
        """Sync xóa wishlist cũ và thay bằng danh sách mới"""
        WishlistItem.objects.create(user=self.user, product=self.product1)
        res = self.client.post("/api/wishlist/sync/", {
            "product_ids": [self.product2.id],
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(
            WishlistItem.objects.filter(user=self.user, product=self.product1).exists()
        )
        self.assertTrue(
            WishlistItem.objects.filter(user=self.user, product=self.product2).exists()
        )

    def test_sync_with_empty_list_clears_wishlist(self):
        """Sync với danh sách rỗng → xóa toàn bộ wishlist"""
        WishlistItem.objects.create(user=self.user, product=self.product1)
        res = self.client.post("/api/wishlist/sync/", {
            "product_ids": [],
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 0)

    def test_sync_ignores_nonexistent_products(self):
        """Sync với product_id không tồn tại thì bỏ qua, không lỗi"""
        res = self.client.post("/api/wishlist/sync/", {
            "product_ids": [99999],
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 0)

    def test_sync_invalid_format_rejected(self):
        """Gửi product_ids không phải list bị từ chối"""
        res = self.client.post("/api/wishlist/sync/", {
            "product_ids": "not-a-list",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sync_unauthenticated(self):
        """User chưa đăng nhập bị từ chối"""
        self.client.force_authenticate(user=None)
        res = self.client.post("/api/wishlist/sync/", {
            "product_ids": [self.product1.id],
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)