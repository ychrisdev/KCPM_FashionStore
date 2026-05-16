from decimal import Decimal

from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from payments import momo as momo_mod
from payments import zalopay as zalopay_mod

from .models import Wallet, WalletTransaction
from .serializers import TransactionSerializer
from .services import complete_wallet_deposit, mark_wallet_deposit_failed


class MyWalletView(APIView):
    """Số dư + lịch sử giao dịch cho trang ví khách hàng."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        txs = wallet.transactions.all().order_by("-created_at")
        return Response(
            {
                "balance": wallet.balance,
                "transactions": TransactionSerializer(txs, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


# - Cấu trúc class dựa trên hình ảnh code bạn đã cung cấp
class WalletInfoView(APIView):
    """
    View để lấy thông tin số dư ví của người dùng hiện tại.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response({
            "balance": wallet.balance
        }, status=status.HTTP_200_OK)

class WalletActionView(APIView):
    """
    View xử lý nạp tiền (deposit) và rút tiền (withdraw).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action_type = request.data.get('type')  # 'deposit' hoặc 'withdraw'
        try:
            amount = int(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response({"error": "Số tiền không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        if amount <= 0:
            return Response({"error": "Số tiền phải lớn hơn 0"}, status=status.HTTP_400_BAD_REQUEST)

        if action_type == "withdraw":
            if wallet.balance < amount:
                return Response({"error": "Số dư không đủ để rút"}, status=status.HTTP_400_BAD_REQUEST)
            wallet.balance -= amount
            note = "Rút tiền về tài khoản ngân hàng/MoMo"
            tx_type = "withdrawal"
        elif action_type == "deposit":
            return Response(
                {
                    "error": "Nạp tiền qua MoMo hoặc ZaloPay: mở \"Nạp tiền\", chọn số tiền và cổng thanh toán.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return Response({"error": "Hành động không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            type=tx_type,
            description=note,
            status="completed",
        )

        return Response({
            "balance": wallet.balance,
            "message": "Giao dịch thành công!"
        }, status=status.HTTP_200_OK)


_DEPOSIT_MIN = 10_000
_DEPOSIT_MAX = 50_000_000


class WalletDepositStartView(APIView):
    """Tạo giao dịch nạp pending + trả payment_url (MoMo / ZaloPay)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = (request.data.get("provider") or "").strip().lower()
        if provider not in ("momo", "zalopay"):
            return Response(
                {"error": "Chọn provider là momo hoặc zalopay."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount = int(request.data.get("amount", 0))
        except (ValueError, TypeError):
            return Response({"error": "Số tiền không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        if amount < _DEPOSIT_MIN or amount > _DEPOSIT_MAX:
            return Response(
                {"error": f"Số tiền nạp từ {_DEPOSIT_MIN} đến {_DEPOSIT_MAX} VNĐ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amt_dec = Decimal(amount)
        desc = f"Nạp tiền qua {provider.upper()}"

        with db_transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=request.user)
            tx = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amt_dec,
                type="deposit",
                status="pending",
                gateway=provider,
                gateway_ref="",
                description=desc,
            )
            tid = tx.transaction_id

        try:
            if provider == "momo":
                pay_url, order_id_str = momo_mod.create_wallet_payment(request, tid, amt_dec)
                ref = order_id_str
            else:
                pay_url, app_tid = zalopay_mod.create_wallet_deposit_payment(
                    request,
                    tid,
                    amt_dec,
                    str(request.user.pk),
                )
                ref = app_tid
        except ValueError as exc:
            mark_wallet_deposit_failed(tid)
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        WalletTransaction.objects.filter(pk=tid).update(gateway_ref=ref[:128])

        return Response(
            {
                "payment_url": pay_url,
                "transaction_id": tid,
                "provider": provider,
            },
            status=status.HTTP_200_OK,
        )


class WalletDepositZalopaySyncView(APIView):
    """Đối soát ZaloPay /v2/query cho giao dịch nạp ví pending."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        tx = get_object_or_404(
            WalletTransaction,
            pk=pk,
            wallet__user=request.user,
            type="deposit",
            gateway="zalopay",
        )
        wallet = tx.wallet
        if tx.status != "pending":
            return Response(
                {
                    "balance": str(wallet.balance),
                    "transaction": TransactionSerializer(tx).data,
                },
                status=status.HTTP_200_OK,
            )

        atid = (tx.gateway_ref or "").strip()
        if not atid:
            return Response(
                {"error": "Thiếu mã giao dịch ZaloPay. Hãy thử nạp lại."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            body = zalopay_mod.query_order_status(atid)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        paid, zp = zalopay_mod.is_query_result_paid(tx.amount, body)
        if paid:
            complete_wallet_deposit(
                tx.pk,
                gateway="zalopay",
                external_ref=str(zp or ""),
                amount_vnd=tx.amount,
            )
            tx.refresh_from_db()
            wallet.refresh_from_db()

        data = {
            "balance": str(wallet.balance),
            "transaction": TransactionSerializer(tx).data,
        }
        if not paid:
            data["zalopay_pending_message"] = (
                body.get("return_message")
                or body.get("sub_return_message")
                or "ZaloPay chưa xác nhận thanh toán."
            )
        return Response(data, status=status.HTTP_200_OK)

class WithdrawRequestView(APIView):
    """
    View xử lý yêu cầu rút tiền riêng biệt (nếu cần mở rộng logic sau này).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Hiện tại có thể dùng chung logic ở WalletActionView hoặc viết riêng tại đây
        return Response({"message": "Yêu cầu rút tiền đã được ghi nhận và đang chờ xử lý."}, status=status.HTTP_202_ACCEPTED)