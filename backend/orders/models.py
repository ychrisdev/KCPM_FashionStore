from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from products.models import ProductVariant


class DiscountCode(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField()
    min_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-id",)

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"

    @property
    def is_usage_exhausted(self) -> bool:
        return self.usage_limit is not None and self.used_count >= self.usage_limit

    @property
    def effective_is_active(self) -> bool:
        today = timezone.localdate()
        return (
            self.is_active
            and self.start_date <= today <= self.end_date
            and not self.is_usage_exhausted
        )

    @property
    def status(self) -> str:
        return "active" if self.effective_is_active else "expired"

    @property
    def status_label(self) -> str:
        return "Dang hoat dong" if self.effective_is_active else "Het han"


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("shipping", "Shipping"),
        ("awaiting_confirmation", "Awaiting Confirmation"),
        ("returning", "Returning"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Tam tinh (hang), tinh tren server",
    )
    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Phi van chuyen (VND)",
    )
    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    discount_code_snapshot = models.CharField(max_length=50, blank=True, default="")
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="So tien giam tu ma giam gia (VND)",
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_by_user = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    PAYMENT_METHOD_CHOICES = (
        ("cod", "Thanh toán khi nhận hàng (COD)"),
        ("wallet", "Ví trên ứng dụng"),
        ("vnpay", "VNPay"),
        ("momo", "Ví MoMo"),
        ("zalopay", "Ví ZaloPay"),
    )
    payment_method = models.CharField(
        max_length=24,
        choices=PAYMENT_METHOD_CHOICES,
        default="cod",
    )
    gateway_transaction_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Mã giao dịch cổng (VNPay / MoMo / ZaloPay)",
    )

    GATEWAY_STATUS_CHOICES = (
        ("none", "Không qua cổng (COD)"),
        ("pending", "Chờ thanh toán"),
        ("paid", "Đã thanh toán"),
        ("failed", "Thanh toán thất bại"),
    )
    gateway_status = models.CharField(
        max_length=24,
        choices=GATEWAY_STATUS_CHOICES,
        default="none",
    )
    # Mã giao dịch app_trans_id gửi lên ZaloPay /v2/create (dùng cho /v2/query khi callback không tới được).
    zalopay_app_trans_id = models.CharField(
        max_length=48,
        blank=True,
        default="",
        help_text="app_trans_id gửi ZaloPay (dùng API query khi callback không tới server).",
    )
    # True khi tồn kho đã trừ tại checkout (luồng hiện tại trừ stock trước khi INSERT đơn)
    inventory_deducted = models.BooleanField(default=True)

    def __str__(self):
        return f"Order {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

class Shipping(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    note = models.TextField(blank=True, default="")

class ReturnRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Chờ duyệt"),
        ("approved", "Đã duyệt"),
        ("rejected", "Từ chối"),
        ("completed", "Hoàn thành"),
    )
    REASON_CHOICES = (
        ("wrong_item", "Sản phẩm sai"),
        ("damaged", "Sản phẩm hỏng/lỗi"),
        ("not_as_described", "Không đúng mô tả"),
        ("changed_mind", "Thay đổi quyết định"),
        ("other", "Lý do khác"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="return_requests")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="return_requests")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"ReturnRequest #{self.id} — Order #{self.order_id} ({self.status})"
class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã hoàn tiền'),
        ('rejected', 'Từ chối'),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)