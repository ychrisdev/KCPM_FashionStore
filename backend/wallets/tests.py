from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from wallets.models import Wallet, WalletTransaction


class MyWalletViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="walletuser", password="123456")
        self.client.force_authenticate(self.user)

    def test_get_wallet_creates_if_not_exist(self):
        """Lần đầu gọi tự tạo wallet với balance 0"""
        res = self.client.get("/api/wallets/my-wallet/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res.data["balance"])), Decimal("0"))

    def test_get_wallet_returns_balance(self):
        """Trả về đúng số dư hiện tại"""
        Wallet.objects.create(user=self.user, balance=Decimal("500000"))
        res = self.client.get("/api/wallets/my-wallet/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res.data["balance"])), Decimal("500000"))

    def test_get_wallet_returns_transactions(self):
        """Trả về danh sách giao dịch"""
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("100000"))
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=Decimal("100000"),
            type="deposit",
            status="completed",
        )
        res = self.client.get("/api/wallets/my-wallet/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["transactions"]), 1)

    def test_get_wallet_unauthenticated(self):
        """User chưa đăng nhập bị từ chối"""
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/wallets/my-wallet/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class WalletInfoViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="walletuser2", password="123456")
        self.client.force_authenticate(self.user)
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal("500000"))

    def test_withdraw_success(self):
        """Rút tiền thành công khi đủ số dư"""
        res = self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": 100000,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("400000"))

    def test_withdraw_insufficient_balance(self):
        """Rút tiền thất bại khi không đủ số dư"""
        res = self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": 999999,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_zero_amount_rejected(self):
        """Rút 0 đồng bị từ chối"""
        res = self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": 0,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_negative_amount_rejected(self):
        """Rút số âm bị từ chối"""
        res = self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": -1000,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_via_info_returns_error(self):
        """Nạp tiền qua /info/ trả về hướng dẫn dùng cổng thanh toán"""
        res = self.client.post("/api/wallets/action/", {
            "type": "deposit",
            "amount": 100000,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_action_type_rejected(self):
        """Action type không hợp lệ bị từ chối"""
        res = self.client.post("/api/wallets/action/", {
            "type": "hack",
            "amount": 100000,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_amount_format_rejected(self):
        """Amount không phải số bị từ chối"""
        res = self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": "abc",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_creates_transaction_record(self):
        """Rút tiền thành công tạo bản ghi WalletTransaction"""
        self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": 50000,
        }, format="json")
        self.assertTrue(
            WalletTransaction.objects.filter(
                wallet=self.wallet,
                type="withdrawal",
                status="completed",
            ).exists()
        )

    def test_unauthenticated_cannot_access(self):
        """User chưa đăng nhập bị từ chối"""
        self.client.force_authenticate(user=None)
        res = self.client.post("/api/wallets/action/", {
            "type": "withdraw",
            "amount": 100000,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
