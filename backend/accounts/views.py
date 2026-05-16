from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from urllib.parse import quote, quote_plus, urlencode

import requests
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from core.permissions import is_admin, is_staff, RoleChoices, IsAdminOrStaff
from orders.models import DiscountCode

from .birthday_reminder import build_birthday_template_context, render_birthday_email_bodies
from .models import BirthdayEmailTemplate, Profile
from .serializers import (
    BirthdayEmailTemplateSerializer,
    ProfileSerializer,
    RegisterSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def _password_reset_email_bodies(user: User, reset_url: str) -> tuple[str, str]:
    """Nội dung email dạng text + HTML (template trong templates/emails/)."""
    display_name = (user.get_full_name() or "").strip() or user.username
    ctx = {"display_name": display_name, "reset_url": reset_url}
    text_body = render_to_string("emails/password_reset.txt", ctx).strip()
    html_body = render_to_string("emails/password_reset.html", ctx).strip()
    return text_body, html_body


def _allowed_google_oauth_redirect_uris():
    """
    Các redirect_uri được phép khi đổi code — phải khớp một URI đã khai báo trong
    Google Cloud Console (Authorized redirect URIs).
    """
    uris = set()
    primary = (getattr(settings, "GOOGLE_REDIRECT_URI", "") or "").strip().rstrip("/")
    fe = (getattr(settings, "FRONTEND_ORIGIN", "") or "").strip().rstrip("/")
    if primary:
        uris.add(primary)
    if fe:
        uris.add(f"{fe}/auth/google/callback")
    expanded = set()
    for u in uris:
        if not u:
            continue
        expanded.add(u)
        if "//localhost" in u:
            expanded.add(u.replace("//localhost", "//127.0.0.1", 1))
        if "//127.0.0.1" in u:
            expanded.add(u.replace("//127.0.0.1", "//localhost", 1))
    return expanded


def _facebook_profile_picture_url(userinfo: dict) -> str:
    """
    Graph API có thể trả picture: null hoặc cấu trúc khác — không dùng chuỗi .get lồng trực tiếp
    (ví dụ userinfo.get('picture', {}) trả None nếu key tồn tại với giá trị null).
    """
    raw = userinfo.get("picture")
    if not isinstance(raw, dict):
        return ""
    data = raw.get("data")
    if not isinstance(data, dict):
        return ""
    url = (data.get("url") or "").strip()
    return url[:500]


class CustomTokenObtainPairView(TokenObtainPairView):
    """Đăng nhập bằng username hoặc email; trả về lỗi tiếng Việt."""
    serializer_class = CustomTokenObtainPairSerializer


class ProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Profile do signal tạo; chỉ liệt kê / xem / cập nhật (không POST/DELETE)."""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if is_admin(user) or getattr(user, "is_superuser", False):
            return Profile.objects.all()
        return Profile.objects.filter(user=user)

    def perform_update(self, serializer):
        serializer.save()
        
        # Method 2: Gửi ngay định kì sinh nhật sau khu cập nhật (nếu thoả điều kiện). 
        # Chạy trong luồng phụ (thread) để không làm chậm lúc người dùng lưu form.
        from accounts.birthday_reminder import send_birthday_reminder_emails
        import threading
        threading.Thread(target=send_birthday_reminder_emails, daemon=True).start()


class BirthdayEmailTemplateAdminView(RetrieveUpdateAPIView):
    """GET/PATCH mẫu email sinh nhật (pk=1) — staff/admin."""

    serializer_class = BirthdayEmailTemplateSerializer
    permission_classes = [IsAdminOrStaff]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return BirthdayEmailTemplate.get_solo()


class BirthdayEmailPreviewView(APIView):
    """POST xem trước HTML/text (không lưu). Body giống PATCH + preview_display_name."""

    permission_classes = [IsAdminOrStaff]

    def post(self, request):
        base = BirthdayEmailTemplate.get_solo()
        d = request.data
        subject_t = d.get("email_subject", base.email_subject)
        intro = d.get("intro_text", base.intro_text)
        cta = d.get("cta_button_label", base.cta_button_label)
        foot = d.get("footer_text", base.footer_text)
        dc = base.discount_code
        if "discount_code" in d:
            raw = d.get("discount_code")
            if raw in (None, ""):
                dc = None
            else:
                dc = DiscountCode.objects.filter(pk=raw).first()
        env_fb = (getattr(settings, "BIRTHDAY_VOUCHER_CODE", "") or "").strip()
        display = (d.get("preview_display_name") or "Khách hàng thân mến").strip()
        tomorrow = timezone.localdate() + timedelta(days=1)
        subject, ctx = build_birthday_template_context(
            display_name=display,
            birthday_date=tomorrow,
            email_subject=subject_t,
            intro_text=intro,
            cta_button_label=cta,
            footer_text=foot,
            discount_code_obj=dc,
            env_voucher_fallback=env_fb if dc is None else "",
        )
        text_body, html_body = render_birthday_email_bodies(ctx, subject)
        return Response(
            {"subject": subject, "html": html_body, "text": text_body}
        )


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Method 2: Khách hàng khai báo sinh nhật ngay lúc đăng ký trùng khớp -> gửi ưu đãi ngay lập tức.
            from accounts.birthday_reminder import send_birthday_reminder_emails
            import threading
            threading.Thread(target=send_birthday_reminder_emails, daemon=True).start()

            return Response({
                "message": "Đăng ký thành công!",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "Đổi mật khẩu thành công!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=404)

        avatar_url = None
        try:
            if profile.avatar:
                avatar_url = request.build_absolute_uri(profile.avatar.url)
        except Exception:
            pass
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": profile.phone,
            "address": profile.address,
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
            "role": profile.role,
            "can_access_admin": is_staff(request.user),
            "is_admin": is_admin(request.user),
            "avatar": avatar_url,
        })

    def _build_login_response(user: User, request) -> dict:
        """Response chuẩn cho mọi luồng đăng nhập — bao gồm avatar."""
        refresh = RefreshToken.for_user(user)
        avatar_url = None
        try:
            profile = user.profile
            if profile.avatar:
                avatar_url = request.build_absolute_uri(profile.avatar.url)
        except Exception:
            pass
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar": avatar_url,
            },
        }

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            user = User.objects.get(email=email)

            backend = (settings.EMAIL_BACKEND or "").lower()
            if "smtp" in backend:
                if not (settings.EMAIL_HOST_USER or "").strip() or not (
                    settings.EMAIL_HOST_PASSWORD or ""
                ).strip():
                    return Response(
                        {
                            "message": (
                                "Chưa cấu hình gửi email: trong backend/.env cần EMAIL_HOST_USER "
                                "(Gmail đầy đủ), EMAIL_HOST_PASSWORD (mật khẩu ứng dụng 16 ký tự, "
                                "bỏ dấu cách), và nên đặt DEFAULT_FROM_EMAIL cùng Gmail. "
                                "Khởi động lại server sau khi sửa .env."
                            ),
                        },
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

            # Generate password reset token
            from django.contrib.auth.tokens import default_token_generator
            token = default_token_generator.make_token(user)

            frontend = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
            reset_url = f"{frontend}/reset-password?{urlencode({'token': token, 'user_id': str(user.id)})}"

            text_body, html_body = _password_reset_email_bodies(user, reset_url)

            # Gửi email (Gmail: cấu hình SMTP trong .env — xem env.example)
            try:
                send_mail(
                    subject="Đặt lại mật khẩu - FashionStore",
                    message=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                    html_message=html_body,
                )
            except Exception as e:
                err_s = str(e)
                low = err_s.lower()
                if (
                    "535" in err_s
                    or "badcredentials" in low
                    or "username and password not accepted" in low
                ):
                    return Response(
                        {
                            "message": (
                                "Gmail từ chối đăng nhập SMTP (lỗi 535). Kiểm tra backend/.env: "
                                "(1) EMAIL_HOST_USER đúng Gmail đã tạo Mật khẩu ứng dụng; "
                                "(2) EMAIL_HOST_PASSWORD là mật khẩu 16 ký tự do Google cấp "
                                "(không dùng mật khẩu đăng nhập web; có thể dán có dấu cách — "
                                "server sẽ tự bỏ khoảng trắng); "
                                "(3) tài khoản Google đã bật xác minh 2 bước; "
                                "(4) tạo mật khẩu mới tại https://myaccount.google.com/apppasswords "
                                "nếu mật cũ sai hoặc đã thu hồi. "
                                "Tài khoản Workspace/đại học có thể không cho App Password — thử Gmail cá nhân "
                                "hoặc hỏi quản trị. Sau đó khởi động lại runserver."
                            ),
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                return Response(
                    {"message": f"Lỗi gửi email: {err_s}. Vui lòng thử lại sau."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            payload = {
                "message": f"Liên kết đặt lại mật khẩu đã được gửi đến {email}",
            }
            if settings.DEBUG and "console" in backend:
                payload["dev_note"] = (
                    "EMAIL_BACKEND=console: không có thư trong hộp Gmail — chỉ in ra terminal "
                    "runserver. Đổi sang smtp + điền Gmail trong .env để gửi thật."
                )
                payload["reset_url"] = reset_url
            return Response(payload, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["_user"]
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response(
                {
                    "message": "Đặt lại mật khẩu thành công. Bạn có thể đăng nhập bằng mật khẩu mới."
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleAuthUrlView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Generate Google OAuth2 authorization URL"""
        client_id = settings.GOOGLE_CLIENT_ID
        redirect_uri = settings.GOOGLE_REDIRECT_URI

        if not client_id:
            return Response({
                "error": "Google OAuth chưa được cấu hình"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Google OAuth2 authorization URL
        scope = "openid email profile"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={quote_plus(client_id)}&"
            f"redirect_uri={quote_plus(redirect_uri)}&"
            f"response_type=code&"
            f"scope={quote_plus(scope)}&"
            f"access_type=offline&"
            f"prompt=select_account"
        )

        return Response({
            "auth_url": auth_url
        })


class GoogleCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Exchange authorization code for tokens and authenticate user"""
        code = request.data.get('code')
        if not code:
            return Response({
                "error": "Thiếu mã authorization"
            }, status=status.HTTP_400_BAD_REQUEST)

        raw_redirect = (request.data.get("redirect_uri") or "").strip().rstrip("/")
        allowed = _allowed_google_oauth_redirect_uris()
        if raw_redirect:
            if raw_redirect not in allowed:
                return Response(
                    {
                        "error": (
                            "redirect_uri không khớp cấu hình. Thêm đúng URI vào "
                            "Google Cloud Console (Authorized redirect URIs), hoặc mở "
                            "site bằng cùng host với URI đã khai báo (localhost vs 127.0.0.1)."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            redirect_uri = raw_redirect
        else:
            redirect_uri = (settings.GOOGLE_REDIRECT_URI or "").strip().rstrip("/")

        try:
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }

            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()

            # Get user info from Google
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            userinfo_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            userinfo_response = requests.get(userinfo_url, headers=userinfo_headers)
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

            # Find or create user
            email = userinfo.get('email')
            google_id = userinfo.get('id')

            if not email:
                return Response({
                    "error": "Không thể lấy thông tin email từ Google"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Try to find existing user by email
            user = User.objects.filter(email=email).first()

            if user:
                # Update existing user with Google info
                profile = Profile.objects.get(user=user)
                profile.google_id = google_id
                profile.save()
            else:
                # Create new user
                username = email.split('@')[0]
                # Ensure username is unique
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=userinfo.get('given_name', ''),
                    last_name=userinfo.get('family_name', ''),
                )

                Profile.objects.create(
                    user=user,
                    google_id=google_id,
                    phone='',
                    address='',
                    role=RoleChoices.CUSTOMER
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            })

        except requests.exceptions.RequestException as e:
            return Response({
                "error": f"Lỗi kết nối với Google: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": f"Lỗi xác thực Google: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Handle Google ID token verification (alternative method)"""
        id_token = request.data.get('id_token')

        if not id_token:
            return Response({
                "error": "Thiếu ID token"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify Google ID token
            verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            verify_response = requests.get(verify_url)
            verify_response.raise_for_status()
            userinfo = verify_response.json()

            # Extract user info
            email = userinfo.get('email')
            google_id = userinfo.get('sub')

            if not email:
                return Response({
                    "error": "Không thể lấy thông tin email từ Google"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Find or create user
            user = User.objects.filter(email=email).first()

            if user:
                profile = Profile.objects.get(user=user)
                profile.google_id = google_id
                profile.save()
            else:
                username = email.split('@')[0]
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=userinfo.get('given_name', ''),
                    last_name=userinfo.get('family_name', ''),
                )

                Profile.objects.create(
                    user=user,
                    google_id=google_id,
                    phone='',
                    address='',
                    role=RoleChoices.CUSTOMER
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            })

        except requests.exceptions.RequestException as e:
            return Response({
                "error": f"Lỗi xác thực Google: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": f"Lỗi xử lý: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


class FacebookAuthUrlView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Generate Facebook OAuth2 authorization URL"""
        app_id = settings.FACEBOOK_APP_ID
        redirect_uri = settings.FACEBOOK_REDIRECT_URI

        if not app_id:
            return Response({
                "error": "Facebook OAuth chưa được cấu hình"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Chỉ dùng public_profile (tránh lỗi Invalid Scopes: email); email xử lý trong callback nếu thiếu
        scope = "public_profile"
        auth_url = (
            f"https://www.facebook.com/v21.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={quote(redirect_uri, safe='')}&"
            f"scope={scope}&"
            f"response_type=code&"
            f"state=facebook"
        )

        return Response({
            "auth_url": auth_url
        })


class FacebookCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Exchange authorization code for access token and authenticate user"""
        code = request.data.get('code')

        if not code:
            return Response({
                "error": "Thiếu mã authorization"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Exchange code for access token (redirect_uri phải khớp chính xác với Facebook App)
            token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
            token_params = {
                "client_id": settings.FACEBOOK_APP_ID,
                "client_secret": settings.FACEBOOK_APP_SECRET,
                "code": code,
                "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
            }

            token_response = requests.get(token_url, params=token_params)
            tokens = token_response.json()

            if 'error' in tokens:
                err = tokens['error']
                msg = err.get('message', 'Lỗi xác thực Facebook')
                return Response({
                    "error": f"Facebook: {msg}. Kiểm tra Redirect URI trong Facebook App có đúng http://localhost:5173/auth/facebook/callback không."
                }, status=status.HTTP_400_BAD_REQUEST)

            access_token = tokens.get('access_token')
            if not access_token:
                return Response({
                    "error": "Không nhận được access token từ Facebook"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get user info from Facebook
            userinfo_url = "https://graph.facebook.com/v21.0/me"
            userinfo_params = {
                "fields": "id,name,email,first_name,last_name,picture",
                "access_token": access_token,
            }
            userinfo_response = requests.get(userinfo_url, params=userinfo_params)
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

            if 'error' in userinfo:
                err = userinfo.get('error')
                if isinstance(err, dict):
                    msg = err.get('message', 'Lỗi lấy thông tin Facebook')
                else:
                    msg = str(err) if err else 'Lỗi lấy thông tin Facebook'
                return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

            # Extract user info (email có thể None nếu chỉ request public_profile)
            facebook_id = userinfo.get('id')
            if not facebook_id:
                return Response({
                    "error": "Facebook không trả id người dùng."
                }, status=status.HTTP_400_BAD_REQUEST)

            email = userinfo.get('email') or f"fb_{facebook_id}@placeholder.local"
            first_name = userinfo.get('first_name') or ''
            last_name = userinfo.get('last_name') or ''
            picture = _facebook_profile_picture_url(userinfo)

            # Find or create user (ưu tiên tìm theo facebook_id, rồi email)
            profile_row = Profile.objects.filter(facebook_id=facebook_id).first()
            user = profile_row.user if profile_row else None
            if not user and email:
                user = User.objects.filter(email=email).first()

            if user:
                profile, _ = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        "phone": "",
                        "address": "",
                        "role": RoleChoices.CUSTOMER,
                    },
                )
                profile.facebook_id = facebook_id
                if picture:
                    profile.avatar = picture
                profile.save()
            else:
                base_username = (email.split('@')[0] if '@' in email else f"fb_{facebook_id}").replace('.', '_')[:30]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"[:30]
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )

                Profile.objects.create(
                    user=user,
                    facebook_id=facebook_id,
                    avatar=picture,
                    phone='',
                    address='',
                    role=RoleChoices.CUSTOMER
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            })

        except requests.exceptions.RequestException as e:
            return Response({
                "error": f"Lỗi kết nối với Facebook: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": f"Lỗi xác thực Facebook: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


class FacebookLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Handle Facebook access token verification"""
        access_token = request.data.get('access_token')

        if not access_token:
            return Response({
                "error": "Thiếu access token"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify access token
            debug_url = "https://graph.facebook.com/debug_token"
            debug_params = {
                "input_token": access_token,
                "access_token": f"{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}",
            }

            debug_response = requests.get(debug_url, params=debug_params)
            debug_response.raise_for_status()
            debug_data = debug_response.json()

            if not debug_data.get('data', {}).get('is_valid'):
                return Response({
                    "error": "Access token không hợp lệ"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get user info from Facebook
            userinfo_url = "https://graph.facebook.com/v21.0/me"
            userinfo_params = {
                "fields": "id,name,email,first_name,last_name,picture",
                "access_token": access_token,
            }
            userinfo_response = requests.get(userinfo_url, params=userinfo_params)
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

            facebook_id = userinfo.get('id')
            if not facebook_id:
                return Response({
                    "error": "Facebook không trả id người dùng."
                }, status=status.HTTP_400_BAD_REQUEST)

            email = userinfo.get('email') or f"fb_{facebook_id}@placeholder.local"
            first_name = userinfo.get('first_name') or ''
            last_name = userinfo.get('last_name') or ''
            picture = _facebook_profile_picture_url(userinfo)

            # Find or create user (ưu tiên facebook_id, rồi email)
            profile_obj = Profile.objects.filter(facebook_id=facebook_id).first()
            user = profile_obj.user if profile_obj else (User.objects.filter(email=email).first() if email else None)

            if user:
                profile, _ = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        "phone": "",
                        "address": "",
                        "role": RoleChoices.CUSTOMER,
                    },
                )
                profile.facebook_id = facebook_id
                if picture:
                    profile.avatar = picture
                profile.save()
            else:
                base_username = (email.split('@')[0] if '@' in email else f"fb_{facebook_id}").replace('.', '_')[:30]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"[:30]
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )

                Profile.objects.create(
                    user=user,
                    facebook_id=facebook_id,
                    avatar=picture,
                    phone='',
                    address='',
                    role=RoleChoices.CUSTOMER
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            })

        except requests.exceptions.RequestException as e:
            return Response({
                "error": f"Lỗi xác thực Facebook: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": f"Lỗi xử lý: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)