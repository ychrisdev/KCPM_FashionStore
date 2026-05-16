from django.contrib.auth.models import User
from rest_framework import serializers
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from orders.models import DiscountCode

from .models import BirthdayEmailTemplate, Profile
from core.permissions import RoleChoices, can_manage_profile_roles


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Cho phép đăng nhập bằng username hoặc email; thông báo lỗi tiếng Việt."""

    def validate(self, attrs):
        username_or_email = (attrs.get("username") or "").strip()
        password = attrs.get("password")

        if not username_or_email or not password:
            raise serializers.ValidationError(
                {"detail": "Vui lòng nhập email hoặc tên đăng nhập và mật khẩu."}
            )

        user = None
        if "@" in username_or_email:
            user = User.objects.filter(email__iexact=username_or_email).first()
        if user is None:
            user = User.objects.filter(username=username_or_email).first()

        if not user:
            raise serializers.ValidationError(
                {
                    "detail": "Email/tên đăng nhập hoặc mật khẩu không đúng.",
                }
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Tài khoản chưa được kích hoạt."}
            )
        if not user.check_password(password):
            raise serializers.ValidationError(
                {
                    "detail": "Email/tên đăng nhập hoặc mật khẩu không đúng.",
                }
            )

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "avatar")
        
    def get_avatar(self, obj):
        try:
            avatar = obj.profile.avatar
            if not avatar:
                return None
            request = self.context.get("request")
            return request.build_absolute_uri(avatar.url) if request else avatar.url
        except Exception:
            return None


class ProfileUserSerializer(serializers.ModelSerializer):
    """User nhúng trong Profile: đọc đủ trường; ghi họ tên + email (username chỉ đọc)."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")
        read_only_fields = ("id", "username")

    def validate_email(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Vui lòng nhập email.")
        user = self.instance
        if user is None:
            return value
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Email đã được sử dụng bởi tài khoản khác.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm", "phone", "address", "birth_date")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Tên đăng nhập đã tồn tại")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email đã được sử dụng")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Mật khẩu xác nhận không khớp"})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        phone = validated_data.pop('phone', '')
        address = validated_data.pop('address', '')
        birth_date = validated_data.pop('birth_date', None)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password
        )

        # Signal đã tạo Profile; chỉ cập nhật phone, address, role, birth_date
        profile = Profile.objects.get(user=user)
        profile.phone = phone or ""
        profile.address = address or ""
        profile.role = RoleChoices.CUSTOMER
        if birth_date:
            profile.birth_date = birth_date
        profile.save(update_fields=["phone", "address", "role", "birth_date"])

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        raw = (value or "").strip()
        if not raw:
            raise serializers.ValidationError("Vui lòng nhập email.")
        # Khớp đăng nhập: không phân biệt hoa/thường (Postgres so sánh email phân biệt hoa thường)
        user = User.objects.filter(email__iexact=raw).first()
        if not user:
            raise serializers.ValidationError("Email không tồn tại trong hệ thống")
        return user.email


class PasswordResetConfirmSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.password_validation import validate_password

        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Mật khẩu xác nhận không khớp"}
            )
        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "Liên kết không hợp lệ hoặc đã hết hạn."}
            )
        if not default_token_generator.check_token(user, data["token"]):
            raise serializers.ValidationError(
                {"detail": "Liên kết không hợp lệ hoặc đã hết hạn."}
            )
        validate_password(data["new_password"], user)
        data["_user"] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Mật khẩu xác nhận không khớp"})
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mật khẩu cũ không đúng")
        return value

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        user = self.context['request'].user
        validate_password(value, user)
        return value


class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False)
    user = ProfileUserSerializer()
    role = serializers.ChoiceField(choices=RoleChoices.CHOICES, required=False)

    class Meta:
        model = Profile
        fields = (
            "id",
            "user",
            "phone",
            "address",
            "birth_date",
            "role",
            "google_id",
            "facebook_id",
            "avatar",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("google_id", "facebook_id", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context.get("request")
        if request and not can_manage_profile_roles(request.user):
            if "role" in attrs:
                raise serializers.ValidationError(
                    {"role": "Chỉ quản trị viên mới được thay đổi vai trò."}
                )
        return attrs
    
    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and not can_manage_profile_roles(request.user):
            validated_data.pop("role", None)
        new_bd = validated_data.get("birth_date", serializers.empty)
        # Ngăn việc khách hàng đổi ngày sinh để nhận lại mã trong cùng 1 năm
        # Việc KHÔNG set lại cờ này thành None đảm bảo mỗi tài khoản chỉ nhận được 1 lần/lên 1 năm dương lịch.
        user_data = validated_data.pop("user", None)
        instance = super().update(instance, validated_data)
        if user_data is not None:
            user_ser = ProfileUserSerializer(   
                instance=instance.user,
                data=user_data,
                partial=True,
                context=self.context,
            )
            user_ser.is_valid(raise_exception=True)
            user_ser.save()
        return instance


class BirthdayEmailTemplateSerializer(serializers.ModelSerializer):
    discount_code_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BirthdayEmailTemplate
        fields = (
            "id",
            "email_subject",
            "intro_text",
            "cta_button_label",
            "footer_text",
            "discount_code",
            "discount_code_detail",
        )
        read_only_fields = ("id",)

    def get_discount_code_detail(self, obj):
        dc = obj.discount_code
        if dc is None:
            return None
        return {
            "id": dc.id,
            "code": dc.code,
            "name": dc.name,
            "discount_percent": dc.discount_percent,
        }