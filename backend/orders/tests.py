from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from products.models import Category, Color, Product, ProductVariant, Promotion, Size
from wallets.models import Wallet

from .models import DiscountCode, Order, OrderItem, ReturnRequest, Shipping
from .pricing import (
    build_order_totals,
    discount_amount_vnd,
    normalize_discount_code,
    shipping_fee_vnd,
    unit_price_vnd,
    validate_discount_code_instance,
)
from .serializers import DiscountCodeSerializer, OrderItemSerializer, OrderSerializer
def extract_results(data):
    """Trả list kết quả, hỗ trợ cả response có phân trang lẫn không phân trang."""
    if isinstance(data, dict):
        return data.get("results", [])
    return data
# ---------------------------------------------------------------------------
# Fake objects dùng cho pricing.unit_price_vnd (hàm chỉ dùng duck-typing,
# không cần model thật -> test nhanh, không phụ thuộc DB/products app)
# ---------------------------------------------------------------------------
class _FakePromo:
    def __init__(self, is_active, discount_percent=10):
        self.is_active = is_active
        self.discount_percent = discount_percent


class _FakeProduct:
    def __init__(self, price, promotion=None):
        self.price = price
        self.promotion = promotion


class _FakeVariant:
    def __init__(self, price, product):
        self.price = price
        self.product = product


# ===========================================================================
# 1. pricing.py
# ===========================================================================
class UnitPriceVndBranchTests(TestCase):
    """Nhánh trong unit_price_vnd()."""

    def test_variant_has_own_price_used_directly(self):
        product = _FakeProduct(price=Decimal("100000"))
        variant = _FakeVariant(price=Decimal("120000"), product=product)
        self.assertEqual(unit_price_vnd(variant), Decimal("120000"))

    def test_variant_price_none_falls_back_to_product_price(self):
        product = _FakeProduct(price=Decimal("100000"))
        variant = _FakeVariant(price=None, product=product)
        self.assertEqual(unit_price_vnd(variant), Decimal("100000"))

    def test_no_promotion_no_discount(self):
        product = _FakeProduct(price=Decimal("100000"), promotion=None)
        variant = _FakeVariant(price=None, product=product)
        self.assertEqual(unit_price_vnd(variant), Decimal("100000"))

    def test_promotion_exists_but_inactive_no_discount(self):
        promo = _FakePromo(is_active=False, discount_percent=50)
        product = _FakeProduct(price=Decimal("100000"), promotion=promo)
        variant = _FakeVariant(price=None, product=product)
        self.assertEqual(unit_price_vnd(variant), Decimal("100000"))

    def test_promotion_active_applies_discount_and_rounds_half_up(self):
        # 10001 * 50% = 5000.5 -> ROUND_HALF_UP -> 5001
        promo = _FakePromo(is_active=True, discount_percent=50)
        product = _FakeProduct(price=Decimal("10001"), promotion=promo)
        variant = _FakeVariant(price=None, product=product)
        self.assertEqual(unit_price_vnd(variant), Decimal("5001"))


class ShippingFeeVndBranchTests(TestCase):
    """Nhánh boundary tại FREE_SHIPPING_THRESHOLD_VND = 500000."""

    def test_subtotal_below_threshold_charges_fee(self):
        self.assertEqual(shipping_fee_vnd(Decimal("499999")), Decimal("30000"))

    def test_subtotal_exactly_threshold_is_free(self):
        self.assertEqual(shipping_fee_vnd(Decimal("500000")), Decimal("0"))

    def test_subtotal_above_threshold_is_free(self):
        self.assertEqual(shipping_fee_vnd(Decimal("600000")), Decimal("0"))


class NormalizeDiscountCodeBranchTests(TestCase):
    def test_none_returns_empty_string(self):
        self.assertEqual(normalize_discount_code(None), "")

    def test_empty_string_returns_empty_string(self):
        self.assertEqual(normalize_discount_code(""), "")

    def test_strips_and_uppercases(self):
        self.assertEqual(normalize_discount_code("  save15 "), "SAVE15")


class ValidateDiscountCodeInstanceBranchTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def _make(self, **overrides):
        defaults = dict(
            name="Test",
            code="TESTCODE",
            discount_percent=10,
            min_order_value=Decimal("0"),
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=1),
            is_active=True,
            usage_limit=None,
            used_count=0,
        )
        defaults.update(overrides)
        return DiscountCode.objects.create(**defaults)

    def test_inactive_code_raises(self):
        code = self._make(is_active=False)
        with self.assertRaises(ValidationError):
            validate_discount_code_instance(code, Decimal("100000"))

    def test_not_started_yet_raises(self):
        code = self._make(start_date=self.today + timedelta(days=1))
        with self.assertRaises(ValidationError):
            validate_discount_code_instance(code, Decimal("100000"))

    def test_already_expired_raises(self):
        code = self._make(end_date=self.today - timedelta(days=1))
        with self.assertRaises(ValidationError):
            validate_discount_code_instance(code, Decimal("100000"))

    def test_usage_limit_reached_raises(self):
        code = self._make(usage_limit=5, used_count=5)
        with self.assertRaises(ValidationError):
            validate_discount_code_instance(code, Decimal("100000"))

    def test_subtotal_below_minimum_raises(self):
        code = self._make(min_order_value=Decimal("200000"))
        with self.assertRaises(ValidationError):
            validate_discount_code_instance(code, Decimal("100000"))

    def test_all_conditions_pass_no_raise(self):
        code = self._make(min_order_value=Decimal("50000"))
        validate_discount_code_instance(code, Decimal("100000"))  # không raise


class DiscountAmountAndTotalsBranchTests(TestCase):
    def test_discount_amount_rounds_half_up(self):
        # 100001 * 33% = 33000.33 -> 33000
        code = DiscountCode.objects.create(
            name="R", code="R1", discount_percent=33,
            start_date=timezone.localdate(), end_date=timezone.localdate(),
        )
        self.assertEqual(discount_amount_vnd(Decimal("100001"), code), Decimal("33000"))

    def test_build_order_totals_without_discount_code(self):
        shipping, discount, total = build_order_totals(Decimal("400000"), None)
        self.assertEqual(shipping, Decimal("30000"))
        self.assertEqual(discount, Decimal("0"))
        self.assertEqual(total, Decimal("430000"))

    def test_build_order_totals_with_valid_discount_code(self):
        code = DiscountCode.objects.create(
            name="S10", code="SAVE10", discount_percent=10,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=1),
        )
        shipping, discount, total = build_order_totals(Decimal("600000"), code)
        self.assertEqual(shipping, Decimal("0"))       # đủ ngưỡng free ship
        self.assertEqual(discount, Decimal("60000"))
        self.assertEqual(total, Decimal("540000"))

    def test_build_order_totals_negative_total_clamped_to_zero(self):
        # discount_percent > 100 chỉ có thể xảy ra nếu tạo thẳng qua model/ORM
        # (serializer đã chặn >100), nhưng đây là nhánh "if total < 0" trong pricing.py
        # cần được test để chứng minh code phòng thủ hoạt động đúng.
        code = DiscountCode.objects.create(
            name="Over", code="OVER200", discount_percent=200,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=1),
        )
        shipping, discount, total = build_order_totals(Decimal("600000"), code)
        self.assertEqual(total, Decimal("0"))


# ===========================================================================
# 2. models.py -> DiscountCode properties
# ===========================================================================
class DiscountCodeModelPropertyBranchTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def _make(self, **overrides):
        defaults = dict(
            name="P", code="PCODE", discount_percent=10,
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=1),
            is_active=True, usage_limit=None, used_count=0,
        )
        defaults.update(overrides)
        return DiscountCode.objects.create(**defaults)

    def test_is_usage_exhausted_false_when_no_limit(self):
        code = self._make(usage_limit=None, used_count=999)
        self.assertFalse(code.is_usage_exhausted)

    def test_is_usage_exhausted_false_when_under_limit(self):
        code = self._make(usage_limit=10, used_count=5)
        self.assertFalse(code.is_usage_exhausted)

    def test_is_usage_exhausted_true_when_reached(self):
        code = self._make(usage_limit=10, used_count=10)
        self.assertTrue(code.is_usage_exhausted)

    def test_effective_is_active_false_when_is_active_false(self):
        code = self._make(is_active=False)
        self.assertFalse(code.effective_is_active)
        self.assertEqual(code.status, "expired")
        self.assertEqual(code.status_label, "Het han")

    def test_effective_is_active_false_when_not_started(self):
        code = self._make(start_date=self.today + timedelta(days=1))
        self.assertFalse(code.effective_is_active)

    def test_effective_is_active_false_when_expired(self):
        code = self._make(end_date=self.today - timedelta(days=1))
        self.assertFalse(code.effective_is_active)

    def test_effective_is_active_false_when_usage_exhausted(self):
        code = self._make(usage_limit=1, used_count=1)
        self.assertFalse(code.effective_is_active)

    def test_effective_is_active_true_when_all_conditions_met(self):
        code = self._make()
        self.assertTrue(code.effective_is_active)
        self.assertEqual(code.status, "active")
        self.assertEqual(code.status_label, "Dang hoat dong")


# ===========================================================================
# 3. serializers.py
# ===========================================================================
class DiscountCodeSerializerBranchTests(TestCase):
    def test_validate_code_empty_after_strip_raises(self):
        serializer = DiscountCodeSerializer()
        with self.assertRaises(Exception):
            serializer.validate_code("   ")

    def test_validate_code_valid_uppercases(self):
        serializer = DiscountCodeSerializer()
        self.assertEqual(serializer.validate_code(" save20 "), "SAVE20")

    def test_validate_discount_percent_zero_raises(self):
        serializer = DiscountCodeSerializer()
        with self.assertRaises(Exception):
            serializer.validate_discount_percent(0)

    def test_validate_discount_percent_over_100_raises(self):
        serializer = DiscountCodeSerializer()
        with self.assertRaises(Exception):
            serializer.validate_discount_percent(101)

    def test_validate_discount_percent_valid_passes(self):
        serializer = DiscountCodeSerializer()
        self.assertEqual(serializer.validate_discount_percent(50), 50)

    def test_validate_start_after_end_raises(self):
        serializer = DiscountCodeSerializer()
        serializer.instance = None
        with self.assertRaises(Exception):
            serializer.validate({
                "start_date": timezone.localdate() + timedelta(days=5),
                "end_date": timezone.localdate(),
            })

    def test_validate_uses_instance_dates_when_attrs_missing(self):
        today = timezone.localdate()
        existing = DiscountCode.objects.create(
            name="X", code="XX", discount_percent=10,
            start_date=today, end_date=today + timedelta(days=10),
        )
        serializer = DiscountCodeSerializer()
        serializer.instance = existing
        # chỉ gửi end_date mới hợp lệ (>= start_date lấy từ instance) -> không raise
        result = serializer.validate({"end_date": today + timedelta(days=20)})
        self.assertIn("end_date", result)


class OrderSerializerValidateStatusBranchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="123456")

    def _order(self, status):
        return Order.objects.create(user=self.user, subtotal=0, total_price=0, status=status)

    def test_no_instance_returns_value_unchanged(self):
        serializer = OrderSerializer()
        self.assertEqual(serializer.validate_status("shipping"), "shipping")

    def test_same_status_as_current_returns_value(self):
        order = self._order("pending")
        serializer = OrderSerializer(instance=order)
        self.assertEqual(serializer.validate_status("pending"), "pending")

    def test_terminal_status_blocks_change(self):
        for terminal in ("completed", "cancelled", "returning"):
            order = self._order(terminal)
            serializer = OrderSerializer(instance=order)
            with self.assertRaises(Exception):
                serializer.validate_status("shipping")

    def test_non_terminal_status_allows_change(self):
        order = self._order("pending")
        serializer = OrderSerializer(instance=order)
        self.assertEqual(serializer.validate_status("shipping"), "shipping")


class OrderItemSerializerVariantInfoBranchTests(TestCase):
    def test_returns_none_when_no_product(self):
        serializer = OrderItemSerializer()
        fake_item = SimpleNamespace(product=None)
        self.assertIsNone(serializer.get_variant_info(fake_item))

    def test_returns_dict_when_product_present(self):
        category = Category.objects.create(name="Ao", description="")
        color = Color.objects.create(name="Do", code="#ff0000")
        size = Size.objects.create(name="S")
        product = Product.objects.create(name="Ao thun", description="", category=category, price=Decimal("100000"))
        variant = ProductVariant.objects.create(product=product, color=color, size=size, stock=1)
        user = User.objects.create_user(username="u2", password="123456")
        order = Order.objects.create(user=user, subtotal=0, total_price=0)
        item = OrderItem.objects.create(order=order, product=variant, quantity=1, price=Decimal("100000"))

        serializer = OrderItemSerializer()
        info = serializer.get_variant_info(item)
        self.assertEqual(info["color"]["name"], "Do")
        self.assertEqual(info["size"]["id"], size.id)


class OrderSerializerGetShippingBranchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", password="123456")

    def test_returns_none_when_shipping_does_not_exist(self):
        order = Order.objects.create(user=self.user, subtotal=0, total_price=0)
        serializer = OrderSerializer()
        self.assertIsNone(serializer.get_shipping(order))

    def test_returns_data_when_shipping_exists(self):
        order = Order.objects.create(user=self.user, subtotal=0, total_price=0)
        Shipping.objects.create(order=order, name="A", phone="0900000000", address="Somewhere")
        serializer = OrderSerializer()
        data = serializer.get_shipping(order)
        self.assertEqual(data["name"], "A")


# ===========================================================================
# 4. views.py -> OrderViewSet.checkout (toàn bộ nhánh)
# ===========================================================================
class CheckoutViewBranchTests(TestCase):
    CHECKOUT_URL = "/api/orders/orders/checkout/"

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="buyer", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Ao", description="")
        color = Color.objects.create(name="Den", code="#000000")
        size = Size.objects.create(name="M")
        self.product = Product.objects.create(
            name="Ao thun", description="", category=category, price=Decimal("200000"),
        )
        self.variant = ProductVariant.objects.create(product=self.product, color=color, size=size, stock=5)

        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.variant, quantity=2)

    def _payload(self, **overrides):
        data = {
            "name": "Nguyen Van A",
            "phone": "0909123456",
            "address": "123 Test Street",
        }
        data.update(overrides)
        return data

    # ---- validate input branches ----
    def test_missing_name_returns_400(self):
        response = self.client.post(self.CHECKOUT_URL, self._payload(name=""), format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_phone_returns_400(self):
        response = self.client.post(self.CHECKOUT_URL, self._payload(phone=""), format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_address_returns_400(self):
        response = self.client.post(self.CHECKOUT_URL, self._payload(address=""), format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_cart_item_ids_type_returns_400(self):
        response = self.client.post(
            self.CHECKOUT_URL, self._payload(cart_item_ids="not-a-list"), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_note_over_2000_chars_is_truncated_not_rejected(self):
        long_note = "x" * 2500
        response = self.client.post(self.CHECKOUT_URL, self._payload(note=long_note), format="json")
        self.assertEqual(response.status_code, 201)

    # ---- cart loading branches ----
    def test_empty_cart_returns_400(self):
        empty_user = User.objects.create_user(username="empty_buyer", password="123456")
        client = APIClient()
        client.force_authenticate(empty_user)
        response = client.post(self.CHECKOUT_URL, self._payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_selected_cart_item_ids_not_in_cart_returns_400(self):
        response = self.client.post(
            self.CHECKOUT_URL, self._payload(cart_item_ids=[999999]), format="json"
        )
        self.assertEqual(response.status_code, 400)

    # ---- stock branches ----
    def test_insufficient_stock_returns_400(self):
        self.cart_item.quantity = 999
        self.cart_item.save(update_fields=["quantity"])
        response = self.client.post(self.CHECKOUT_URL, self._payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_stock_exactly_equal_to_quantity_succeeds(self):
        self.variant.stock = 2
        self.variant.save(update_fields=["stock"])
        response = self.client.post(self.CHECKOUT_URL, self._payload(), format="json")
        self.assertEqual(response.status_code, 201)

    # ---- discount code branches ----
    def test_nonexistent_discount_code_returns_400(self):
        response = self.client.post(
            self.CHECKOUT_URL, self._payload(discount_code="NOTEXIST"), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_discount_code_applied(self):
        DiscountCode.objects.create(
            name="Giam10", code="SAVE10", discount_percent=10,
            min_order_value=Decimal("0"),
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=1),
        )
        response = self.client.post(
            self.CHECKOUT_URL, self._payload(discount_code="save10"), format="json"
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.discount_code_snapshot, "SAVE10")

    # ---- payment method branches ----
    def test_unsupported_payment_method_falls_back_to_cod(self):
        response = self.client.post(
            self.CHECKOUT_URL, self._payload(payment_method="bitcoin"), format="json"
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, "cod")
        self.assertEqual(order.gateway_status, "none")

    def test_cod_payment_success(self):
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="cod"), format="json")
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.gateway_status, "none")

    @patch("orders.views.debit_wallet_for_order_payment")
    def test_wallet_payment_success(self, mock_debit):
        mock_debit.return_value = None
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="wallet"), format="json")
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.gateway_status, "paid")
        mock_debit.assert_called_once()

    @patch("orders.views.debit_wallet_for_order_payment")
    def test_wallet_payment_insufficient_balance_returns_400(self, mock_debit):
        mock_debit.side_effect = ValueError("Số dư ví không đủ.")
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="wallet"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())  # transaction.atomic rollback

    @patch("payments.vnpay.build_payment_url")
    def test_vnpay_payment_success(self, mock_build_url):
        mock_build_url.return_value = "https://vnpay.example/pay?x=1"
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="vnpay"), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_url"], "https://vnpay.example/pay?x=1")

    @patch("payments.vnpay.build_payment_url")
    def test_vnpay_gateway_error_returns_503(self, mock_build_url):
        mock_build_url.side_effect = ValueError("VNPay config missing")
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="vnpay"), format="json")
        self.assertEqual(response.status_code, 503)
        # order đã được tạo trước khi gọi cổng thanh toán (nằm ngoài atomic block)
        self.assertTrue(Order.objects.exists())

    @patch("payments.momo.create_payment")
    def test_momo_payment_success(self, mock_create):
        mock_create.return_value = "https://momo.example/pay?x=1"
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="momo"), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_url"], "https://momo.example/pay?x=1")

    @patch("payments.momo.create_payment")
    def test_momo_gateway_error_returns_503(self, mock_create):
        mock_create.side_effect = ValueError("Momo config missing")
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="momo"), format="json")
        self.assertEqual(response.status_code, 503)

    @patch("payments.zalopay.create_payment")
    def test_zalopay_payment_success(self, mock_create):
        mock_create.return_value = ("https://zalopay.example/pay?x=1", "app_trans_123")
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="zalopay"), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_url"], "https://zalopay.example/pay?x=1")
        order = Order.objects.get()
        self.assertEqual(order.zalopay_app_trans_id, "app_trans_123")

    @patch("payments.zalopay.create_payment")
    def test_zalopay_gateway_error_returns_503(self, mock_create):
        mock_create.side_effect = ValueError("ZaloPay config missing")
        response = self.client.post(self.CHECKOUT_URL, self._payload(payment_method="zalopay"), format="json")
        self.assertEqual(response.status_code, 503)


# ===========================================================================
# OrderViewSet.confirm_received
# ===========================================================================
class ConfirmReceivedBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="owner_cr", password="123456")
        self.other = User.objects.create_user(username="other_cr", password="123456", is_staff=True)
        self.order = Order.objects.create(
            user=self.owner, subtotal=0, total_price=100000, status="awaiting_confirmation"
        )
 
    def _url(self, pk):
        return f"/api/orders/orders/{pk}/confirm-received/"
 
    def test_not_owner_returns_403(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_wrong_status_returns_400(self):
        self.order.status = "pending"
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.owner)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_success_marks_completed(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "completed")
        self.assertTrue(self.order.confirmed_by_user)
        self.assertIsNotNone(self.order.completed_at)
 
 
# ===========================================================================
# OrderViewSet.cancel
# ===========================================================================
class CancelBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="owner_cancel", password="123456")
        self.other = User.objects.create_user(username="other_cancel", password="123456", is_staff=True)
        category = Category.objects.create(name="C", description="")
        color = Color.objects.create(name="Den", code="#000")
        size = Size.objects.create(name="M")
        product = Product.objects.create(name="P", description="", category=category, price=Decimal("100000"))
        self.variant = ProductVariant.objects.create(product=product, color=color, size=size, stock=3)
        self.order = Order.objects.create(
            user=self.owner, subtotal=200000, total_price=200000, status="pending"
        )
        OrderItem.objects.create(order=self.order, product=self.variant, quantity=2, price=Decimal("100000"))
 
    def _url(self, pk):
        return f"/api/orders/orders/{pk}/cancel/"
 
    def test_not_owner_returns_403(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_not_pending_returns_400(self):
        self.order.status = "shipping"
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.owner)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_success_restocks_and_no_refund_when_not_paid(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")
        self.assertEqual(self.variant.stock, 5)  # 3 ton + 2 hoan lai
 
    @patch("orders.views.credit_order_refund_to_user_wallet")
    def test_success_refunds_wallet_when_gateway_paid(self, mock_credit):
        self.order.gateway_status = "paid"
        self.order.save(update_fields=["gateway_status"])
        self.client.force_authenticate(self.owner)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_credit.assert_called_once()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")
 
 
# ===========================================================================
# OrderViewSet.retry_payment
# ===========================================================================
class RetryPaymentBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="owner_retry", password="123456")
        self.other = User.objects.create_user(username="other_retry", password="123456", is_staff=True)
        self.order = Order.objects.create(
            user=self.owner, subtotal=100000, total_price=100000,
            status="pending", payment_method="cod", gateway_status="none",
        )
        self.client.force_authenticate(self.owner)
 
    def _url(self, pk):
        return f"/api/orders/orders/{pk}/retry-payment/"
 
    def test_not_owner_returns_403(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self._url(self.order.pk), {"payment_method": "vnpay"}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_order_not_pending_returns_400(self):
        self.order.status = "shipping"
        self.order.save(update_fields=["status"])
        response = self.client.post(self._url(self.order.pk), {"payment_method": "vnpay"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_already_paid_returns_400(self):
        self.order.gateway_status = "paid"
        self.order.save(update_fields=["gateway_status"])
        response = self.client.post(self._url(self.order.pk), {"payment_method": "vnpay"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_unsupported_payment_method_returns_400(self):
        response = self.client.post(self._url(self.order.pk), {"payment_method": "bitcoin"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    @patch("orders.views.debit_wallet_for_order_payment")
    def test_wallet_success(self, mock_debit):
        mock_debit.return_value = None
        response = self.client.post(self._url(self.order.pk), {"payment_method": "wallet"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.gateway_status, "paid")
        self.assertEqual(self.order.payment_method, "wallet")
 
    @patch("orders.views.debit_wallet_for_order_payment")
    def test_wallet_insufficient_balance_returns_400(self, mock_debit):
        mock_debit.side_effect = ValueError("So du vi khong du.")
        response = self.client.post(self._url(self.order.pk), {"payment_method": "wallet"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.gateway_status, "none")
 
    def test_same_payment_method_skips_update_branch(self):
        self.order.payment_method = "vnpay"
        self.order.save(update_fields=["payment_method"])
        with patch("payments.vnpay.build_payment_url", return_value="https://vnpay.example/x"):
            response = self.client.post(self._url(self.order.pk), {"payment_method": "vnpay"}, format="json")
        self.assertEqual(response.status_code, 200)
 
    @patch("payments.vnpay.build_payment_url")
    def test_vnpay_success(self, mock_build):
        mock_build.return_value = "https://vnpay.example/x"
        response = self.client.post(self._url(self.order.pk), {"payment_method": "vnpay"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["payment_url"], "https://vnpay.example/x")
 
    @patch("payments.vnpay.build_payment_url")
    def test_vnpay_gateway_error_returns_503(self, mock_build):
        mock_build.side_effect = ValueError("config missing")
        response = self.client.post(self._url(self.order.pk), {"payment_method": "vnpay"}, format="json")
        self.assertEqual(response.status_code, 503)
 
    @patch("payments.momo.create_payment")
    def test_momo_success(self, mock_create):
        mock_create.return_value = "https://momo.example/x"
        response = self.client.post(self._url(self.order.pk), {"payment_method": "momo"}, format="json")
        self.assertEqual(response.status_code, 200)
 
    @patch("payments.momo.create_payment")
    def test_momo_gateway_error_returns_503(self, mock_create):
        mock_create.side_effect = ValueError("config missing")
        response = self.client.post(self._url(self.order.pk), {"payment_method": "momo"}, format="json")
        self.assertEqual(response.status_code, 503)
 
    @patch("payments.zalopay.create_payment")
    def test_zalopay_success(self, mock_create):
        mock_create.return_value = ("https://zalopay.example/x", "app_trans_1")
        response = self.client.post(self._url(self.order.pk), {"payment_method": "zalopay"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.zalopay_app_trans_id, "app_trans_1")
 
    @patch("payments.zalopay.create_payment")
    def test_zalopay_gateway_error_returns_503(self, mock_create):
        mock_create.side_effect = ValueError("config missing")
        response = self.client.post(self._url(self.order.pk), {"payment_method": "zalopay"}, format="json")
        self.assertEqual(response.status_code, 503)
 
 
# ===========================================================================
# OrderViewSet.approve_refund
# ===========================================================================
class ApproveRefundBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username="staff_ar", password="123456", is_staff=True)
        self.owner = User.objects.create_user(username="owner_ar", password="123456")
        self.order = Order.objects.create(
            user=self.owner, subtotal=0, total_price=100000, status="shipping", gateway_status="paid"
        )
        self.client.force_authenticate(self.staff)
 
    def _url(self, pk):
        return f"/api/orders/orders/{pk}/approve_refund/"
 
    def test_already_refunded_returns_400(self):
        self.order.status = "refunded"
        self.order.save(update_fields=["status"])
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    @patch("orders.views.credit_order_refund_to_user_wallet")
    def test_success_marks_refunded(self, mock_credit):
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_credit.assert_called_once()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "refunded")
 
    @patch("orders.views.credit_order_refund_to_user_wallet")
    def test_unexpected_exception_returns_400(self, mock_credit):
        mock_credit.side_effect = Exception("boom")
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
 
# ===========================================================================
# OrderViewSet.zalopay_sync
# ===========================================================================
class ZalopaySyncBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="owner_zs", password="123456")
        self.other = User.objects.create_user(username="other_zs", password="123456", is_staff=True)
        self.order = Order.objects.create(
            user=self.owner, subtotal=0, total_price=100000,
            payment_method="zalopay", gateway_status="pending",
            zalopay_app_trans_id="260701_1_abc123",
        )
        self.client.force_authenticate(self.owner)
 
    def _url(self, pk):
        return f"/api/orders/orders/{pk}/zalopay-sync/"
 
    def test_not_owner_returns_403(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_not_zalopay_method_returns_400(self):
        self.order.payment_method = "cod"
        self.order.save(update_fields=["payment_method"])
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_already_paid_returns_current_data_without_query(self):
        self.order.gateway_status = "paid"
        self.order.save(update_fields=["gateway_status"])
        with patch("payments.zalopay.query_order_status") as mock_query:
            response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_query.assert_not_called()
 
    def test_missing_app_trans_id_returns_400(self):
        self.order.zalopay_app_trans_id = ""
        self.order.save(update_fields=["zalopay_app_trans_id"])
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    @patch("payments.zalopay.query_order_status")
    def test_query_gateway_error_returns_503(self, mock_query):
        mock_query.side_effect = ValueError("timeout")
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 503)
 
    @patch("payments.services.mark_order_paid")
    @patch("payments.zalopay.is_query_result_paid")
    @patch("payments.zalopay.query_order_status")
    def test_paid_result_marks_order_paid(self, mock_query, mock_is_paid, mock_mark_paid):
        mock_query.return_value = {"return_code": 1, "zp_trans_id": "zp123"}
        mock_is_paid.return_value = (True, "zp123")
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_mark_paid.assert_called_once_with(self.order.pk, "zp123")
 
    @patch("payments.zalopay.is_query_result_paid")
    @patch("payments.zalopay.query_order_status")
    def test_unpaid_result_returns_pending_message(self, mock_query, mock_is_paid):
        mock_query.return_value = {"return_code": 2, "return_message": "Chua thanh toan"}
        mock_is_paid.return_value = (False, "")
        response = self.client.post(self._url(self.order.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["zalopay_pending_message"], "Chua thanh toan")
 
 
# ===========================================================================
# ReturnRequestViewSet.create
# ===========================================================================
class ReturnRequestCreateBranchTests(TestCase):
    URL = "/api/orders/returns/"
 
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="buyer_rr", password="123456")
        self.other = User.objects.create_user(username="other_rr", password="123456")
        self.client.force_authenticate(self.user)
 
    def _order(self, **overrides):
        defaults = dict(user=self.user, subtotal=0, total_price=100000, status="shipping")
        defaults.update(overrides)
        return Order.objects.create(**defaults)
 
    def test_missing_order_id_returns_400(self):
        response = self.client.post(self.URL, {"reason": "changed_mind"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_invalid_order_id_type_returns_400(self):
        response = self.client.post(self.URL, {"order": "abc", "reason": "changed_mind"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_order_not_found_or_not_owned_returns_400(self):
        order = self._order(user=self.other)
        response = self.client.post(self.URL, {"order": order.pk, "reason": "changed_mind"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_order_status_not_eligible_returns_400(self):
        order = self._order(status="pending")
        response = self.client.post(self.URL, {"order": order.pk, "reason": "changed_mind"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_completed_order_past_return_window_returns_400(self):
        order = self._order(
            status="completed", confirmed_by_user=True,
            completed_at=timezone.now() - timedelta(days=3650),
        )
        response = self.client.post(self.URL, {"order": order.pk, "reason": "changed_mind"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_duplicate_request_returns_400(self):
        order = self._order(status="shipping")
        ReturnRequest.objects.create(order=order, user=self.user, reason="changed_mind")
        response = self.client.post(self.URL, {"order": order.pk, "reason": "damaged"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_success_creates_return_request(self):
        order = self._order(status="shipping")
        response = self.client.post(self.URL, {"order": order.pk, "reason": "changed_mind"}, format="json")
        self.assertEqual(response.status_code, 201)
 
 
# ===========================================================================
# ReturnRequestViewSet.approve / reject
# ===========================================================================
class ReturnRequestApproveRejectBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username="staff_rr2", password="123456", is_staff=True)
        self.buyer = User.objects.create_user(username="buyer_rr2", password="123456")
        self.order = Order.objects.create(user=self.buyer, subtotal=0, total_price=100000, status="shipping")
        self.rr = ReturnRequest.objects.create(order=self.order, user=self.buyer, reason="damaged")
 
    def test_approve_forbidden_for_non_staff(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(f"/api/orders/returns/{self.rr.pk}/approve/", {}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_approve_success_updates_order_status(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/orders/returns/{self.rr.pk}/approve/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.rr.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.rr.status, "approved")
        self.assertEqual(self.order.status, "returning")
 
    def test_approve_non_pending_returns_400(self):
        self.rr.status = "approved"
        self.rr.save(update_fields=["status"])
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/orders/returns/{self.rr.pk}/approve/", {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_reject_forbidden_for_non_staff(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(f"/api/orders/returns/{self.rr.pk}/reject/", {}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_reject_success_restores_order_status(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/orders/returns/{self.rr.pk}/reject/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.rr.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.rr.status, "rejected")
        self.assertEqual(self.order.status, "completed")
 
    def test_reject_non_pending_returns_400(self):
        self.rr.status = "rejected"
        self.rr.save(update_fields=["status"])
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/orders/returns/{self.rr.pk}/reject/", {}, format="json")
        self.assertEqual(response.status_code, 400)
 
 
# ===========================================================================
# ReturnRequestViewSet.complete
# ===========================================================================
class ReturnRequestCompleteBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username="staff_rr3", password="123456", is_staff=True)
        self.buyer = User.objects.create_user(username="buyer_rr3", password="123456")
        self.order = Order.objects.create(user=self.buyer, subtotal=0, total_price=100000, status="returning")
        self.rr = ReturnRequest.objects.create(
            order=self.order, user=self.buyer, reason="damaged", status="approved"
        )
        self.client.force_authenticate(self.staff)
 
    def _url(self, pk):
        return f"/api/orders/returns/{pk}/complete/"
 
    def test_forbidden_for_non_staff(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(self._url(self.rr.pk), {}, format="json")
        self.assertEqual(response.status_code, 403)
 
    def test_not_found_returns_404(self):
        response = self.client.post(self._url(999999), {}, format="json")
        self.assertEqual(response.status_code, 404)
 
    def test_not_approved_returns_400(self):
        self.rr.status = "pending"
        self.rr.save(update_fields=["status"])
        response = self.client.post(self._url(self.rr.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_order_already_refunded_returns_400(self):
        self.order.status = "refunded"
        self.order.save(update_fields=["status"])
        response = self.client.post(self._url(self.rr.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    @patch("orders.views.credit_order_refund_to_user_wallet")
    def test_success_marks_completed_and_refunded(self, mock_credit):
        response = self.client.post(self._url(self.rr.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_credit.assert_called_once()
        self.rr.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.rr.status, "completed")
        self.assertEqual(self.order.status, "refunded")


# ===========================================================================
# OrderViewSet.discount_preview
# ===========================================================================
class DiscountPreviewBranchTests(TestCase):
    URL = "/api/orders/orders/discount-preview/"
 
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="buyer_dp", password="123456")
        self.client.force_authenticate(self.user)
 
        category = Category.objects.create(name="Ao", description="")
        color = Color.objects.create(name="Den", code="#000")
        size = Size.objects.create(name="M")
        product = Product.objects.create(name="Ao", description="", category=category, price=Decimal("200000"))
        self.variant = ProductVariant.objects.create(product=product, color=color, size=size, stock=5)
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.variant, quantity=2)
 
    def test_invalid_cart_item_ids_type_returns_400(self):
        response = self.client.post(self.URL, {"cart_item_ids": "abc"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_empty_cart_returns_400(self):
        empty_user = User.objects.create_user(username="empty_dp", password="123456")
        client = APIClient()
        client.force_authenticate(empty_user)
        response = client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_nonexistent_discount_code_returns_400(self):
        response = self.client.post(self.URL, {"discount_code": "NOPE"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_invalid_discount_code_business_rule_returns_400(self):
        DiscountCode.objects.create(
            name="Expired", code="OLD10", discount_percent=10,
            start_date=timezone.localdate() - timedelta(days=10),
            end_date=timezone.localdate() - timedelta(days=1),
        )
        response = self.client.post(self.URL, {"discount_code": "old10"}, format="json")
        self.assertEqual(response.status_code, 400)
 
    def test_no_discount_code_returns_pricing_without_discount(self):
        response = self.client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["discount_code"], "")
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("400000"))
 
    def test_valid_discount_code_returns_discounted_pricing(self):
        DiscountCode.objects.create(
            name="Save10", code="SAVE10", discount_percent=10,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=1),
        )
        response = self.client.post(self.URL, {"discount_code": "save10"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["discount_code"], "SAVE10")
        self.assertEqual(Decimal(response.data["discount_amount"]), Decimal("40000"))
 
    def test_selected_cart_items_only(self):
        response = self.client.post(
            self.URL, {"cart_item_ids": [self.cart_item.id]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("400000"))
 
 
# ===========================================================================
# DiscountCodeViewSet.active
# ===========================================================================
class DiscountCodeActiveBranchTests(TestCase):
    URL = "/api/orders/discount-codes/active/"
 
    def setUp(self):
        self.client = APIClient()  # không cần đăng nhập - AllowAny
 
    def test_returns_only_currently_active_codes(self):
        today = timezone.localdate()
        DiscountCode.objects.create(
            name="Active", code="ACT1", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
            is_active=True,
        )
        DiscountCode.objects.create(
            name="Expired", code="EXP1", discount_percent=10,
            start_date=today - timedelta(days=10), end_date=today - timedelta(days=1),
            is_active=True,
        )
        DiscountCode.objects.create(
            name="Exhausted", code="EXH1", discount_percent=10,
            start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
            usage_limit=1, used_count=1,
        )
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        codes = {item["code"] for item in response.data}
        self.assertIn("ACT1", codes)
        self.assertNotIn("EXP1", codes)
        self.assertNotIn("EXH1", codes)
 
    def test_active_code_without_usage_limit_included(self):
        today = timezone.localdate()
        DiscountCode.objects.create(
            name="NoLimit", code="NOLIM", discount_percent=5,
            start_date=today, end_date=today, usage_limit=None,
        )
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        codes = {item["code"] for item in response.data}
        self.assertIn("NOLIM", codes)
 
 
# ===========================================================================
# OrderItemViewSet.get_queryset / get_permissions
# ===========================================================================
class OrderItemViewSetBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username="staff_oi", password="123456", is_staff=True)
        self.owner = User.objects.create_user(username="owner_oi", password="123456")
        self.other = User.objects.create_user(username="other_oi", password="123456")

        category = Category.objects.create(name="Ao", description="")
        color = Color.objects.create(name="Den", code="#000")
        size = Size.objects.create(name="M")
        product = Product.objects.create(name="Ao", description="", category=category, price=Decimal("100000"))
        self.variant = ProductVariant.objects.create(product=product, color=color, size=size, stock=5)

        self.order = Order.objects.create(user=self.owner, subtotal=0, total_price=100000)
        self.item = OrderItem.objects.create(
            order=self.order, product=self.variant, quantity=1, price=Decimal("100000")
        )

    def test_owner_sees_only_own_items(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/orders/order-items/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in extract_results(response.data)]
        self.assertIn(self.item.id, ids)

    def test_other_user_does_not_see_items(self):
        self.client.force_authenticate(self.other)
        response = self.client.get("/api/orders/order-items/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in extract_results(response.data)]
        self.assertNotIn(self.item.id, ids)

    def test_staff_sees_all_items(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/orders/order-items/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in extract_results(response.data)]
        self.assertIn(self.item.id, ids)

    def test_non_staff_cannot_delete(self):
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/orders/order-items/{self.item.id}/")
        self.assertEqual(response.status_code, 403)
# ===========================================================================
# ReturnRequestViewSet.get_queryset / get_permissions
# ===========================================================================
class ReturnRequestQuerysetBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username="staff_rrq", password="123456", is_staff=True)
        self.owner = User.objects.create_user(username="owner_rrq", password="123456")
        self.other = User.objects.create_user(username="other_rrq", password="123456")

        self.order = Order.objects.create(user=self.owner, subtotal=0, total_price=100000, status="shipping")
        self.rr = ReturnRequest.objects.create(
            order=self.order, user=self.owner, reason="damaged", status="pending"
        )

    def test_owner_sees_only_own_requests(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/orders/returns/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in extract_results(response.data)]
        self.assertIn(self.rr.id, ids)

    def test_other_user_does_not_see_requests(self):
        self.client.force_authenticate(self.other)
        response = self.client.get("/api/orders/returns/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in extract_results(response.data)]
        self.assertNotIn(self.rr.id, ids)

    def test_staff_sees_all_and_can_filter_by_status(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/orders/returns/?status=pending")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in extract_results(response.data)]
        self.assertIn(self.rr.id, ids)

        response2 = self.client.get("/api/orders/returns/?status=approved")
        ids2 = [row["id"] for row in extract_results(response2.data)]
        self.assertNotIn(self.rr.id, ids2)

    def test_non_staff_cannot_update(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/orders/returns/{self.rr.id}/", {"description": "x"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

class DiscountCodeCheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="buyer", password="123456")
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Ao", description="")
        promotion = Promotion.objects.create(
            name="Sale thuong",
            discount_percent=10,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=7),
        )
        color = Color.objects.create(name="Den", code="#000000")
        size = Size.objects.create(name="M")
        product = Product.objects.create(
            name="Ao thun",
            description="Demo",
            category=category,
            price=Decimal("300000"),
            promotion=promotion,
        )
        variant = ProductVariant.objects.create(product=product, color=color, size=size, stock=10)
        size_l = Size.objects.create(name="L")
        second_variant = ProductVariant.objects.create(product=product, color=color, size=size_l, stock=8)

        cart = Cart.objects.create(user=self.user)
        self.first_cart_item = CartItem.objects.create(cart=cart, product=variant, quantity=2)
        self.second_cart_item = CartItem.objects.create(cart=cart, product=second_variant, quantity=1)

        self.discount_code = DiscountCode.objects.create(
            name="Giam 15",
            code="SAVE15",
            discount_percent=15,
            min_order_value=Decimal("200000"),
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=7),
            is_active=True,
        )

    def test_discount_preview_returns_discount_amount(self):
        response = self.client.post("/api/orders/orders/discount-preview/", {"discount_code": "SAVE15"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["discount_code"], "SAVE15")
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("810000"))
        self.assertEqual(Decimal(response.data["discount_amount"]), Decimal("121500"))
        self.assertEqual(Decimal(response.data["shipping_fee"]), Decimal("0"))
        self.assertEqual(Decimal(response.data["total_price"]), Decimal("688500"))

    def test_discount_preview_supports_selected_cart_items(self):
        response = self.client.post(
            "/api/orders/orders/discount-preview/",
            {"discount_code": "SAVE15", "cart_item_ids": [self.first_cart_item.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("540000"))
        self.assertEqual(Decimal(response.data["discount_amount"]), Decimal("81000"))
        self.assertEqual(Decimal(response.data["total_price"]), Decimal("459000"))

    def test_checkout_persists_discount_code_and_discount_amount(self):
        response = self.client.post(
            "/api/orders/orders/checkout/",
            {
                "name": "Nguyen Van A",
                "phone": "0909123456",
                "address": "123 Test Street",
                "discount_code": "SAVE15",
                "cart_item_ids": [self.first_cart_item.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get()
        self.discount_code.refresh_from_db()

        self.assertEqual(order.discount_code_snapshot, "SAVE15")
        self.assertEqual(order.discount_amount, Decimal("81000"))
        self.assertEqual(order.shipping_fee, Decimal("0"))
        self.assertEqual(order.total_price, Decimal("459000"))
        self.assertEqual(self.discount_code.used_count, 1)
        self.assertFalse(CartItem.objects.filter(pk=self.first_cart_item.pk).exists())
        self.assertTrue(CartItem.objects.filter(pk=self.second_cart_item.pk).exists())


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ORDER_SHIPPED_EMAIL_ENABLED=True,
    RETURN_REFUND_EMAIL_ENABLED=True,
)
class OrderNotificationEmailTests(TransactionTestCase):
    def setUp(self):
        mail.outbox.clear()
        self.buyer = User.objects.create_user(
            username="buyer2",
            email="buyer2@example.com",
            password="123456",
        )
        self.staff = User.objects.create_user(
            username="staff_orders",
            email="staff@example.com",
            password="123456",
            is_staff=True,
        )

        category = Category.objects.create(name="Giay", description="")
        color = Color.objects.create(name="Trang", code="#fff")
        size = Size.objects.create(name="42")
        product = Product.objects.create(
            name="Giay chay bo",
            description="",
            category=category,
            price=Decimal("1500000"),
        )
        self.variant = ProductVariant.objects.create(
            product=product, color=color, size=size, stock=5
        )

        self.order = Order.objects.create(
            user=self.buyer,
            subtotal=Decimal("1500000"),
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=Decimal("1500000"),
            status="pending",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.variant,
            quantity=1,
            price=Decimal("1500000"),
        )
        Shipping.objects.create(
            order=self.order,
            name="Buyer Two",
            phone="0900000002",
            address="1 Test Road",
        )

    def test_patch_status_to_shipping_sends_email(self):
        client = APIClient()
        client.force_authenticate(self.staff)
        url = f"/api/orders/orders/{self.order.pk}/"
        response = client.patch(url, {"status": "shipping"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("đang được giao", mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, ["buyer2@example.com"])

    def test_return_complete_sends_refund_email(self):
        self.order.status = "shipping"
        self.order.save(update_fields=["status"])
        rr = ReturnRequest.objects.create(
            order=self.order,
            user=self.buyer,
            reason="changed_mind",
            description="",
            status="approved",
            admin_note="Da hoan tien.",
        )

        client = APIClient()
        client.force_authenticate(self.staff)
        url = f"/api/orders/returns/{rr.pk}/complete/"
        response = client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("trả hàng", mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, ["buyer2@example.com"])
        body = mail.outbox[0].body
        self.assertIn("Da hoan tien.", body)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "refunded")
        wallet = Wallet.objects.get(user=self.buyer)
        self.assertEqual(wallet.balance, self.order.total_price)
