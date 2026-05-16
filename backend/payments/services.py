"""Cập nhật trạng thái thanh toán đơn hàng + gửi email xác nhận (một lần)."""

from __future__ import annotations

import logging

from django.db import transaction

from orders.mail import send_order_confirmation_email

logger = logging.getLogger(__name__)


def mark_order_paid(order_id: int, gateway_txn_id: str = "") -> bool:
    """
    Đặt gateway_status=paid, lưu mã giao dịch. Gửi email xác nhận đơn nếu chưa gửi (COD đã gửy lúc đặt).
    Trả True nếu vừa chuyển sang paid.
    """
    from orders.models import Order

    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            logger.warning("mark_order_paid: order %s không tồn tại", order_id)
            return False

        if order.gateway_status == "paid":
            return False

        if order.payment_method == "cod":
            return False

        order.gateway_status = "paid"
        order.status = "pending"
        if gateway_txn_id:
            tid = gateway_txn_id[:128]
            order.gateway_transaction_id = tid
        order.save(update_fields=["gateway_status", "status", "gateway_transaction_id"])

    transaction.on_commit(lambda: send_order_confirmation_email(order_id))
    return True


def mark_order_payment_failed(order_id: int) -> None:
    from django.db.models import F

    from orders.models import Order, OrderItem
    from products.models import ProductVariant

    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            return
        if order.gateway_status == "paid":
            return
        if order.gateway_status == "failed":
            return
        if order.payment_method == "cod":
            return

        prev_gateway = order.gateway_status
        update_fields = ["gateway_status"]
        order.gateway_status = "failed"

        # MoMo / ZaloPay: thanh toán không thành công → hủy đơn và hoàn tồn (giống POST cancel).
        if (
            order.payment_method in ("momo", "zalopay")
            and order.status == "pending"
            and prev_gateway == "pending"
        ):
            items = OrderItem.objects.filter(order=order)
            for item in items:
                ProductVariant.objects.filter(pk=item.product_id).update(
                    stock=F("stock") + item.quantity
                )
            order.status = "cancelled"
            update_fields.append("status")

        order.save(update_fields=update_fields)
