from datetime import datetime, time
from django.utils import timezone
from vouchers.models import Voucher  # sửa theo app của bạn


def generate_birthday_voucher(user, birthday_date):
    email = (user.email or "").strip().lower()

    # lấy phần trước @
    local_part = email.split("@")[0]

    code = f"HBD_{local_part}".upper()

    # thời gian bắt đầu & kết thúc trong ngày sinh nhật
    start_dt = timezone.make_aware(datetime.combine(birthday_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(birthday_date, time.max))

    # tránh tạo trùng nếu cron chạy lại
    voucher, created = Voucher.objects.get_or_create(
        code=code,
        defaults={
            "user": user,
            "discount_percent": 10,  # hoặc lấy từ template
            "usage_limit": 1,
            "used_count": 0,
            "is_active": True,
            "start_date": start_dt,
            "expiry_date": end_dt,
        },
    )

    return voucher