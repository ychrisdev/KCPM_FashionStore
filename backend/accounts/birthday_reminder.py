"""Nhắc sinh nhật: gửi email trước 1 ngày (chạy qua management command + cron)."""

from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import BirthdayEmailTemplate, Profile
from core.permissions import RoleChoices
from orders.models import DiscountCode

logger = logging.getLogger(__name__)


def _is_placeholder_email(email: str) -> bool:
    e = (email or "").strip().lower()
    return not e or e.endswith("@placeholder.local")


def _tomorrow_local() -> date:
    return timezone.localdate() + timedelta(days=1)


def _is_anniversary_birthday(birth: date, on_day: date) -> bool:
    """True nếu `on_day` là ngày sinh nhật theo lịch (xử lý 29/2 năm không nhuận)."""
    bm, bd = birth.month, birth.day
    if bm == 2 and bd == 29:
        if calendar.isleap(on_day.year):
            return on_day.month == 2 and on_day.day == 29
        return on_day.month == 2 and on_day.day == 28
    return on_day.month == bm and on_day.day == bd


def iter_profiles_birthday_tomorrow() -> list[Profile]:
    """Khách có ngày sinh nhật vào ngày mai (theo timezone Django)."""
    t = _tomorrow_local()
    candidates = (
        Profile.objects.filter(
            birth_date__isnull=False,
            role=RoleChoices.CUSTOMER,
        )
        .exclude(user__email="")
        .select_related("user")
    )
    out: list[Profile] = []
    for p in candidates:
        bd = p.birth_date
        if bd and _is_anniversary_birthday(bd, t):
            out.append(p)
    return out


def build_birthday_template_context(
    *,
    display_name: str,
    birthday_date: date,
    email_subject: str,
    intro_text: str,
    cta_button_label: str,
    footer_text: str,
    discount_code_obj: Any | None,
    env_voucher_fallback: str,
) -> tuple[str, dict]:
    """
    Trả về (subject, context) cho template emails/birthday_reminder.{txt,html}.
    Ưu tiên mã giảm giá trong DB; nếu không có thì dùng chuỗi .env BIRTHDAY_VOUCHER_CODE.
    """
    shop_url = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    voucher_code = ""
    discount_percent: int | None = None
    discount_name = ""
    if discount_code_obj is not None:
        voucher_code = (discount_code_obj.code or "").strip()
        discount_percent = discount_code_obj.discount_percent
        discount_name = (discount_code_obj.name or "").strip()
    else:
        voucher_code = (env_voucher_fallback or "").strip()

    subject = (email_subject or "").strip() or (
        "[FashionStore] Sinh nhật của bạn — quà tri ân từ cửa hàng"
    )
    foot = (footer_text or "").strip() or (
        "Thư tự động — vui lòng không trả lời trực tiếp email này."
    )
    cta = (cta_button_label or "").strip() or "Vào FashionStore"
    products_url = f"{shop_url}/products"

    ctx = {
        "display_name": display_name,
        "birthday_date": birthday_date,
        "intro_text": intro_text or "",
        "voucher_code": voucher_code,
        "has_voucher_block": bool(voucher_code),
        "discount_percent": discount_percent,
        "discount_name": discount_name,
        "has_discount_percent": discount_percent is not None,
        "cta_button_label": cta,
        "footer_text": foot,
        "shop_url": shop_url,
        "products_url": products_url,
    }
    return subject, ctx


def render_birthday_email_bodies(ctx: dict, subject: str) -> tuple[str, str]:
    text_body = render_to_string("emails/birthday_reminder.txt", ctx).strip()
    html_body = render_to_string("emails/birthday_reminder.html", ctx).strip()
    return text_body, html_body


def birthday_email_from_template(
    *,
    display_name: str,
    birthday_date: date,
    template: BirthdayEmailTemplate | None = None,
    custom_discount: Any | None = None,
) -> tuple[str, str, str]:
    tmpl = template or BirthdayEmailTemplate.get_solo()
    env_fb = (getattr(settings, "BIRTHDAY_VOUCHER_CODE", "") or "").strip()
    
    dc = custom_discount if custom_discount else (tmpl.discount_code if getattr(tmpl, "discount_code_id", None) else None)
    
    subject, ctx = build_birthday_template_context(
        display_name=display_name,
        birthday_date=birthday_date,
        email_subject=tmpl.email_subject,
        intro_text=tmpl.intro_text,
        cta_button_label=tmpl.cta_button_label,
        footer_text=tmpl.footer_text,
        discount_code_obj=dc,
        env_voucher_fallback=env_fb if not dc else "",
    )
    text_body, html_body = render_birthday_email_bodies(ctx, subject)
    return subject, text_body, html_body


def send_birthday_reminder_emails(explain: list[str] | None = None) -> tuple[int, int]:
    """
    Gửi email nhắc (trước 1 ngày) cho khách có sinh nhật ngày mai.
    Trả về (đã gửi, bỏ qua/lỗi không tăng sent — chỉ đếm gửi thành công).
    Nếu truyền explain (list), append ly do bo qua (ASCII, cho console Windows).
    """
    def _note(msg: str) -> None:
        if explain is not None:
            explain.append(msg)

    if not getattr(settings, "BIRTHDAY_REMINDER_EMAIL_ENABLED", True):
        logger.info("birthday reminder: tắt trong cấu hình (BIRTHDAY_REMINDER_EMAIL_ENABLED)")
        _note("skip: BIRTHDAY_REMINDER_EMAIL_ENABLED is off")
        return 0, 0

    if not (getattr(settings, "EMAIL_HOST_USER", "") or "").strip():
        logger.warning(
            "birthday reminder: chưa cấu hình EMAIL_HOST_USER — không gửi email"
        )
        _note("skip: EMAIL_HOST_USER empty")
        return 0, 0

    tomorrow = _tomorrow_local()
    tmpl = BirthdayEmailTemplate.get_solo()

    sent = 0
    skipped = 0

    for profile in iter_profiles_birthday_tomorrow():
        uname = profile.user.get_username()
        if profile.birthday_reminder_sent_for_year == tomorrow.year:
            skipped += 1
            _note(
                f"skip user={uname}: already reminded for calendar year {tomorrow.year} "
                f"(clear Profile.birthday_reminder_sent_for_year to test again)"
            )
            continue

        user = profile.user
        to_email = (user.email or "").strip()
        if not to_email or _is_placeholder_email(to_email):
            skipped += 1
            _note(f"skip user={uname}: missing or placeholder email")
            continue

        display_name = (user.get_full_name() or "").strip() or user.username
        
        email_prefix = to_email.split('@')[0].upper()
        voucher_code = f"HBD_{email_prefix}"
        
        discount_percent = 10
        if getattr(tmpl, "discount_code_id", None) and tmpl.discount_code:
            discount_percent = tmpl.discount_code.discount_percent
            
        discount_code_obj, created = DiscountCode.objects.get_or_create(
            code=voucher_code,
            defaults={
                "name": f"Sinh nhật {display_name}",
                "discount_percent": discount_percent,
                "min_order_value": 0,
                "start_date": tomorrow,
                "end_date": tomorrow,
                "usage_limit": 1,
                "is_active": True,
                "used_count": 0,
            }
        )
        if not created:
            if discount_code_obj.start_date != tomorrow or discount_code_obj.end_date != tomorrow:
                discount_code_obj.start_date = tomorrow
                discount_code_obj.end_date = tomorrow
                discount_code_obj.used_count = 0
                discount_code_obj.usage_limit = 1
                discount_code_obj.is_active = True
                discount_code_obj.save(update_fields=["start_date", "end_date", "used_count", "usage_limit", "is_active"])

        try:
            subject, text_body, html_body = birthday_email_from_template(
                display_name=display_name,
                birthday_date=tomorrow,
                template=tmpl,
                custom_discount=discount_code_obj,
            )
        except Exception:
            logger.exception("birthday reminder: render template thất bại")
            skipped += 1
            _note(f"skip user={uname}: template render failed (see logs)")
            continue

        try:
            send_mail(
                subject=subject,
                message=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
                html_message=html_body,
            )
        except Exception:
            logger.exception("birthday reminder: gửi email tới %s thất bại", to_email)
            skipped += 1
            _note(f"skip user={uname}: send_mail failed for {to_email} (see logs)")
            continue

        Profile.objects.filter(pk=profile.pk).update(
            birthday_reminder_sent_for_year=tomorrow.year
        )
        sent += 1

    return sent, skipped
