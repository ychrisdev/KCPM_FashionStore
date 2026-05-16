from rest_framework import permissions


class RoleChoices:
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"

    CHOICES = [
        (CUSTOMER, "Customer"),
        (STAFF, "Staff"),
        (ADMIN, "Admin"),
    ]


def get_user_role(user):
    if not user.is_authenticated:
        return None
    try:
        from accounts.models import Profile

        role = Profile.objects.filter(user_id=user.pk).values_list("role", flat=True).first()
        if role is None:
            return RoleChoices.CUSTOMER
        return role
    except Exception:
        return RoleChoices.CUSTOMER


def is_admin(user):
    """Quản trị: gán role, xóa review/comment người khác (theo API)."""
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return get_user_role(user) == RoleChoices.ADMIN


def can_manage_profile_roles(user):
    """Gán / đổi role Profile — chỉ admin (theo Profile) hoặc superuser Django."""
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return get_user_role(user) == RoleChoices.ADMIN


def is_staff(user):
    """Nhân viên nội bộ: staff hoặc admin; hoặc superuser / cờ staff Django."""
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if getattr(user, "is_staff", False):
        return True
    role = get_user_role(user)
    return role in (RoleChoices.STAFF, RoleChoices.ADMIN)


def is_order_staff(user):
    """Đơn hàng / trả hàng — staff và admin (tương đương is_staff theo profile)."""
    return is_staff(user)


class IsOrderStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_order_staff(request.user)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_staff(request.user)


class IsAdminWritePublicRead(permissions.BasePermission):
    """GET công khai; ghi chỉ admin Profile (hoặc superuser). Dùng cho biến thể/tồn kho."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_admin(request.user)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_staff(request.user)


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_admin(request.user):
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "profile") and hasattr(obj.profile, "user"):
            return obj.profile.user == request.user
        return False


class IsAuthenticatedOrReadOnlyForCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return is_staff(request.user)
        return True
