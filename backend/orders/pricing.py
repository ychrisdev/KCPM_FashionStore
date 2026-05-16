from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework.exceptions import ValidationError

# Mien phi van chuyen tu muc nay (VND)
FREE_SHIPPING_THRESHOLD_VND = Decimal("500000")
SHIPPING_FEE_VND = Decimal("30000")


def unit_price_vnd(product) -> Decimal:
    base_price = product.price if product.price is not None else product.product.price
    p = Decimal(base_price)
    
    promo = getattr(product.product, "promotion", None)
    if promo and getattr(promo, "is_active", False):
        d = Decimal(promo.discount_percent)
        p = p * (Decimal(100) - d) / Decimal(100)
    return p.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def shipping_fee_vnd(subtotal: Decimal) -> Decimal:
    if subtotal >= FREE_SHIPPING_THRESHOLD_VND:
        return Decimal("0")
    return SHIPPING_FEE_VND


def normalize_discount_code(code: str | None) -> str:
    return (code or "").strip().upper()


def validate_discount_code_instance(discount_code, subtotal: Decimal) -> None:
    today = timezone.localdate()
    if not discount_code.is_active:
        raise ValidationError("Mã giảm giá hiện không khả dụng.")
    if discount_code.start_date > today:
        raise ValidationError("Mã giảm giá chưa đến ngày áp dụng.")
    if discount_code.end_date < today:
        raise ValidationError("Mã giảm giá đã hết hạn.")
    if discount_code.usage_limit is not None and discount_code.used_count >= discount_code.usage_limit:
        raise ValidationError("Mã giảm giá đã hết lượt sử dụng.")
    if subtotal < Decimal(discount_code.min_order_value):
        minimum = Decimal(discount_code.min_order_value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        raise ValidationError(f"Đơn hàng tối thiểu để dùng mã này là {minimum} VND.")


def discount_amount_vnd(subtotal: Decimal, discount_code) -> Decimal:
    raw = subtotal * Decimal(discount_code.discount_percent) / Decimal(100)
    return raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def build_order_totals(subtotal: Decimal, discount_code=None) -> tuple[Decimal, Decimal, Decimal]:
    shipping_fee = shipping_fee_vnd(subtotal)
    discount_amount = Decimal("0")
    if discount_code is not None:
        validate_discount_code_instance(discount_code, subtotal)
        discount_amount = discount_amount_vnd(subtotal, discount_code)
    total = subtotal - discount_amount + shipping_fee
    if total < 0:
        total = Decimal("0")
    return shipping_fee, discount_amount, total
