"""
=============================================================
White-box Unit Tests — Chức năng Giỏ hàng (Cart)
=============================================================
Mục tiêu:
  - Statement Coverage  : bao phủ toàn bộ câu lệnh thực thi
  - Branch/Decision Coverage: bao phủ mọi nhánh True/False
 
File liên quan:
  - cart/views.py         → CartViewSet, CartItemViewSet.create()
  - cart/serializers.py   → CartItemSerializer.validate(), get_variant_info()
  - cart/models.py        → Cart (ForeignKey user, KHÔNG unique), CartItem
 
Lưu ý quan trọng về dead code:
  - Nhánh `else: item = serializer.save(cart=cart)` trong views.create()
    là DEAD CODE — không thể reach được vì:
      * Nếu product_variant_id gửi hợp lệ → attrs["product"] = variant (Branch A)
      * Nếu product_id gửi + có variant   → serializer.validate() set attrs["product"]
                                             → validated_data["product"] != None → Branch A
      * Nếu không gửi gì / product_id không có variant → ValidationError,
        không bao giờ đến được dòng `if variant` trong view
    → Branch B (else) không thể được cover bởi bất kỳ input hợp lệ nào.
 
Chạy lệnh:
  python manage.py test cart.tests_whitebox --verbosity=2
 
=============================================================
"""
 
from unittest.mock import MagicMock
 
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
 
from cart.models import Cart, CartItem
from cart.serializers import CartItemSerializer
from products.models import Category, Color, Product, ProductVariant, Size
 
 
# ─────────────────────────────────────────────────────────────
# HELPER: tạo ProductVariant nhanh, dùng chung toàn file
# ─────────────────────────────────────────────────────────────
def make_variant(product, color_name="Đỏ", size_name="M", stock=10, price=100000):
    """
    Tạo 1 ProductVariant mới.
    Dùng get_or_create cho Color/Size để tránh IntegrityError khi
    nhiều test trong cùng class gọi make_variant với cùng tên.
    """
    color, _ = Color.objects.get_or_create(name=color_name, defaults={"code": "#000"})
    size, _ = Size.objects.get_or_create(name=size_name, defaults={"order": 1})
    return ProductVariant.objects.create(
        product=product, color=color, size=size, stock=stock, price=price
    )
 
 
# =============================================================
# BASE SETUP dùng chung cho các nhóm CartItem test
# =============================================================
class CartItemBaseSetup(TestCase):
    """
    Tạo user, product, variant (stock=10) dùng chung.
    Các subclass gọi super().setUp() để kế thừa.
    """
 
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="ci_user", password="123456")
        self.client.force_authenticate(self.user)
 
        cat = Category.objects.create(name="Áo", description="")
        self.product = Product.objects.create(
            name="Áo test", description="", category=cat, price=100000
        )
        # variant chính: color=Đen, size=S, stock=10
        self.variant = make_variant(self.product, color_name="Đen", size_name="S", stock=10)
 
 
# =============================================================
# NHÓM 1: CartViewSet (ReadOnlyModelViewSet)
# Branches:
#   get_queryset() → filter(user=request.user)
#   permission_classes → IsAuthenticated
# =============================================================
class CartViewSetStatementTest(TestCase):
    """
    Statement Coverage cho CartViewSet:
      Bao phủ dòng: Cart.objects.filter(user=self.request.user).order_by(...)
      và dòng permission_classes = [IsAuthenticated]
    """
 
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="user_cart_sc", password="123456")
        self.client.force_authenticate(self.user)
 
    def test_SC01_get_cart_authenticated_executes_get_queryset(self):
        """
        [SC] GET /carts/ khi đã đăng nhập → 200.
        Thực thi dòng: Cart.objects.filter(user=self.request.user).order_by('-created_at')
        """
        Cart.objects.create(user=self.user)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
 
    def test_SC02_get_cart_unauthenticated_blocked_by_permission(self):
        """
        [SC] GET /carts/ khi chưa đăng nhập → 401.
        Thực thi dòng: permission_classes = [IsAuthenticated]
        """
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
 
 
class CartViewSetBranchTest(TestCase):
    """
    Branch Coverage cho CartViewSet.get_queryset():
      Branch A: user có ít nhất 1 Cart  → trả về list không rỗng
      Branch B: user không có Cart nào  → trả về list rỗng
      Branch C: filter đúng user, không lẫn Cart của người khác
    """
 
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="br_user_cv", password="123456")
        self.other = User.objects.create_user(username="br_other_cv", password="123456")
        self.client.force_authenticate(self.user)
 
    def test_BC01_user_has_cart_returns_non_empty_list(self):
        """[BC] Branch A: user có cart → response list có 1 phần tử"""
        Cart.objects.create(user=self.user)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
 
    def test_BC02_user_no_cart_returns_empty_list(self):
        """[BC] Branch B: user không có cart → response list rỗng"""
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)
 
    def test_BC03_get_queryset_filters_only_own_carts(self):
        """
        [BC] Branch C: filter(user=request.user) đúng owner.
        Tạo 1 cart cho user, 1 cho other → chỉ trả về 1 (của user hiện tại).
        """
        Cart.objects.create(user=self.user)
        Cart.objects.create(user=self.other)
        res = self.client.get("/api/cart/carts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
 
 
# =============================================================
# NHÓM 2: CartItemViewSet.create() — views.py
# Branch trong create():
#   Branch A  (if variant → True):
#     A1: created=True  → CartItem tạo mới với defaults={"quantity": qty}
#     A2: created=False → item.quantity += quantity; item.save()
#   Branch B  (else → variant=None): DEAD CODE — không thể reach
#     (serializer luôn set attrs["product"] hoặc raise ValidationError trước đó)
# =============================================================
class CartItemCreateStatementTest(CartItemBaseSetup):
    """
    Statement Coverage cho CartItemViewSet.create():
    Bao phủ toàn bộ câu lệnh trong hàm create():
      - cart, _ = Cart.objects.get_or_create(user=request.user)
      - serializer.is_valid(raise_exception=True)
      - variant = serializer.validated_data.get("product")
      - quantity = serializer.validated_data.get("quantity", 1)
      - item, created = CartItem.objects.get_or_create(...)
      - if not created: item.quantity += quantity; item.save()
      - return Response(..., status=HTTP_201_CREATED)
    """
 
    def test_SC03_create_new_item_executes_all_statements(self):
        """
        [SC] POST item mới → tất cả câu lệnh trong create() được thực thi.
        Cart tự tạo, CartItem được tạo, trả về 201.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.user).exists())
 
    def test_SC04_accumulate_executes_quantity_plus_equals_statement(self):
        """
        [SC] POST cùng variant 2 lần → dòng `item.quantity += quantity; item.save()` được thực thi.
        Kết quả: quantity = 2 + 3 = 5.
        """
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 2,
        }, format="json")
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 3,
        }, format="json")
        item = CartItem.objects.get(cart__user=self.user, product=self.variant)
        self.assertEqual(item.quantity, 5)
 
 
class CartItemCreateBranchTest(CartItemBaseSetup):
    """
    Branch Coverage cho CartItemViewSet.create():
 
    Branch A1 (if variant=True, created=True):
      → get_or_create tạo CartItem mới với defaults={"quantity": quantity}
 
    Branch A2 (if variant=True, created=False):
      → item.quantity += quantity; item.save()  [cộng dồn]
 
    Branch B (else: variant=None):
      → DEAD CODE: không thể reach.
        Khi gửi product_id hợp lệ, serializer.validate() set attrs["product"] = variant,
        nên validated_data["product"] luôn có giá trị → Branch A được chọn.
        Test BC06 dưới đây vẫn xác minh kết quả đúng (201) cho product_id path,
        nhưng thực tế đi qua Branch A chứ không phải Branch B.
    """
 
    def test_BC04_branch_A1_new_item_created_true(self):
        """
        [BC] Branch A1: gửi product_variant_id chưa có trong giỏ.
        get_or_create → created=True → CartItem tạo mới, quantity đúng.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 3,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 3)
        self.assertEqual(
            CartItem.objects.filter(cart__user=self.user, product=self.variant).count(), 1
        )
 
    def test_BC05_branch_A2_existing_item_created_false_accumulates(self):
        """
        [BC] Branch A2: gửi cùng product_variant_id lần 2.
        get_or_create → created=False → item.quantity += qty; item.save().
        Kết quả: quantity = 4 + 3 = 7, chỉ có 1 CartItem.
        """
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 4,
        }, format="json")
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 3,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 7)
        self.assertEqual(
            CartItem.objects.filter(cart__user=self.user, product=self.variant).count(), 1
        )
 
    def test_BC06_product_id_path_goes_through_branch_A_not_B(self):
        """
        [BC] Gửi product_id thay vì product_variant_id.
        serializer.validate() resolve product_id → variant, set attrs["product"].
        validated_data["product"] != None → Branch A (không phải Branch B/else).
        Branch B (else) là DEAD CODE trong codebase hiện tại.
        Kết quả: 201.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_id": self.product.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
 
 
# =============================================================
# NHÓM 3: CartItemSerializer.validate() — nhánh PATCH
# (self.instance is not None)
# Branch:
#   P0: self.instance is not None → True (PATCH) / False (POST)
#   P1: "quantity" in attrs → True / False
#   P2: q > variant.stock → True (raise 400) / False (pass)
# =============================================================
class CartItemPatchValidateBranchTest(CartItemBaseSetup):
    """
    Branch Coverage cho validate() khi self.instance is not None (PATCH):
      Branch P1-T + P2-F: quantity ≤ stock         → pass, 200
      Branch P1-T + P2-T: quantity > stock          → raise, 400
      Branch P1-T + biên: quantity = stock (Max)    → pass, 200
      Branch P1-T: quantity = 0 (min_value từ IntegerField) → 400
      Branch P1-F: PATCH không gửi quantity field   → skip stock check, 200
    """
 
    def setUp(self):
        super().setUp()
        cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=cart, product=self.variant, quantity=1
        )
 
    def test_BC07_patch_quantity_within_stock_branch_P2_false(self):
        """
        [BC] Branch P1-T, P2-F: PATCH quantity=5 ≤ stock=10.
        validate pass → 200, item.quantity cập nhật = 5.
        """
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {
            "quantity": 5,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 5)
 
    def test_BC08_patch_quantity_exceeds_stock_branch_P2_true(self):
        """
        [BC] Branch P1-T, P2-T: PATCH quantity=11 > stock=10.
        raise ValidationError → 400, response chứa key 'quantity'.
        """
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {
            "quantity": 11,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
 
    def test_BC09_patch_quantity_equal_stock_max_boundary_branch_P2_false(self):
        """
        [BC] Biên Max: PATCH quantity = stock = 10.
        Nhánh P2 → False (10 > 10 sai) → 200.
        """
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {
            "quantity": 10,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
 
    def test_BC10_patch_quantity_zero_fails_min_value_validator(self):
        """
        [BC] PATCH quantity=0 → IntegerField(min_value=1) reject trước validate() → 400.
        """
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {
            "quantity": 0,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
 
    def test_BC30_patch_without_quantity_field_branch_P1_false(self):
        """
        [BC] Branch P1-F: PATCH body rỗng {} → 'quantity' not in attrs.
        Bỏ qua hoàn toàn block stock check → return attrs → 200, không đổi quantity.
        """
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 1)  # quantity không đổi
 
 
# =============================================================
# NHÓM 4: CartItemSerializer.validate() — nhánh POST
# (self.instance is None)
# Branch:
#   V1: attrs.get("product") truthy     → skip product_id block
#   V2: attrs falsy + product_id + variant exists → attrs["product"] = variant
#   V3: attrs falsy + product_id + no variant  → raise "chưa có biến thể"
#   V4: attrs falsy + no product_id     → raise "Cần gửi..."
#   V5: variant not None, need ≤ stock  → pass (existing=None)
#   V5b: need = stock (Max boundary)    → pass
#   V6: need > stock, existing=None     → raise, no "Trong giỏ đã có"
#   V7: need > stock, existing!=None    → raise, kèm "Trong giỏ đã có X."
#   V7b: existing + qty = stock (Max)   → pass, quantity = stock
# =============================================================
class CartItemPostValidateBranchTest(CartItemBaseSetup):
 
    def test_BC11_branch_V1_product_variant_id_sets_attrs_product(self):
        """
        [BC] Branch V1: gửi product_variant_id hợp lệ.
        PrimaryKeyRelatedField(source='product') → attrs["product"] = variant instance.
        Bỏ qua toàn bộ block product_id → 201.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
 
    def test_BC12_branch_V2_product_id_with_existing_variant(self):
        """
        [BC] Branch V2: gửi product_id, product có variant.
        validate() → variant = ProductVariant.filter(product=...).first()
        → attrs["product"] = variant → 201.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_id": self.product.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
 
    def test_BC13_branch_V3_product_id_no_variant_raises_error(self):
        """
        [BC] Branch V3: gửi product_id nhưng product chưa có variant nào.
        validate() → filter → None → raise 400 'chưa có biến thể (variant)'.
        """
        cat2 = Category.objects.create(name="Phụ kiện", description="")
        empty_product = Product.objects.create(
            name="Sản phẩm trống", description="", category=cat2, price=50000
        )
        res = self.client.post("/api/cart/cart-items/", {
            "product_id": empty_product.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("product_id", res.data)
 
    def test_BC14_branch_V4_neither_variant_id_nor_product_id(self):
        """
        [BC] Branch V4: không gửi product_variant_id lẫn product_id.
        validate() → attrs.get("product") = None, product_id = None
        → raise 400 'Cần gửi product_variant_id hoặc product_id.'
        """
        res = self.client.post("/api/cart/cart-items/", {
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_BC15_branch_V5_stock_sufficient_no_existing(self):
        """
        [BC] Branch V5: quantity=5, stock=10, chưa có CartItem.
        existing=None, need=5 ≤ 10 → if need > stock → False → pass → 201.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 5,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 5)
 
    def test_BC16_branch_V5b_quantity_equal_stock_max_boundary(self):
        """
        [BC] Branch V5b (biên Max): quantity = stock = 10, chưa có CartItem.
        need=10, 10 > 10 → False → pass → 201.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 10,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 10)
 
    def test_BC17_branch_V6_stock_insufficient_no_existing_no_extra_msg(self):
        """
        [BC] Branch V6: quantity=11 > stock=10, chưa có CartItem (existing=None).
        need=11 > 10 → True → raise 400.
        extra = "" (vì existing=None) → message KHÔNG chứa 'Trong giỏ đã có'.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 11,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
        err_msg = str(res.data["quantity"])
        self.assertNotIn("Trong giỏ đã có", err_msg)
 
    def test_BC18_branch_V7_stock_insufficient_with_existing_has_extra_msg(self):
        """
        [BC] Branch V7: existing.quantity=8, gửi thêm quantity=5 → need=13 > stock=10.
        raise 400, extra = ' Trong giỏ đã có 8.' → message CHỨA chuỗi đó.
        """
        # Tạo CartItem sẵn quantity=8
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 8,
        }, format="json")
        # Gửi thêm 5 → 8+5=13 > 10
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 5,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        err_msg = str(res.data["quantity"])
        self.assertIn("Trong giỏ đã có 8", err_msg)
 
    def test_BC19_branch_V7b_accumulate_equal_stock_max_boundary(self):
        """
        [BC] Branch V7b (biên Max cộng dồn): existing=3 + qty=7 = stock=10.
        need=10, 10 > 10 → False → pass → 201, quantity = 10.
        """
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 3,
        }, format="json")
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 7,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 10)
 
    def test_BC31_post_quantity_zero_fails_min_value(self):
        """
        [BC] POST quantity=0 → IntegerField(min_value=1) reject → 400.
        (validate() không được gọi, field-level validation chặn trước)
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 0,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
 
    def test_BC32_post_quantity_string_fails_type_validation(self):
        """[BC] POST quantity='abc' → IntegerField type check → 400."""
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": "abc",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
 
    def test_BC33_post_quantity_negative_fails_min_value(self):
        """[BC] POST quantity=-1 → IntegerField(min_value=1) → 400."""
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": -1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
 
    def test_BC34_post_quantity_one_min_plus_boundary(self):
        """[BC] POST quantity=1 (Min+, biên hợp lệ nhỏ nhất) → 201."""
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 1)
 
 
# =============================================================
# NHÓM 5: DELETE CartItem — get_queryset() filter + permission
# Branch:
#   D1: id tồn tại, thuộc user hiện tại      → 204
#   D2: id không tồn tại trong DB            → 404
#   D3: id tồn tại nhưng thuộc user khác     → 404 (queryset filter loại ra)
#   D4: chưa đăng nhập                       → 401
# =============================================================
class CartItemDeleteBranchTest(CartItemBaseSetup):
 
    def setUp(self):
        super().setUp()
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart, product=self.variant, quantity=2
        )
 
    def test_BC20_delete_own_item_branch_D1_found_204(self):
        """[BC] Branch D1: DELETE CartItem của chính mình → 204, xóa khỏi DB."""
        res = self.client.delete(f"/api/cart/cart-items/{self.item.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=self.item.id).exists())
 
    def test_BC21_delete_nonexistent_id_branch_D2_not_found_404(self):
        """[BC] Branch D2: DELETE id=999999 không tồn tại → 404."""
        res = self.client.delete("/api/cart/cart-items/999999/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
 
    def test_BC22_delete_other_user_item_branch_D3_filtered_out_404(self):
        """
        [BC] Branch D3: DELETE CartItem của user khác.
        get_queryset() filter(cart__user=request.user) loại bỏ item đó → 404
        (không trả 403 — không lộ thông tin tồn tại).
        """
        other = User.objects.create_user(username="del_other", password="123456")
        other_cart = Cart.objects.create(user=other)
        other_item = CartItem.objects.create(
            cart=other_cart, product=self.variant, quantity=1
        )
        res = self.client.delete(f"/api/cart/cart-items/{other_item.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        # Xác nhận item của user khác KHÔNG bị xóa
        self.assertTrue(CartItem.objects.filter(id=other_item.id).exists())
 
    def test_BC35_delete_unauthenticated_branch_D4_returns_401(self):
        """[BC] Branch D4: DELETE không có token → IsAuthenticated chặn → 401."""
        self.client.force_authenticate(user=None)
        res = self.client.delete(f"/api/cart/cart-items/{self.item.id}/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
 
 
# =============================================================
# NHÓM 6: PATCH — get_queryset() filter + permission
# Branch:
#   Q1: CartItem thuộc user hiện tại          → 200
#   Q2: CartItem thuộc user khác              → 404
#   Q3: id không tồn tại                      → 404
#   Q4: chưa đăng nhập                        → 401
# =============================================================
class CartItemPatchPermissionTest(CartItemBaseSetup):
 
    def setUp(self):
        super().setUp()
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart, product=self.variant, quantity=1
        )
 
    def test_BC23_patch_own_item_branch_Q1_returns_200(self):
        """[BC] Branch Q1: PATCH CartItem của chính mình → 200."""
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {
            "quantity": 3,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 3)
 
    def test_BC24_patch_other_user_item_branch_Q2_returns_404(self):
        """
        [BC] Branch Q2: PATCH CartItem của user khác.
        get_queryset() loại ra → 404 (không phải 403).
        """
        other = User.objects.create_user(username="patch_other", password="123456")
        other_cart = Cart.objects.create(user=other)
        other_item = CartItem.objects.create(
            cart=other_cart, product=self.variant, quantity=1
        )
        res = self.client.patch(f"/api/cart/cart-items/{other_item.id}/", {
            "quantity": 2,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
 
    def test_BC25_patch_nonexistent_id_branch_Q3_returns_404(self):
        """[BC] Branch Q3: PATCH id=999999 không tồn tại → 404."""
        res = self.client.patch("/api/cart/cart-items/999999/", {
            "quantity": 2,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
 
    def test_BC36_patch_unauthenticated_branch_Q4_returns_401(self):
        """[BC] Branch Q4: PATCH không có token → 401."""
        self.client.force_authenticate(user=None)
        res = self.client.patch(f"/api/cart/cart-items/{self.item.id}/", {
            "quantity": 3,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
 
 
# =============================================================
# NHÓM 7: CartItemSerializer.get_variant_info()
# Branch:
#   I1: obj.product is None → return None
#   I2: obj.product exists  → return dict {color, size}
# =============================================================
class CartItemVariantInfoBranchTest(CartItemBaseSetup):
 
    def setUp(self):
        super().setUp()
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart, product=self.variant, quantity=1
        )
 
    def test_BC37_branch_I1_product_none_returns_none(self):
        """
        [BC] Branch I1: obj.product = None → get_variant_info() return None.
        Dùng MagicMock để force nhánh này (không thể tạo CartItem với product=None
        do FK constraint).
        """
        mock_item = MagicMock()
        mock_item.product = None
        serializer = CartItemSerializer()
        result = serializer.get_variant_info(mock_item)
        self.assertIsNone(result)
 
    def test_BC26_branch_I2_product_exists_returns_color_size_dict(self):
        """
        [BC] Branch I2: GET cart-items/{id} → variant_info chứa color và size.
        """
        res = self.client.get(f"/api/cart/cart-items/{self.item.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("variant_info", res.data)
        self.assertIn("color", res.data["variant_info"])
        self.assertIn("size", res.data["variant_info"])
 
    def test_BC27_branch_I2_variant_info_values_match_variant(self):
        """
        [BC] Branch I2: giá trị color.name='Đen', size.name='S'
        đúng với variant đã thêm vào giỏ.
        """
        res = self.client.get(f"/api/cart/cart-items/{self.item.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["variant_info"]["color"]["name"], "Đen")
        self.assertEqual(res.data["variant_info"]["size"]["name"], "S")
 
    def test_BC38_get_cart_items_only_returns_own_items(self):
        """
        [BC] GET /cart-items/ → chỉ trả về item của user hiện tại.
        item của user khác không xuất hiện trong response.
        """
        other = User.objects.create_user(username="vi_other", password="123456")
        other_cart = Cart.objects.create(user=other)
        other_item = CartItem.objects.create(
            cart=other_cart, product=self.variant, quantity=1
        )
        res = self.client.get("/api/cart/cart-items/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids_returned = [item["id"] for item in res.data]
        self.assertIn(self.item.id, ids_returned)
        self.assertNotIn(other_item.id, ids_returned)
 
    def test_BC39_get_cart_items_unauthenticated_returns_401(self):
        """[BC] GET /cart-items/ không có token → 401."""
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/cart/cart-items/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
 
    def test_BC40_post_cart_item_unauthenticated_returns_401(self):
        """[BC] POST /cart-items/ không có token → 401."""
        self.client.force_authenticate(user=None)
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
 
 
# =============================================================
# NHÓM 8: 2 Variant khác nhau → 2 CartItem riêng
# Xác nhận: get_or_create(cart, product=variant) với product khác nhau
# luôn created=True → không cộng dồn chéo giữa 2 variant
# =============================================================
class CartItemTwoVariantsBranchTest(CartItemBaseSetup):
 
    def setUp(self):
        super().setUp()
        # variant2: cùng product, cùng size S, khác màu (Xanh)
        self.variant2 = make_variant(self.product, color_name="Xanh", size_name="S", stock=10)
        # variant3: cùng product, cùng màu Đen, khác size (L)
        self.variant3 = make_variant(self.product, color_name="Đen", size_name="L", stock=10)
 
    def test_BC28_two_diff_color_variants_create_separate_cart_items(self):
        """
        [BC] 2 variant khác màu (Đen-S vs Xanh-S) → 2 CartItem riêng.
        get_or_create với product khác nhau → mỗi lần created=True.
        """
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant2.id,
            "quantity": 1,
        }, format="json")
        count = CartItem.objects.filter(cart__user=self.user).count()
        self.assertEqual(count, 2)
 
    def test_BC29_two_diff_size_variants_create_separate_cart_items(self):
        """
        [BC] 2 variant khác size (Đen-S vs Đen-L) → 2 CartItem riêng.
        """
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant3.id,
            "quantity": 1,
        }, format="json")
        count = CartItem.objects.filter(cart__user=self.user).count()
        self.assertEqual(count, 2)
 
    def test_BC41_two_variant_items_have_distinct_product_ids_and_correct_quantities(self):
        """
        [BC] 2 CartItem phải có product_id khác nhau và quantity đúng riêng biệt.
        Đảm bảo không bị merge/cộng dồn chéo.
        """
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 2,
        }, format="json")
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant2.id,
            "quantity": 3,
        }, format="json")
        items = CartItem.objects.filter(cart__user=self.user).order_by("id")
        self.assertEqual(items.count(), 2)
        self.assertNotEqual(items[0].product_id, items[1].product_id)
        quantities = set(items.values_list("quantity", flat=True))
        self.assertIn(2, quantities)
        self.assertIn(3, quantities)
 
 
# =============================================================
# NHÓM 9: Cart auto get_or_create trong views.create()
# Branch:
#   CA1: user chưa có Cart → get_or_create tạo mới (created=True)
#   CA2: user đã có Cart   → get_or_create dùng lại (created=False)
# Lưu ý: Cart.user là ForeignKey (KHÔNG unique) →
#   nếu có nhiều Cart cho cùng user, get_or_create có thể
#   raise MultipleObjectsReturned. Đây là bug tiềm ẩn trong design.
# =============================================================
class CartAutoCreateBranchTest(CartItemBaseSetup):
 
    def test_BC42_branch_CA1_cart_created_automatically(self):
        """
        [BC] Branch CA1: user chưa có Cart, gọi POST item.
        Cart.objects.get_or_create(user=...) → created=True → Cart mới được tạo.
        """
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)
 
    def test_BC43_branch_CA2_existing_cart_reused_not_duplicated(self):
        """
        [BC] Branch CA2: user đã có đúng 1 Cart.
        get_or_create(user=...) → created=False → Cart cũ được dùng lại.
        Sau POST, vẫn chỉ có đúng 1 Cart.
        """
        Cart.objects.create(user=self.user)
        self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)
 
 
# =============================================================
# NHÓM 10: Edge case — variant stock = 0
# Branch: need=1 > stock=0 → True → raise 400
# =============================================================
class CartItemZeroStockEdgeCaseTest(CartItemBaseSetup):
 
    def setUp(self):
        super().setUp()
        self.zero_variant = make_variant(
            self.product, color_name="Tím", size_name="XL", stock=0
        )
 
    def test_BC44_post_item_with_zero_stock_raises_400(self):
        """
        [BC] variant.stock=0, quantity=1 → need=1 > 0 → True → raise 400.
        Không thể thêm bất kỳ số lượng nào vào giỏ khi hết hàng.
        """
        res = self.client.post("/api/cart/cart-items/", {
            "product_variant_id": self.zero_variant.id,
            "quantity": 1,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res.data)
 