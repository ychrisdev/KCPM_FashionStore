from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from products.models import Category, Color, Product, ProductVariant, Promotion, Size

from wallets.models import Wallet

from .models import DiscountCode, Order, OrderItem, ReturnRequest, Shipping


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
