"""Email thông báo đơn hàng: xác nhận đặt hàng, đang giao, hoàn tất trả hàng / hoàn tiền."""

import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _orders_page_url() -> str:
    base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    return f"{base}/orders"


def _fmt_vnd(value) -> str:
    if isinstance(value, Decimal):
        return f'{value:,.0f}'.replace(',', '.')
    return str(value)


def send_order_confirmation_email(order_id: int) -> None:
    if not getattr(settings, 'ORDER_CONFIRMATION_EMAIL_ENABLED', True):
        return

    from .models import Order, OrderItem

    try:
        order = (
            Order.objects.select_related('user')
            .get(pk=order_id)
        )
    except Order.DoesNotExist:
        logger.warning('send_order_confirmation_email: Order %s không tồn tại', order_id)
        return

    user = order.user
    to_email = (user.email or '').strip()
    if not to_email:
        logger.info('send_order_confirmation_email: User %s không có email, bỏ qua', user.pk)
        return

    try:
        shipping = order.shipping
    except Exception:
        shipping = None

    item_lines = []
    for item in OrderItem.objects.filter(order=order).select_related(
        'product__product', 'product__color', 'product__size'
    ):
        pv = item.product
        name = pv.product.name
        variant = f'{pv.color.name} / {pv.size.name}'
        unit = _fmt_vnd(item.price)
        item_lines.append(f'- {name} ({variant}) × {item.quantity} — {unit}đ / SP')

    ctx = {
        'username': user.get_username(),
        'order_id': order.id,
        'item_lines': item_lines,
        'items_text': '\n'.join(item_lines),
        'subtotal': _fmt_vnd(order.subtotal),
        'shipping_fee': _fmt_vnd(order.shipping_fee),
        'total': _fmt_vnd(order.total_price),
        'shipping_name': shipping.name if shipping else '',
        'shipping_phone': shipping.phone if shipping else '',
        'shipping_address': shipping.address if shipping else '',
        'shipping_note': (shipping.note or '').strip() if shipping else '',
    }

    try:
        text_body = render_to_string('emails/order_confirmation.txt', ctx)
    except Exception as e:
        logger.exception('Render template order_confirmation: %s', e)
        text_body = (
            f"Xin chào {ctx['username']},\n\n"
            f"Đơn #{order.id} đã được ghi nhận. Tổng: {ctx['total']}đ.\n"
        )

    subject = f'[FashionStore] Xác nhận đơn hàng #{order.id}'

    try:
        send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception('Gửi email xác nhận đơn #%s thất bại: %s', order_id, e)


def send_order_shipped_email(order_id: int) -> None:
    if not getattr(settings, "ORDER_SHIPPED_EMAIL_ENABLED", True):
        return

    from .models import Order

    try:
        order = Order.objects.select_related("user").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("send_order_shipped_email: Order %s không tồn tại", order_id)
        return

    user = order.user
    to_email = (user.email or "").strip()
    if not to_email:
        logger.info("send_order_shipped_email: User %s không có email, bỏ qua", user.pk)
        return

    ctx = {
        "username": user.get_username(),
        "order_id": order.id,
        "orders_url": _orders_page_url(),
    }

    try:
        text_body = render_to_string("emails/order_shipped.txt", ctx)
    except Exception as e:
        logger.exception("Render template order_shipped: %s", e)
        text_body = (
            f"Xin chào {ctx['username']},\n\n"
            f"Đơn #{order.id} đang được giao đến bạn.\n"
            f"Xem chi tiết: {ctx['orders_url']}\n"
        )

    subject = f"[FashionStore] Đơn hàng #{order.id} đang được giao"

    try:
        send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Gửi email đang giao đơn #%s thất bại: %s", order_id, e)


def send_return_refund_completed_email(return_request_id: int) -> None:
    """Khi staff hoàn tất yêu cầu trả hàng (thường kèm xử lý hoàn tiền)."""
    if not getattr(settings, "RETURN_REFUND_EMAIL_ENABLED", True):
        return

    from .models import ReturnRequest

    try:
        rr = ReturnRequest.objects.select_related("user", "order").get(pk=return_request_id)
    except ReturnRequest.DoesNotExist:
        logger.warning(
            "send_return_refund_completed_email: ReturnRequest %s không tồn tại",
            return_request_id,
        )
        return

    user = rr.user
    to_email = (user.email or "").strip()
    if not to_email:
        logger.info(
            "send_return_refund_completed_email: User %s không có email, bỏ qua",
            user.pk,
        )
        return

    ctx = {
        "username": user.get_username(),
        "return_id": rr.id,
        "order_id": rr.order_id,
        "admin_note": (rr.admin_note or "").strip(),
        "orders_url": _orders_page_url(),
    }

    try:
        text_body = render_to_string("emails/return_refund_completed.txt", ctx)
    except Exception as e:
        logger.exception("Render template return_refund_completed: %s", e)
        text_body = (
            f"Xin chào {ctx['username']},\n\n"
            f"Yêu cầu trả hàng #{rr.id} (đơn #{rr.order_id}) đã được xử lý xong.\n"
        )

    subject = f"[FashionStore] Hoàn tất xử lý trả hàng — đơn #{rr.order_id}"

    try:
        send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception(
            "Gửi email hoàn trả/hoàn tiền cho yêu cầu #%s thất bại: %s",
            return_request_id,
            e,
        )
