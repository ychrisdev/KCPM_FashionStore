from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from products.models import Category, Color, Product, ProductVariant, Size


class CartViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="cartuser", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Áo", description="")
        color = Color.objects.create(name="Đỏ", code="#FF0000")
        size = Size.objects.create(name="M", order=1)
        self.product = Product.objects.create(
            name="Áo thun test",
            description="Mô tả",
            category=category,
            price=200000,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=color,
            size=size,
            stock=10,
        )

    def test_get_cart_list_authenticated(self):
        """User đã đăng nhập lấy được danh sách cart"""
        Cart.objects.create(user=self.user)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_get_cart_list_unauthenticated(self):
        """User chưa đăng nhập bị từ chối"""
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_only_returns_own_carts(self):
        """User chỉ thấy cart của mình, không thấy cart người khác"""
        other_user = User.objects.create_user(username="other", password="123456")
        Cart.objects.create(user=self.user)
        Cart.objects.create(user=other_user)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)


class CartItemViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="itemuser", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Quần", description="")
        color = Color.objects.create(name="Xanh", code="#0000FF")
        size = Size.objects.create(name="L", order=2)
        self.product = Product.objects.create(
            name="Quần jean test",
            description="Mô tả",
            category=category,
            price=400000,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=color,
            size=size,
            stock=5,
        )

    def test_add_item_creates_cart_automatically(self):
        """Thêm item tự động tạo cart nếu chưa có"""
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_add_item_to_cart(self):
        """Thêm item vào cart thành công"""
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 2,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 1)

    def test_add_same_item_increases_quantity(self):
        """Thêm cùng 1 variant 2 lần thì quantity cộng dồn"""
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 2,
        }, format="json")
        item = CartItem.objects.get(cart__user=self.user, product=self.variant)
        self.assertEqual(item.quantity, 3)

    def test_get_cart_items_unauthenticated(self):
        """User chưa đăng nhập bị từ chối xem cart items"""
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/cart/cart-items/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_cart_items_only_own(self):
        """User chỉ thấy cart items của mình"""
        other_user = User.objects.create_user(username="other2", password="123456")
        other_cart = Cart.objects.create(user=other_user)
        CartItem.objects.create(cart=other_cart, product=self.variant, quantity=1)

        res = self.client.get("/api/cart/cart-items/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_delete_cart_item(self):
        """Xóa cart item thành công"""
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, product=self.variant, quantity=1)
        res = self.client.delete(f"/api/cart/cart-items/{item.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)
