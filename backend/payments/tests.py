import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from payments.services import mark_order_paid, mark_order_payment_failed
from payments.views import (
    MomoNotifyView,
    MomoReturnView,
    VnpayIpnView,
    VnpayReturnView,
    ZalopayCallbackView,
)
from products.models import Category, Color, Product, ProductVariant, Size
from wallets.models import Wallet, WalletTransaction
from wallets.services import (
    complete_wallet_deposit,
    credit_order_refund_to_user_wallet,
    credit_refund_to_wallet,
    debit_wallet_for_order_payment,
    mark_wallet_deposit_failed,
)


class PaymentViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="payment_user",
            email="payment@example.com",
            password="123456",
        )
        self.client.force_authenticate(user=self.user)
        self.order = Order.objects.create(
            user=self.user,
            subtotal=Decimal("500000"),
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=Decimal("500000"),
            status="pending",
            payment_method="cod",
            gateway_status="none",
        )
        self.wallet, _ = Wallet.objects.get_or_create(
            user=self.user,
            defaults={"balance": Decimal("0")},
        )

    def test_retry_payment_cod_success(self):
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "cod"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment_method"], "cod")

    def test_retry_payment_wallet_success_when_balance_enough(self):
        self.wallet.balance = Decimal("500000")
        self.wallet.save(update_fields=["balance"])
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "wallet"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(self.order.payment_method, "wallet")
        self.assertEqual(self.order.gateway_status, "paid")
        self.assertEqual(self.wallet.balance, Decimal("0"))
        self.assertTrue(
            WalletTransaction.objects.filter(
                wallet=self.wallet,
                amount=Decimal("500000"),
                type="payment",
                status="completed",
            ).exists()
        )

    def test_retry_payment_wallet_failed_when_balance_not_enough(self):
        self.wallet.balance = Decimal("499999")
        self.wallet.save(update_fields=["balance"])
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "wallet"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Số dư ví không đủ", str(res.data))
        self.order.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertNotEqual(self.order.gateway_status, "paid")
        self.assertEqual(self.wallet.balance, Decimal("499999"))
        self.assertFalse(
            WalletTransaction.objects.filter(
                wallet=self.wallet,
                type="payment",
                status="completed",
            ).exists()
        )

    @patch("payments.vnpay.build_payment_url")
    def test_retry_payment_vnpay_success(self, mock_build_payment_url):
        mock_build_payment_url.return_value = "https://vnpay.vn/payment-demo"
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "vnpay"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("payment_url", res.data)

    @patch("payments.momo.create_payment")
    def test_retry_payment_momo_success(self, mock_create_payment):
        mock_create_payment.return_value = "https://momo.vn/payment-demo"
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "momo"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("payment_url", res.data)

    @patch("payments.zalopay.create_payment")
    def test_retry_payment_zalopay_success(self, mock_create_payment):
        mock_create_payment.return_value = (
            "https://zalopay.vn/payment-demo",
            "app_trans_id_demo",
        )
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "zalopay"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("payment_url", res.data)

    def test_retry_payment_invalid_method(self):
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "paypal"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    def test_retry_payment_order_not_pending(self):
        self.order.status = "shipping"
        self.order.save(update_fields=["status"])
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "cod"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    def test_retry_payment_order_already_paid(self):
        self.order.gateway_status = "paid"
        self.order.save(update_fields=["gateway_status"])
        res = self.client.post(
            f"/api/orders/orders/{self.order.id}/retry-payment/",
            {"payment_method": "cod"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    def test_retry_payment_other_user_order_forbidden(self):
        other_user = User.objects.create_user(
            username="other_payment_user",
            email="other_payment@example.com",
            password="123456",
        )
        other_order = Order.objects.create(
            user=other_user,
            subtotal=Decimal("500000"),
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=Decimal("500000"),
            status="pending",
            payment_method="cod",
            gateway_status="none",
        )
        res = self.client.post(
            f"/api/orders/orders/{other_order.id}/retry-payment/",
            {"payment_method": "cod"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", res.data)

    def test_retry_payment_order_not_found(self):
        res = self.client.post(
            "/api/orders/orders/999999/retry-payment/",
            {"payment_method": "cod"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", res.data)


class PaymentServiceTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payment_service_user",
            email="payment_service_user@example.com",
            password="123456",
        )
        self.category = Category.objects.create(name="Áo", description="")
        self.color = Color.objects.create(name="Đen", code="#000000")
        self.size = Size.objects.create(name="M")
        self.product = Product.objects.create(
            name="Áo test",
            description="Sản phẩm test",
            category=self.category,
            price=Decimal("100000"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=5,
        )

    def create_order(
        self,
        *,
        payment_method="vnpay",
        gateway_status="pending",
        status="pending",
        total_price=Decimal("100000"),
    ):
        return Order.objects.create(
            user=self.user,
            subtotal=total_price,
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=total_price,
            payment_method=payment_method,
            gateway_status=gateway_status,
            status=status,
        )

    def test_mark_order_paid_returns_false_when_order_not_exists(self):
        self.assertFalse(mark_order_paid(999999, "TXN_NOT_FOUND"))

    def test_mark_order_paid_returns_false_when_order_already_paid(self):
        order = self.create_order(gateway_status="paid")
        self.assertFalse(mark_order_paid(order.id, "TXN_ALREADY_PAID"))
        order.refresh_from_db()
        self.assertEqual(order.gateway_status, "paid")

    def test_mark_order_paid_returns_false_for_cod_order(self):
        order = self.create_order(payment_method="cod", gateway_status="none")
        self.assertFalse(mark_order_paid(order.id, "TXN_COD"))
        order.refresh_from_db()
        self.assertEqual(order.gateway_status, "none")

    @patch("payments.services.send_order_confirmation_email")
    def test_mark_order_paid_success_updates_gateway_status_and_transaction_id(self, mock_send_email):
        order = self.create_order(payment_method="vnpay", gateway_status="pending")
        result = mark_order_paid(order.id, "X" * 150)
        self.assertTrue(result)
        order.refresh_from_db()
        self.assertEqual(order.gateway_status, "paid")
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.gateway_transaction_id, "X" * 128)
        mock_send_email.assert_called_once_with(order.id)

    def test_mark_order_payment_failed_does_nothing_when_order_not_exists(self):
        self.assertIsNone(mark_order_payment_failed(999999))

    def test_mark_order_payment_failed_does_nothing_when_order_already_paid(self):
        order = self.create_order(payment_method="momo", gateway_status="paid")
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.assertEqual(order.gateway_status, "paid")
        self.assertEqual(order.status, "pending")

    def test_mark_order_payment_failed_does_nothing_when_gateway_already_failed(self):
        order = self.create_order(payment_method="momo", gateway_status="failed")
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.assertEqual(order.gateway_status, "failed")
        self.assertEqual(order.status, "pending")

    def test_mark_order_payment_failed_does_nothing_for_cod_order(self):
        order = self.create_order(payment_method="cod", gateway_status="none")
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.assertEqual(order.gateway_status, "none")
        self.assertEqual(order.status, "pending")

    def test_mark_order_payment_failed_for_momo_pending_cancels_order_and_restores_stock(self):
        order = self.create_order(payment_method="momo", gateway_status="pending", status="pending")
        OrderItem.objects.create(order=order, product=self.variant, quantity=2, price=Decimal("100000"))
        before_stock = self.variant.stock
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.gateway_status, "failed")
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(self.variant.stock, before_stock + 2)

    def test_mark_order_payment_failed_for_zalopay_pending_cancels_order_and_restores_stock(self):
        order = self.create_order(payment_method="zalopay", gateway_status="pending", status="pending")
        OrderItem.objects.create(order=order, product=self.variant, quantity=1, price=Decimal("100000"))
        before_stock = self.variant.stock
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.gateway_status, "failed")
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(self.variant.stock, before_stock + 1)

    def test_mark_order_payment_failed_for_vnpay_only_sets_gateway_failed(self):
        order = self.create_order(payment_method="vnpay", gateway_status="pending", status="pending")
        OrderItem.objects.create(order=order, product=self.variant, quantity=2, price=Decimal("100000"))
        before_stock = self.variant.stock
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.gateway_status, "failed")
        self.assertEqual(order.status, "pending")
        self.assertEqual(self.variant.stock, before_stock)

    def test_mark_order_payment_failed_for_momo_not_pending_does_not_cancel_or_restore_stock(self):
        order = self.create_order(payment_method="momo", gateway_status="none", status="pending")
        OrderItem.objects.create(order=order, product=self.variant, quantity=2, price=Decimal("100000"))
        before_stock = self.variant.stock
        mark_order_payment_failed(order.id)
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.gateway_status, "failed")
        self.assertEqual(order.status, "pending")
        self.assertEqual(self.variant.stock, before_stock)


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="wallet_service_user",
            email="wallet_service_user@example.com",
            password="123456",
        )

    def test_credit_refund_to_wallet_creates_wallet_and_refund_transaction(self):
        tx = credit_refund_to_wallet(self.user, Decimal("50000"), description="Hoàn tiền test")
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("50000"))
        self.assertEqual(tx.wallet, wallet)
        self.assertEqual(tx.amount, Decimal("50000"))
        self.assertEqual(tx.type, "refund")
        self.assertEqual(tx.status, "completed")
        self.assertEqual(tx.description, "Hoàn tiền test")

    def test_credit_refund_to_wallet_adds_to_existing_balance(self):
        Wallet.objects.create(user=self.user, balance=Decimal("100000"))
        tx = credit_refund_to_wallet(self.user, "25000", description="Hoàn tiền lần 2")
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("125000"))
        self.assertEqual(tx.amount, Decimal("25000"))

    def test_credit_refund_to_wallet_rejects_zero_amount(self):
        with self.assertRaisesMessage(ValueError, "Số tiền hoàn phải lớn hơn 0"):
            credit_refund_to_wallet(self.user, Decimal("0"), description="Không hợp lệ")

    def test_credit_refund_to_wallet_rejects_negative_amount(self):
        with self.assertRaisesMessage(ValueError, "Số tiền hoàn phải lớn hơn 0"):
            credit_refund_to_wallet(self.user, Decimal("-1000"), description="Không hợp lệ")

    def test_credit_order_refund_to_user_wallet_uses_order_description(self):
        tx = credit_order_refund_to_user_wallet(
            self.user,
            order_id=123,
            total_price=Decimal("70000"),
            reason_label="Hoàn tiền đơn hủy",
        )
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("70000"))
        self.assertEqual(tx.description, "Hoàn tiền đơn hủy — Đơn #123")
        self.assertEqual(tx.type, "refund")
        self.assertEqual(tx.status, "completed")

    def test_debit_wallet_for_order_payment_success(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("100000"))
        tx = debit_wallet_for_order_payment(self.user, order_id=55, amount=Decimal("60000"))
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("40000"))
        self.assertEqual(tx.wallet, wallet)
        self.assertEqual(tx.amount, Decimal("60000"))
        self.assertEqual(tx.type, "payment")
        self.assertEqual(tx.status, "completed")
        self.assertEqual(tx.description, "Thanh toán đơn hàng #55")

    def test_debit_wallet_for_order_payment_rejects_zero_amount(self):
        with self.assertRaisesMessage(ValueError, "Số tiền thanh toán không hợp lệ"):
            debit_wallet_for_order_payment(self.user, order_id=55, amount=Decimal("0"))

    def test_debit_wallet_for_order_payment_rejects_negative_amount(self):
        with self.assertRaisesMessage(ValueError, "Số tiền thanh toán không hợp lệ"):
            debit_wallet_for_order_payment(self.user, order_id=55, amount=Decimal("-1000"))

    def test_debit_wallet_for_order_payment_rejects_insufficient_balance(self):
        Wallet.objects.create(user=self.user, balance=Decimal("10000"))
        with self.assertRaisesMessage(ValueError, "Số dư ví không đủ để thanh toán đơn hàng này."):
            debit_wallet_for_order_payment(self.user, order_id=55, amount=Decimal("20000"))
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("10000"))
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_complete_wallet_deposit_returns_false_when_transaction_not_exists(self):
        result = complete_wallet_deposit(999999, gateway="momo", external_ref="MOMO_REF", amount_vnd=Decimal("100000"))
        self.assertFalse(result)

    def test_complete_wallet_deposit_returns_true_when_already_completed(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("100000"))
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=Decimal("50000"),
            type="deposit",
            status="completed",
            gateway="momo",
            gateway_ref="OLD_REF",
        )
        result = complete_wallet_deposit(tx.pk, gateway="momo", external_ref="MOMO_REF", amount_vnd=Decimal("50000"))
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertTrue(result)
        self.assertEqual(wallet.balance, Decimal("100000"))
        self.assertEqual(tx.status, "completed")

    def test_complete_wallet_deposit_returns_false_when_status_not_pending(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("0"))
        tx = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("50000"), type="deposit", status="failed", gateway="momo")
        result = complete_wallet_deposit(tx.pk, gateway="momo", amount_vnd=Decimal("50000"))
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertFalse(result)
        self.assertEqual(wallet.balance, Decimal("0"))
        self.assertEqual(tx.status, "failed")

    def test_complete_wallet_deposit_returns_false_when_gateway_mismatch(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("0"))
        tx = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("50000"), type="deposit", status="pending", gateway="momo")
        result = complete_wallet_deposit(tx.pk, gateway="zalopay", amount_vnd=Decimal("50000"))
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertFalse(result)
        self.assertEqual(wallet.balance, Decimal("0"))
        self.assertEqual(tx.status, "pending")

    def test_complete_wallet_deposit_returns_false_when_amount_mismatch(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("0"))
        tx = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("50000"), type="deposit", status="pending", gateway="momo")
        result = complete_wallet_deposit(tx.pk, gateway="momo", amount_vnd=Decimal("49999"))
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertFalse(result)
        self.assertEqual(wallet.balance, Decimal("0"))
        self.assertEqual(tx.status, "pending")

    def test_complete_wallet_deposit_success_adds_balance_and_marks_completed(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("10000"))
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=Decimal("50000"),
            type="deposit",
            status="pending",
            gateway="momo",
            gateway_ref="MOMO_ORDER_1",
        )
        result = complete_wallet_deposit(tx.pk, gateway=" MoMo ", external_ref="MOMO_CALLBACK_1", amount_vnd=Decimal("50000"))
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertTrue(result)
        self.assertEqual(wallet.balance, Decimal("60000"))
        self.assertEqual(tx.status, "completed")

    def test_complete_wallet_deposit_success_without_amount_check(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("10000"))
        tx = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("25000"), type="deposit", status="pending", gateway="zalopay")
        result = complete_wallet_deposit(tx.pk, gateway="zalopay", external_ref="ZLP_REF")
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertTrue(result)
        self.assertEqual(wallet.balance, Decimal("35000"))
        self.assertEqual(tx.status, "completed")

    def test_complete_wallet_deposit_returns_false_when_amount_invalid(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("0"))
        tx = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("50000"), type="deposit", status="pending", gateway="momo")
        result = complete_wallet_deposit(tx.pk, gateway="momo", amount_vnd="abc")
        wallet.refresh_from_db()
        tx.refresh_from_db()
        self.assertFalse(result)
        self.assertEqual(wallet.balance, Decimal("0"))
        self.assertEqual(tx.status, "pending")

    def test_mark_wallet_deposit_failed_updates_only_pending_deposit(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("0"))
        pending_deposit = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("50000"), type="deposit", status="pending", gateway="momo")
        completed_deposit = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("60000"), type="deposit", status="completed", gateway="momo")
        pending_refund = WalletTransaction.objects.create(wallet=wallet, amount=Decimal("70000"), type="refund", status="pending")
        mark_wallet_deposit_failed(pending_deposit.pk)
        mark_wallet_deposit_failed(completed_deposit.pk)
        mark_wallet_deposit_failed(pending_refund.pk)
        pending_deposit.refresh_from_db()
        completed_deposit.refresh_from_db()
        pending_refund.refresh_from_db()
        self.assertEqual(pending_deposit.status, "failed")
        self.assertEqual(completed_deposit.status, "completed")
        self.assertEqual(pending_refund.status, "pending")


@override_settings(FRONTEND_ORIGIN="http://localhost:5173")
class PaymentViewVnpayTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="vnpay_user",
            email="vnpay_user@example.com",
            password="123456",
        )

    def create_order(self, payment_method="vnpay", gateway_status="pending", total_price=Decimal("100000")):
        return Order.objects.create(
            user=self.user,
            subtotal=total_price,
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=total_price,
            payment_method=payment_method,
            gateway_status=gateway_status,
            status="pending",
        )

    @patch("payments.views.mark_order_paid")
    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_return_success(self, mock_verify, mock_mark_paid):
        order = self.create_order()
        mock_verify.return_value = (True, {"order_id": order.id, "transaction_no": "VNPAY_TXN_001", "raw": {"vnp_Amount": "10000000"}})
        response = VnpayReturnView.as_view()(self.factory.get("/api/payments/vnpay/return/"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=success", response["Location"])
        mock_mark_paid.assert_called_once_with(order.id, "VNPAY_TXN_001")

    @patch("payments.views.mark_order_payment_failed")
    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_return_failed(self, mock_verify, mock_mark_failed):
        order = self.create_order()
        mock_verify.return_value = (False, {"order_id": order.id, "response_code": "24", "reason": "cancelled"})
        response = VnpayReturnView.as_view()(self.factory.get("/api/payments/vnpay/return/"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])
        mock_mark_failed.assert_called_once_with(order.id)

    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_return_order_not_found(self, mock_verify):
        mock_verify.return_value = (True, {"order_id": 999999, "transaction_no": "VNPAY_TXN_404"})
        response = VnpayReturnView.as_view()(self.factory.get("/api/payments/vnpay/return/"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])

    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_return_wrong_payment_method(self, mock_verify):
        order = self.create_order(payment_method="cod", gateway_status="none")
        mock_verify.return_value = (True, {"order_id": order.id, "transaction_no": "VNPAY_TXN_WRONG"})
        response = VnpayReturnView.as_view()(self.factory.get("/api/payments/vnpay/return/"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])

    @patch("payments.views.mark_order_paid")
    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_ipn_success(self, mock_verify, mock_mark_paid):
        order = self.create_order()
        mock_verify.return_value = (True, {"order_id": order.id, "transaction_no": "VNPAY_IPN_001", "raw": {"vnp_Amount": "10000000"}})
        response = VnpayIpnView.as_view()(self.factory.get("/api/payments/vnpay/ipn/"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('"RspCode": "00"', response.content.decode())
        mock_mark_paid.assert_called_once_with(order.id, "VNPAY_IPN_001")

    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_ipn_invalid_signature(self, mock_verify):
        mock_verify.return_value = (False, {"reason": "bad_signature", "response_code": "97"})
        response = VnpayIpnView.as_view()(self.factory.get("/api/payments/vnpay/ipn/"))
        self.assertEqual(response.status_code, 400)
        self.assertIn('"RspCode": "97"', response.content.decode())

    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_ipn_order_not_found(self, mock_verify):
        mock_verify.return_value = (True, {"order_id": 999999})
        response = VnpayIpnView.as_view()(self.factory.get("/api/payments/vnpay/ipn/"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('"RspCode": "01"', response.content.decode())

    @patch("payments.views.vnpay.verify_callback")
    def test_vnpay_ipn_wrong_payment_method(self, mock_verify):
        order = self.create_order(payment_method="cod", gateway_status="none")
        mock_verify.return_value = (True, {"order_id": order.id})
        response = VnpayIpnView.as_view()(self.factory.get("/api/payments/vnpay/ipn/"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('"RspCode": "04"', response.content.decode())


@override_settings(FRONTEND_ORIGIN="http://localhost:5173")
class PaymentViewMomoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="momo_user",
            email="momo_user@example.com",
            password="123456",
        )

    def create_order(self, payment_method="momo", gateway_status="pending", total_price=Decimal("100000")):
        return Order.objects.create(
            user=self.user,
            subtotal=total_price,
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=total_price,
            payment_method=payment_method,
            gateway_status=gateway_status,
            status="pending",
        )

    def create_wallet_transaction(self, amount=Decimal("50000"), gateway="momo", status="pending"):
        wallet, _ = Wallet.objects.get_or_create(user=self.user, defaults={"balance": Decimal("0")})
        return WalletTransaction.objects.create(wallet=wallet, amount=amount, type="deposit", status=status, gateway=gateway)

    def test_momo_notify_invalid_json(self):
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data="{bad-json", content_type="application/json"))
        self.assertEqual(response.status_code, 400)

    @patch("payments.views.momo.verify_notify_signature", return_value=False)
    def test_momo_notify_bad_signature(self, mock_verify):
        body = {"orderId": "FS1_123", "resultCode": 0, "transId": "MOMO_BAD_SIG"}
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data=json.dumps(body), content_type="application/json"))
        self.assertEqual(response.status_code, 400)

    @patch("payments.views.mark_order_paid")
    @patch("payments.views.momo.verify_notify_signature", return_value=True)
    def test_momo_notify_order_success(self, mock_verify, mock_mark_paid):
        order = self.create_order()
        body = {"orderId": f"FS{order.id}_123", "resultCode": 0, "transId": "MOMO_TXN_001"}
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data=json.dumps(body), content_type="application/json"))
        self.assertEqual(response.status_code, 200)
        mock_mark_paid.assert_called_once_with(order.id, "MOMO_TXN_001")

    @patch("payments.views.mark_order_payment_failed")
    @patch("payments.views.momo.verify_notify_signature", return_value=True)
    def test_momo_notify_order_failed(self, mock_verify, mock_mark_failed):
        order = self.create_order()
        body = {"orderId": f"FS{order.id}_123", "resultCode": 1006, "transId": "MOMO_TXN_FAIL"}
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data=json.dumps(body), content_type="application/json"))
        self.assertEqual(response.status_code, 200)
        mock_mark_failed.assert_called_once_with(order.id)

    @patch("payments.views.momo.verify_notify_signature", return_value=True)
    def test_momo_notify_bad_order_id(self, mock_verify):
        body = {"orderId": "BAD_ORDER", "resultCode": 0, "transId": "MOMO_BAD"}
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data=json.dumps(body), content_type="application/json"))
        self.assertEqual(response.status_code, 400)

    @patch("wallets.services.complete_wallet_deposit", return_value=True)
    @patch("wallets.services.mark_wallet_deposit_failed")
    @patch("payments.views.momo.verify_notify_signature", return_value=True)
    def test_momo_notify_wallet_success(self, mock_verify, mock_mark_failed, mock_complete):
        tx = self.create_wallet_transaction()
        body = {"orderId": f"WALLET{tx.pk}_123", "resultCode": 0, "amount": "50000", "transId": "MOMO_WALLET_001"}
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data=json.dumps(body), content_type="application/json"))
        self.assertEqual(response.status_code, 200)
        mock_complete.assert_called_once()
        mock_mark_failed.assert_not_called()

    @patch("wallets.services.mark_wallet_deposit_failed")
    @patch("payments.views.momo.verify_notify_signature", return_value=True)
    def test_momo_notify_wallet_failed(self, mock_verify, mock_mark_failed):
        tx = self.create_wallet_transaction()
        body = {"orderId": f"WALLET{tx.pk}_123", "resultCode": 1006, "amount": "50000", "transId": "MOMO_WALLET_FAIL"}
        response = MomoNotifyView.as_view()(self.factory.post("/api/payments/momo/notify/", data=json.dumps(body), content_type="application/json"))
        self.assertEqual(response.status_code, 200)
        mock_mark_failed.assert_called_once_with(tx.pk)

    @patch("payments.views.mark_order_paid")
    def test_momo_return_order_success(self, mock_mark_paid):
        order = self.create_order()
        request = self.factory.get("/api/payments/momo/return/", {"orderId": f"FS{order.id}_123", "resultCode": "0", "amount": "100000", "transId": "MOMO_RETURN_001"})
        response = MomoReturnView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=success", response["Location"])
        mock_mark_paid.assert_called_once_with(order.id, "MOMO_RETURN_001")

    @patch("payments.views.mark_order_payment_failed")
    def test_momo_return_order_failed(self, mock_mark_failed):
        order = self.create_order()
        request = self.factory.get("/api/payments/momo/return/", {"orderId": f"FS{order.id}_123", "resultCode": "1006", "amount": "100000", "transId": "MOMO_RETURN_FAIL"})
        response = MomoReturnView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])
        mock_mark_failed.assert_called_once_with(order.id)

    def test_momo_return_order_not_found(self):
        response = MomoReturnView.as_view()(self.factory.get("/api/payments/momo/return/", {"orderId": "FS999999_123", "resultCode": "0", "amount": "100000"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])

    def test_momo_return_wrong_payment_method(self):
        order = self.create_order(payment_method="cod", gateway_status="none")
        response = MomoReturnView.as_view()(self.factory.get("/api/payments/momo/return/", {"orderId": f"FS{order.id}_123", "resultCode": "0", "amount": "100000"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])

    @patch("wallets.services.complete_wallet_deposit", return_value=True)
    def test_momo_return_wallet_success(self, mock_complete):
        tx = self.create_wallet_transaction()
        response = MomoReturnView.as_view()(self.factory.get("/api/payments/momo/return/", {"orderId": f"WALLET{tx.pk}_123", "resultCode": "0", "amount": "50000", "transId": "MOMO_WALLET_RETURN"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=success", response["Location"])
        mock_complete.assert_called_once()

    @patch("wallets.services.mark_wallet_deposit_failed")
    def test_momo_return_wallet_failed(self, mock_mark_failed):
        tx = self.create_wallet_transaction()
        response = MomoReturnView.as_view()(self.factory.get("/api/payments/momo/return/", {"orderId": f"WALLET{tx.pk}_123", "resultCode": "1006", "amount": "50000"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response["Location"])
        mock_mark_failed.assert_called_once_with(tx.pk)


@override_settings(FRONTEND_ORIGIN="http://localhost:5173")
class PaymentViewZalopayTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="zalopay_user",
            email="zalopay_user@example.com",
            password="123456",
        )

    def create_order(self, payment_method="zalopay", gateway_status="pending", total_price=Decimal("100000")):
        return Order.objects.create(
            user=self.user,
            subtotal=total_price,
            shipping_fee=Decimal("0"),
            discount_amount=Decimal("0"),
            total_price=total_price,
            payment_method=payment_method,
            gateway_status=gateway_status,
            status="pending",
        )

    def create_wallet_transaction(self, amount=Decimal("50000"), gateway="zalopay", status="pending"):
        wallet, _ = Wallet.objects.get_or_create(user=self.user, defaults={"balance": Decimal("0")})
        return WalletTransaction.objects.create(wallet=wallet, amount=amount, type="deposit", status=status, gateway=gateway)

    def parse_json_response(self, response):
        return json.loads(response.content.decode("utf-8"))

    def callback_request(self):
        return self.factory.post(
            "/api/payments/zalopay/callback/",
            data=json.dumps({"data": "{}", "mac": "valid_mac"}),
            content_type="application/json",
        )

    def test_zalopay_callback_missing_data_or_mac(self):
        request = self.factory.post(
            "/api/payments/zalopay/callback/",
            data=json.dumps({}),
            content_type="application/json",
        )
        response = ZalopayCallbackView.as_view()(request)
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_code"], 2)

    @patch("payments.views.zalopay.verify_callback_mac", return_value=False)
    def test_zalopay_callback_invalid_mac(self, mock_verify):
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Invalid MAC")

    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_invalid_data(self, mock_parse, mock_verify):
        mock_parse.side_effect = json.JSONDecodeError("bad", "{}", 0)
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Invalid data")

    @patch("payments.views.zalopay.parse_order_id_from_app_trans_id", return_value=None)
    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id", return_value=None)
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_bad_app_trans_id(self, mock_parse, mock_verify, mock_wallet_id, mock_order_id):
        mock_parse.return_value = {"app_trans_id": "bad", "amount": "100000"}
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Bad app_trans_id")

    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id")
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_wallet_tx_not_found(self, mock_parse, mock_verify, mock_wallet_id):
        mock_wallet_id.return_value = 999999
        mock_parse.return_value = {
            "app_trans_id": "260702_w999999_ab",
            "amount": "50000",
            "zp_trans_id": "ZP_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Txn not found")

    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id")
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_wallet_amount_mismatch(self, mock_parse, mock_verify, mock_wallet_id):
        tx = self.create_wallet_transaction()
        mock_wallet_id.return_value = tx.pk
        mock_parse.return_value = {
            "app_trans_id": f"260702_w{tx.pk}_ab",
            "amount": "49999",
            "zp_trans_id": "ZP_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Amount mismatch")

    @patch("wallets.services.complete_wallet_deposit", return_value=True)
    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id")
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_wallet_success(self, mock_parse, mock_verify, mock_wallet_id, mock_complete):
        tx = self.create_wallet_transaction()
        mock_wallet_id.return_value = tx.pk
        mock_parse.return_value = {
            "app_trans_id": f"260702_w{tx.pk}_ab",
            "amount": "50000",
            "zp_trans_id": "ZP_WALLET_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_code"], 1)
        mock_complete.assert_called_once()

    @patch("payments.views.zalopay.parse_order_id_from_app_trans_id")
    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id", return_value=None)
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_order_not_found(self, mock_parse, mock_verify, mock_wallet_id, mock_order_id):
        mock_order_id.return_value = 999999
        mock_parse.return_value = {
            "app_trans_id": "260702_999999_ab",
            "amount": "100000",
            "zp_trans_id": "ZP_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Order not found")

    @patch("payments.views.zalopay.parse_order_id_from_app_trans_id")
    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id", return_value=None)
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_wrong_payment_method(self, mock_parse, mock_verify, mock_wallet_id, mock_order_id):
        order = self.create_order(payment_method="cod", gateway_status="none")
        mock_order_id.return_value = order.id
        mock_parse.return_value = {
            "app_trans_id": f"260702_{order.id}_ab",
            "amount": "100000",
            "zp_trans_id": "ZP_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Reject")

    @patch("payments.views.zalopay.parse_order_id_from_app_trans_id")
    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id", return_value=None)
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_order_amount_mismatch(self, mock_parse, mock_verify, mock_wallet_id, mock_order_id):
        order = self.create_order(total_price=Decimal("100000"))
        mock_order_id.return_value = order.id
        mock_parse.return_value = {
            "app_trans_id": f"260702_{order.id}_ab",
            "amount": "99999",
            "zp_trans_id": "ZP_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_message"], "Amount mismatch")

    @patch("payments.views.mark_order_paid")
    @patch("payments.views.zalopay.parse_order_id_from_app_trans_id")
    @patch("payments.views.zalopay.parse_wallet_tx_id_from_app_trans_id", return_value=None)
    @patch("payments.views.zalopay.verify_callback_mac", return_value=True)
    @patch("payments.views.zalopay.parse_callback_payload")
    def test_zalopay_callback_order_success(self, mock_parse, mock_verify, mock_wallet_id, mock_order_id, mock_mark_paid):
        order = self.create_order(total_price=Decimal("100000"))
        mock_order_id.return_value = order.id
        mock_parse.return_value = {
            "app_trans_id": f"260702_{order.id}_ab",
            "amount": "100000",
            "zp_trans_id": "ZP_ORDER_TXN",
        }
        response = ZalopayCallbackView.as_view()(self.callback_request())
        data = self.parse_json_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["return_code"], 1)
        mock_mark_paid.assert_called_once_with(order.id, "ZP_ORDER_TXN")
