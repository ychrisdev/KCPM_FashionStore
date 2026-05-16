from django.db import models
from django.contrib.auth.models import User

from core.permissions import RoleChoices


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.CHOICES,
        default=RoleChoices.CUSTOMER
    )
    google_id = models.CharField(max_length=255, blank=True, null=True)
    facebook_id = models.CharField(max_length=255, blank=True, null=True)
    # max_length: cột DB lưu path/URL; URL ảnh Facebook/Google có thể dài > 100 ký tự
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, max_length=1024
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Ngày sinh (năm dùng để hiển thị; nhắc theo tháng/ngày). Khách có thể để trống.
    birth_date = models.DateField(null=True, blank=True)
    # Năm dương lịch của lần sinh nhật sắp tới đã gửi email nhắc (tránh gửi trùng).
    birthday_reminder_sent_for_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.user.username


class BirthdayEmailTemplate(models.Model):
    """
    Cấu hình nội dung email nhắc sinh nhật (luôn dùng bản ghi pk=1).
    Liên kết mã giảm giá thật (orders.DiscountCode) hoặc để trống và dùng .env BIRTHDAY_VOUCHER_CODE.
    """

    email_subject = models.CharField(
        max_length=200,
        default="[FashionStore] Sinh nhật của bạn — quà tri ân từ cửa hàng",
    )
    intro_text = models.TextField(
        default=(
            "Ngày mai là sinh nhật của bạn — FashionStore xin gửi lời chúc "
            "sức khỏe và niềm vui!"
        ),
    )
    cta_button_label = models.CharField(max_length=80, default="Vào FashionStore")
    footer_text = models.TextField(
        blank=True,
        default="Thư tự động — vui lòng không trả lời trực tiếp email này.",
    )
    discount_code = models.ForeignKey(
        "orders.DiscountCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Mẫu email sinh nhật"

    def __str__(self):
        return "Birthday email template"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.select_related("discount_code").get_or_create(
            pk=1,
            defaults={},
        )
        return obj
