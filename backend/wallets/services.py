"""Nghiệp vụ ví: hoàn tiền vào ví khách."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction

from .models import Wallet, WalletTransaction

logger = logging.getLogger(__name__)


def credit_refund_to_wallet(user: User, amount: Decimal | float | str, *, description: str) -> WalletTransaction:
    """
    Cộng số tiền hoàn vào ví của user, ghi giao dịch type=refund / completed.

    Nên gọi bên trong transaction.atomic() cùng khóa đơn hàng / yêu cầu trả hàng.
    """
    amt = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if amt <= 0:
        raise ValueError("Số tiền hoàn phải lớn hơn 0")

    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
    wallet.balance += amt
    wallet.save(update_fields=["balance"])
    return WalletTransaction.objects.create(
        wallet=wallet,
        amount=amt,
        type="refund",
        description=description,
        status="completed",
    )


def credit_order_refund_to_user_wallet(
    user: User,
    *,
    order_id: int,
    total_price: Decimal | float | str,
    reason_label: str,
) -> WalletTransaction:
    """Hoàn toàn bộ total_price của đơn vào ví user (mô tả có mã đơn)."""
    desc = f"{reason_label} — Đơn #{order_id}"
    return credit_refund_to_wallet(user, total_price, description=desc)


def debit_wallet_for_order_payment(
    user: User,
    *,
    order_id: int,
    amount: Decimal | float | str,
) -> WalletTransaction:
    """
    Trừ ví để thanh toán đơn (type=payment, completed).
    Gọi trong transaction.atomic() cùng khóa đơn hàng.
    """
    amt = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if amt <= 0:
        raise ValueError("Số tiền thanh toán không hợp lệ")

    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
    if wallet.balance < amt:
        raise ValueError("Số dư ví không đủ để thanh toán đơn hàng này.")

    wallet.balance -= amt
    wallet.save(update_fields=["balance"])
    return WalletTransaction.objects.create(
        wallet=wallet,
        amount=amt,
        type="payment",
        description=f"Thanh toán đơn hàng #{order_id}",
        status="completed",
    )


def complete_wallet_deposit(
    transaction_id: int,
    *,
    gateway: str,
    external_ref: str = "",
    amount_vnd: Decimal | None = None,
) -> bool:
    """
    Xác nhận nạp ví (pending → completed), cộng balance. Idempotent nếu đã completed.
    """
    gw = (gateway or "").strip().lower()
    with transaction.atomic():
        try:
            tx = (
                WalletTransaction.objects.select_for_update()
                .select_related("wallet")
                .get(pk=transaction_id, type="deposit")
            )
        except WalletTransaction.DoesNotExist:
            return False
        if tx.status == "completed":
            return True
        if tx.status != "pending":
            return False
        if (tx.gateway or "").strip().lower() != gw:
            logger.warning("complete_wallet_deposit gateway mismatch tx=%s", transaction_id)
            return False
        if amount_vnd is not None:
            try:
                if int(tx.amount.quantize(Decimal("1"))) != int(Decimal(amount_vnd).quantize(Decimal("1"))):
                    logger.warning("complete_wallet_deposit amount mismatch tx=%s", transaction_id)
                    return False
            except Exception:
                return False
        wallet = Wallet.objects.select_for_update().get(pk=tx.wallet_id)
        wallet.balance += tx.amount
        wallet.save(update_fields=["balance"])
        tx.status = "completed"
        tx.save(update_fields=["status"])
        if external_ref:
            logger.debug("complete_wallet_deposit tx=%s ref=%s", transaction_id, external_ref)
    return True


def mark_wallet_deposit_failed(transaction_id: int) -> None:
    WalletTransaction.objects.filter(pk=transaction_id, type="deposit", status="pending").update(status="failed")
