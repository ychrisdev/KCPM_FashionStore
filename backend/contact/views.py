from rest_framework import permissions, viewsets
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminOrStaff, is_staff
from .models import Contact, Feedback, Policy
from .serializers import ContactSerializer, FeedbackSerializer, PolicySerializer


class ContactMetaView(APIView):
    """Cấu hình hiển thị trang liên hệ: hotline, giờ làm việc, danh mục chủ đề (không cần DB)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "brand": "FashionStore",
                "hotline_display": "0964 942 121",
                "hotline_e164": "+84964942121",
                "email": "cskh@fashionstore.vn",
                "address": (
                    "70 Tô Ký, Phường Tân Chánh Hiệp, Quận 12, TP. Hồ Chí Minh"
                ),
                "hours": "Thứ Hai – Thứ Sáu: 8:30 – 17:30 (GMT+7). Thứ Bảy, Chủ nhật & ngày lễ: không làm việc tại văn phòng.",
                "response_note": (
                    "Chúng tôi phản hồi qua email trong 1–2 ngày làm việc. "
                    "Trường hợp khẩn về đơn đang giao, vui lòng gọi hotline."
                ),
                "stats": [
                    {"label": "Phản hồi email", "value": "1–2 ngày làm việc"},
                    {"label": "Hotline", "value": "Giờ hành chính"},
                    {"label": "Làm việc", "value": "Thứ 2 – Thứ 6"},
                ],
                "subject_options": [
                    {"value": "order", "label": "Đơn hàng & vận chuyển"},
                    {"value": "return", "label": "Đổi trả & hoàn tiền"},
                    {"value": "product", "label": "Sản phẩm & tồn kho"},
                    {"value": "account", "label": "Tài khoản & bảo mật"},
                    {"value": "partner", "label": "Hợp tác / B2B"},
                    {"value": "other", "label": "Khác"},
                ],
            }
        )


class ContactViewSet(viewsets.ModelViewSet):
    """Contact - ai cũng có thể gửi liên hệ (cho phép all), nhưng chỉ admin/support mới xem được"""
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        """Allow anyone to create, but only staff to view/modify"""
        if self.action in ['create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if is_staff(user):
            return Contact.objects.all().order_by("-created_at")
        return Contact.objects.none()  # Non-staff can't see contacts


class FeedbackViewSet(viewsets.ModelViewSet):
    """Feedback - khách hàng gửi feedback, admin/support quản lý"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [permissions.IsAuthenticated(), IsAdminOrStaff()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated()]
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        if self.action in ["create"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if is_staff(user):
            return Feedback.objects.all().order_by("-created_at")
        return Feedback.objects.filter(user=user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PolicyViewSet(viewsets.ModelViewSet):
    """Policy - công khai đọc; chỉ nhân viên tạo/sửa/xóa."""

    queryset = Policy.objects.all()
    serializer_class = PolicySerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdminOrStaff()]
