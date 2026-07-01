from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from accounts.birthday_reminder import (
    _is_anniversary_birthday,
    _tomorrow_local,
    iter_profiles_birthday_tomorrow,
    send_birthday_reminder_emails,
)
from accounts.models import BirthdayEmailTemplate, Profile
from accounts.serializers import (
    BirthdayEmailTemplateSerializer,
    PasswordResetConfirmSerializer,
    UserSerializer,
)
from accounts.signals import create_user_profile, save_user_profile
from accounts.views import (
    FacebookAuthUrlView,
    FacebookLoginView,
    GoogleAuthUrlView,
    GoogleLoginView,
    _allowed_google_oauth_redirect_uris,
    _facebook_profile_picture_url,
)
from core.permissions import RoleChoices
from orders.models import DiscountCode

TEST_PASSWORD = "secret12345"  
TEST_OLD_PASSWORD = "OldSecret12345"  
TEST_NEW_PASSWORD = "NewSecret12345"  

REGISTER_URL = "/api/auth/registration/"
LOGIN_URL = "/api/auth/token/"

class ProfileRolePermissionTests(TestCase):
    """Đảm bảo chỉ admin/superuser mới PATCH được field role."""

    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username="cust",
            email="cust@example.com",
            password=TEST_PASSWORD,  
        )
        self.customer_profile = Profile.objects.get(user=self.customer)

        self.other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password=TEST_PASSWORD,  
        )
        self.other_profile = Profile.objects.get(user=self.other)

        self.admin_user = User.objects.create_user(
            username="adm",
            email="adm@example.com",
            password=TEST_PASSWORD,  
        )
        p = Profile.objects.get(user=self.admin_user)
        p.role = RoleChoices.ADMIN
        p.save()

        self.staff_user = User.objects.create_user(
            username="staff1",
            email="staff1@example.com",
            password=TEST_PASSWORD,  
        )
        p2 = Profile.objects.get(user=self.staff_user)
        p2.role = RoleChoices.STAFF
        p2.save()

    def test_customer_cannot_patch_own_role(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/accounts/profiles/{self.customer_profile.id}/"
        res = self.client.patch(url, {"role": RoleChoices.ADMIN}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", res.data)
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.role, RoleChoices.CUSTOMER)

    def test_customer_can_patch_phone_without_role(self):
        self.client.force_authenticate(user=self.customer)
        url = f"/api/accounts/profiles/{self.customer_profile.id}/"
        res = self.client.patch(url, {"phone": "0909123456"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.phone, "0909123456")
        self.assertEqual(self.customer_profile.role, RoleChoices.CUSTOMER)

    def test_staff_cannot_patch_own_role(self):
        self.client.force_authenticate(user=self.staff_user)
        staff_profile = Profile.objects.get(user=self.staff_user)
        url = f"/api/accounts/profiles/{staff_profile.id}/"
        res = self.client.patch(url, {"role": RoleChoices.ADMIN}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        staff_profile.refresh_from_db()
        self.assertEqual(staff_profile.role, RoleChoices.STAFF)

    def test_admin_can_patch_other_user_role(self):
        self.client.force_authenticate(user=self.admin_user)
        url = f"/api/accounts/profiles/{self.other_profile.id}/"
        res = self.client.patch(
            url, {"role": RoleChoices.STAFF}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.other_profile.refresh_from_db()
        self.assertEqual(self.other_profile.role, RoleChoices.STAFF)

    def test_current_user_is_admin_flag(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/auth/user/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data.get("is_admin"))

        self.client.force_authenticate(user=self.admin_user)
        r = self.client.get("/api/auth/user/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data.get("is_admin"))

    def test_superuser_can_patch_role_without_profile_admin(self):
        su = User.objects.create_superuser(
            username="su",
            email="su@example.com",
            password=TEST_PASSWORD,  
        )
        Profile.objects.filter(user=su).update(role=RoleChoices.CUSTOMER)
        self.client.force_authenticate(user=su)
        url = f"/api/accounts/profiles/{self.customer_profile.id}/"
        res = self.client.patch(
            url, {"role": RoleChoices.STAFF}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.customer_profile.refresh_from_db()
        self.assertEqual(
            self.customer_profile.role, RoleChoices.STAFF
        )

    def test_customer_cannot_access_dashboard_stats(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/core/dashboard/stats/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_dashboard_returns_ops_scope(self):
        self.client.force_authenticate(user=self.staff_user)
        r = self.client.get("/api/core/dashboard/stats/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data.get("role_scope"), "staff")
        self.assertNotIn("revenue_today", r.data)
        self.assertIn("pending_returns", r.data)
        self.assertIn("shipping_orders", r.data)

    def test_admin_dashboard_returns_financial_scope(self):
        self.client.force_authenticate(user=self.admin_user)
        r = self.client.get("/api/core/dashboard/stats/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data.get("role_scope"), "admin")
        self.assertIn("revenue_today", r.data)
        self.assertIn("users_total", r.data)
        self.assertIn("top_products", r.data)

    def test_customer_dashboard_ok_for_customer(self):
        self.client.force_authenticate(user=self.customer)
        r = self.client.get("/api/core/dashboard/customer/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("orders_total", r.data)
        self.assertIn("recent_orders", r.data)
        self.assertIn("orders_daily_7d", r.data)
        self.assertEqual(len(r.data["orders_daily_7d"]), 7)

    def test_customer_dashboard_forbidden_for_staff(self):
        self.client.force_authenticate(user=self.staff_user)
        r = self.client.get("/api/core/dashboard/customer/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_dashboard_forbidden_for_admin_role(self):
        self.client.force_authenticate(user=self.admin_user)
        r = self.client.get("/api/core/dashboard/customer/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_get_birthday_email_template(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get("/api/accounts/birthday-email-template/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("email_subject", res.data)
        self.assertIn("intro_text", res.data)

    def test_customer_cannot_get_birthday_email_template(self):
        self.client.force_authenticate(user=self.customer)
        res = self.client.get("/api/accounts/birthday-email-template/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class PasswordResetConfirmTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="reset_u",
            email="reset_u@example.com",
            password=TEST_OLD_PASSWORD,  
        )

    def test_confirm_valid_token_changes_password(self):
        token = default_token_generator.make_token(self.user)
        res = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "user_id": self.user.id,
                "token": token,
                "new_password": TEST_NEW_PASSWORD,
                "new_password_confirm": TEST_NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEST_NEW_PASSWORD))

    def test_confirm_invalid_token_rejected(self):
        res = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "user_id": self.user.id,
                "token": "invalid-token",
                "new_password": TEST_NEW_PASSWORD,
                "new_password_confirm": TEST_NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEST_OLD_PASSWORD))

""" 
class BirthdayReminderTests(TestCase):
    def test_anniversary_feb29_non_leap_observed_feb28(self):
        birth = date(2000, 2, 29)
        self.assertTrue(_is_anniversary_birthday(birth, date(2027, 2, 28)))
        self.assertFalse(_is_anniversary_birthday(birth, date(2027, 3, 1)))

    def test_anniversary_feb29_leap_year(self):
        birth = date(2000, 2, 29)
        self.assertTrue(_is_anniversary_birthday(birth, date(2028, 2, 29)))

    @patch("accounts.birthday_reminder._tomorrow_local", return_value=date(2026, 6, 1))
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="sender@example.com",
        DEFAULT_FROM_EMAIL="FashionStore <sender@example.com>",
        BIRTHDAY_REMINDER_EMAIL_ENABLED=True,
        BIRTHDAY_VOUCHER_CODE="SN2026",
    )
    def test_send_reminder_once_and_marks_year(self, _mock_tomorrow):
        user = User.objects.create_user(
            username="bday_user",
            email="bday@example.com",
            password=TEST_PASSWORD,  
        )
        p = Profile.objects.get(user=user)
        p.birth_date = date(1995, 6, 1)
        p.save(update_fields=["birth_date"])

        mail.outbox.clear()
        sent, _ = send_birthday_reminder_emails()
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("SN2026", mail.outbox[0].body)

        p.refresh_from_db()
        self.assertEqual(p.birthday_reminder_sent_for_year, 2026)

        mail.outbox.clear()
        sent2, _ = send_birthday_reminder_emails()
        self.assertEqual(sent2, 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch("accounts.birthday_reminder._tomorrow_local", return_value=date(2026, 6, 1))
    def test_iter_skips_staff(self, _mock_tomorrow):
        user = User.objects.create_user(
            username="staff_bday",
            email="st@example.com",
            password=TEST_PASSWORD,  
        )
        p = Profile.objects.get(user=user)
        p.role = RoleChoices.STAFF
        p.birth_date = date(1990, 6, 1)
        p.save(update_fields=["role", "birth_date"])
        self.assertEqual(iter_profiles_birthday_tomorrow(), [])
 """
class ChangePasswordViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="change_pw_user",
            email="changepw@example.com",
            password=TEST_PASSWORD,  
        )

    def test_change_password_success(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(
            "/api/auth/password/change/",
            {
                "old_password": TEST_PASSWORD,  
                "new_password": TEST_NEW_PASSWORD,  
                "new_password_confirm": TEST_NEW_PASSWORD,  
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEST_NEW_PASSWORD))

    def test_change_password_wrong_old_password(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(
            "/api/auth/password/change/",
            {
                "old_password": "wrongpassword",  
                "new_password": TEST_NEW_PASSWORD,  
                "new_password_confirm": TEST_NEW_PASSWORD,  
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        res = self.client.post(
            "/api/auth/registration/",
            {
                "username": "newuser123",
                "email": "newuser123@example.com",
                "password": TEST_PASSWORD,  
                "password_confirm": TEST_PASSWORD,  
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", res.data)

    def test_register_duplicate_username(self):
        User.objects.create_user(
            username="dupuser",
            email="dup@example.com",
            password=TEST_PASSWORD,  
        )
        res = self.client.post(
            "/api/auth/registration/",
            {
                "username": "dupuser",
                "email": "dup2@example.com",
                "password": TEST_PASSWORD,  
                "password_confirm": TEST_PASSWORD,  
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmSerializerTest(TestCase):
    def test_invalid_user_id_raises_error(self):
        """Cover nhánh User.DoesNotExist trong PasswordResetConfirmSerializer"""
        data = {
            "user_id": 99999,
            "token": "some-token",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("detail", str(serializer.errors))


class BirthdayEmailTemplateSerializerTest(TestCase):
    def test_get_discount_code_detail_returns_data(self):
        """Cover nhánh return {...} trong get_discount_code_detail"""
        dc = DiscountCode.objects.create(
            code="BDAY10",
            name="Birthday Discount",
            discount_percent=10,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        template = BirthdayEmailTemplate.get_solo()
        template.email_subject = "Happy Birthday"
        template.intro_text = "Hello"
        template.cta_button_label = "Shop Now"
        template.footer_text = "Footer"
        template.discount_code = dc
        template.save()

        serializer = BirthdayEmailTemplateSerializer(template)
        detail = serializer.data["discount_code_detail"]
        self.assertIsNotNone(detail)
        self.assertEqual(detail["code"], "BDAY10")

class ProfileUserSerializerTest(TestCase):
    def test_validate_email_with_no_instance(self):
        """Cover nhánh if user is None: return value trong ProfileUserSerializer"""
        from accounts.serializers import ProfileUserSerializer
        serializer = ProfileUserSerializer(data={
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        })
        self.assertTrue(serializer.is_valid())

    def test_validate_email_duplicate_other_user(self):
        """Cover nhánh email đã dùng bởi tài khoản khác"""
        from accounts.serializers import ProfileUserSerializer
        User.objects.create_user(
            username="other_user",
            email="taken@example.com",
            password=TEST_PASSWORD,  
        )
        current = User.objects.create_user(
            username="current_user",
            email="current@example.com",
            password=TEST_PASSWORD,  
        )
        serializer = ProfileUserSerializer(
            instance=current,
            data={"email": "taken@example.com"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class CurrentUserViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="view_user",
            email="view@example.com",
            password=TEST_PASSWORD,  
        )

    def test_current_user_returns_200(self):
        """Cover CurrentUserView.get() — nhánh bình thường"""
        self.client.force_authenticate(user=self.user)
        res = self.client.get("/api/auth/user/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "view@example.com")

    def test_current_user_avatar_exception_handled(self):
        """Cover nhánh except Exception: pass trong get_avatar"""
        self.client.force_authenticate(user=self.user)
        res = self.client.get("/api/auth/user/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data["avatar"])

class GoogleCallbackViewTests(TestCase):
    """Cover GoogleCallbackView.post() và các helper _exchange_google_code,
    _fetch_google_userinfo, _get_or_create_google_user."""

    def setUp(self):
        self.client = APIClient()

    def test_missing_code_returns_400(self):
        res = self.client.post("/api/auth/google/callback/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redirect_uri_not_allowed_returns_400(self):
        res = self.client.post(
            "/api/auth/google/callback/",
            {"code": "fake-code", "redirect_uri": "https://evil.example.com/cb"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.requests.get")
    @patch("accounts.views.requests.post")
    def test_creates_new_user_when_email_not_found(self, mock_post, mock_get):
        """Cover nhánh tạo user mới trong _get_or_create_google_user"""
        mock_post.return_value.json.return_value = {"access_token": "tok123"}
        mock_post.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "email": "newgoogle@example.com",
            "id": "g-id-1",
            "given_name": "New",
            "family_name": "Google",
        }
        mock_get.return_value.raise_for_status.return_value = None

        res = self.client.post(
            "/api/auth/google/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        user = User.objects.get(email="newgoogle@example.com")
        self.assertEqual(Profile.objects.get(user=user).google_id, "g-id-1")

    @patch("accounts.views.requests.get")
    @patch("accounts.views.requests.post")
    def test_links_existing_user_by_email(self, mock_post, mock_get):
        """Cover nhánh user đã tồn tại trong _get_or_create_google_user"""
        existing = User.objects.create_user(
            username="existing_g",
            email="existing@example.com",
            password=TEST_PASSWORD,  
        )
        mock_post.return_value.json.return_value = {"access_token": "tok456"}
        mock_post.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "email": "existing@example.com",
            "id": "g-id-2",
        }
        mock_get.return_value.raise_for_status.return_value = None

        res = self.client.post(
            "/api/auth/google/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        profile = Profile.objects.get(user=existing)
        self.assertEqual(profile.google_id, "g-id-2")

    @patch("accounts.views.requests.get")
    @patch("accounts.views.requests.post")
    def test_no_email_from_google_returns_400(self, mock_post, mock_get):
        """Cover nhánh if not userinfo.get('email') trong GoogleCallbackView.post"""
        mock_post.return_value.json.return_value = {"access_token": "tok789"}
        mock_post.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {"id": "g-id-3"}
        mock_get.return_value.raise_for_status.return_value = None

        res = self.client.post(
            "/api/auth/google/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.requests.post")
    def test_google_request_exception_returns_400(self, mock_post):
        """Cover except requests.exceptions.RequestException trong post()"""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("network down")

        res = self.client.post(
            "/api/auth/google/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class FacebookCallbackViewTests(TestCase):
    """Cover FacebookCallbackView.post() và các helper _exchange_facebook_code,
    _fetch_facebook_userinfo, _find_user_for_facebook, _get_or_create_facebook_user."""

    def setUp(self):
        self.client = APIClient()

    def test_missing_code_returns_400(self):
        res = self.client.post("/api/auth/facebook/callback/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.requests.get")
    def test_token_exchange_error_returns_400(self, mock_get):
        """Cover nhánh 'error' in tokens trong _exchange_facebook_code"""
        mock_get.return_value.json.return_value = {
            "error": {"message": "Invalid verification code"}
        }
        res = self.client.post(
            "/api/auth/facebook/callback/", {"code": "bad-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.requests.get")
    def test_creates_new_user_with_placeholder_email(self, mock_get):
        """Cover nhánh tạo user mới khi Facebook không trả email (_get_or_create_facebook_user)"""
        def fake_get(url, params=None, **kwargs):
            mock_resp = mock_get.return_value.__class__()
            if "oauth/access_token" in url:
                mock_resp.json.return_value = {"access_token": "fb-tok-1"}
            else:
                mock_resp.json.return_value = {
                    "id": "fb-id-1",
                    "first_name": "Face",
                    "last_name": "Book",
                }
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        mock_get.side_effect = fake_get
        res = self.client.post(
            "/api/auth/facebook/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="fb_fb-id-1@placeholder.local")
        self.assertEqual(Profile.objects.get(user=user).facebook_id, "fb-id-1")

    @patch("accounts.views.requests.get")
    def test_links_existing_user_by_facebook_id(self, mock_get):
        """Cover nhánh _find_user_for_facebook tìm theo facebook_id có sẵn"""
        existing = User.objects.create_user(
            username="existing_fb",
            email="existingfb@example.com",
            password=TEST_PASSWORD,
        )
        profile = Profile.objects.get(user=existing)
        profile.facebook_id = "fb-id-2"
        profile.save(update_fields=["facebook_id"])

        def fake_get(url, params=None, **kwargs):
            mock_resp = mock_get.return_value.__class__()
            if "oauth/access_token" in url:
                mock_resp.json.return_value = {"access_token": "fb-tok-2"}
            else:
                mock_resp.json.return_value = {
                    "id": "fb-id-2",
                    "email": "existingfb@example.com",
                }
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        mock_get.side_effect = fake_get

        res = self.client.post(
            "/api/auth/facebook/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["user"]["id"], existing.id)

    @patch("accounts.views.requests.get")
    def test_userinfo_error_returns_400(self, mock_get):
        """Cover nhánh 'error' in userinfo trong _fetch_facebook_userinfo"""
        def fake_get(url, params=None, **kwargs):
            mock_resp = mock_get.return_value.__class__()
            if "oauth/access_token" in url:
                mock_resp.json.return_value = {"access_token": "fb-tok-3"}
            else:
                mock_resp.json.return_value = {"error": {"message": "Bad token"}}
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        mock_get.side_effect = fake_get

        res = self.client.post(
            "/api/auth/facebook/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.requests.get")
    def test_facebook_request_exception_returns_400(self, mock_get):
        """Cover except requests.exceptions.RequestException trong post()"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("network down")

        res = self.client.post(
            "/api/auth/facebook/callback/", {"code": "fake-code"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestViewTests(TestCase):
    """Cover PasswordResetRequestView.post() và _send_password_reset_email."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="reset_req_user",
            email="resetreq@example.com",
            password=TEST_PASSWORD,  
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="sender@example.com",
        EMAIL_HOST_PASSWORD="app-password-16-chars",  
        DEFAULT_FROM_EMAIL="FashionStore <sender@example.com>",
    )
    def test_request_sends_email_successfully(self):
        mail.outbox.clear()
        res = self.client.post(
            "/api/auth/password/reset/",
            {"email": "resetreq@example.com"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",  
    )
    def test_smtp_misconfigured_returns_503(self):
        """Cover nhánh merge-if: smtp backend nhưng thiếu EMAIL_HOST_USER/PASSWORD"""
        res = self.client.post(
            "/api/auth/password/reset/",
            {"email": "resetreq@example.com"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="sender@example.com",
        EMAIL_HOST_PASSWORD="app-password-16-chars",  
    )
    @patch("accounts.views.send_mail")
    def test_gmail_535_error_returns_500_with_guidance(self, mock_send_mail):
        """Cover nhánh lỗi 535 trong _send_password_reset_email"""
        mock_send_mail.side_effect = Exception(
            "(535, b'5.7.8 Username and Password not accepted')"
        )
        res = self.client.post(
            "/api/auth/password/reset/",
            {"email": "resetreq@example.com"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Gmail", res.data["message"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="sender@example.com",
        EMAIL_HOST_PASSWORD="app-password-16-chars",  
    )
    @patch("accounts.views.send_mail")
    def test_generic_send_error_returns_500(self, mock_send_mail):
        """Cover nhánh else (lỗi gửi mail khác 535) trong _send_password_reset_email"""
        mock_send_mail.side_effect = Exception("Connection timed out")
        res = self.client.post(
            "/api/auth/password/reset/",
            {"email": "resetreq@example.com"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Lỗi gửi email", res.data["message"])
        
class RegisterValidationTests(TestCase):
    """
    Cover các trường hợp lỗi validation trong RegisterSerializer.
    Các TC thành công (REG-TC01, TC02, TC03) đã có trong RegisterViewTests.
    """

    def setUp(self):
        self.client = APIClient()
        self.existing_user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password=TEST_PASSWORD,  
        )

    def _post(self, data):
        return self.client.post(REGISTER_URL, data, format="json")

    def _valid_payload(self, **overrides):
        """Trả về payload hợp lệ, có thể ghi đè từng field."""
        base = {
            "username": "validuser",
            "email": "valid@example.com",
            "password": TEST_PASSWORD,
            "password_confirm": TEST_PASSWORD,
        }
        base.update(overrides)
        return base

    def test_register_fail_username_blank(self):
        """REG-TC04: HTTP 400, lỗi field username khi để trống."""
        res = self._post(self._valid_payload(username=""))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data)

    def test_register_fail_email_blank(self):
        """REG-TC05: HTTP 400, lỗi field email khi để trống."""
        res = self._post(self._valid_payload(email=""))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_register_fail_username_already_exists(self):
        """REG-TC06: HTTP 400, username trùng với tài khoản đã có."""
        res = self._post(self._valid_payload(username="existinguser"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data)

    def test_register_fail_email_invalid_format(self):
        """REG-TC07: HTTP 400, email không có @ hoặc thiếu tên miền."""
        res = self._post(self._valid_payload(email="not-an-email"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_register_fail_email_missing_domain(self):
        """REG-TC07 biến thể: email thiếu tên miền (có @ nhưng không có domain)."""
        res = self._post(self._valid_payload(email="user@"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_register_fail_email_already_used(self):
        """REG-TC08: HTTP 400, email trùng với tài khoản đã đăng ký."""
        res = self._post(self._valid_payload(email="existing@example.com"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)
        self.assertIn("Email đã được sử dụng", str(res.data["email"]))

    def test_register_fail_password_too_short(self):
        """REG-TC09: HTTP 400, mật khẩu 7 ký tự (dưới min_length=8)."""
        res = self._post(self._valid_payload(
            password="abc1234",
            password_confirm="abc1234",
        ))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.data)

    def test_register_fail_password_blank(self):
        """REG-TC10: HTTP 400, mật khẩu bỏ trống."""
        res = self._post(self._valid_payload(
            password="",
            password_confirm="",
        ))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.data)

    def test_register_fail_password_confirm_mismatch(self):
        """REG-TC11: HTTP 400, xác nhận mật khẩu không khớp."""
        res = self._post(self._valid_payload(
            password=TEST_PASSWORD,
            password_confirm="different_password99",
        ))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", res.data)
        self.assertIn("Mật khẩu xác nhận không khớp", str(res.data["password_confirm"]))

    def test_register_fail_password_confirm_blank(self):
        """REG-TC11b: HTTP 400, password_confirm để trống (khác với 'không khớp')."""
        res = self._post(self._valid_payload(
            password=TEST_PASSWORD,
            password_confirm="",
        ))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", res.data)

    def test_register_success_username_1_char(self):
        """REG-TC02: HTTP 201, username 1 ký tự hợp lệ."""
        res = self._post(self._valid_payload(username="a"))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_register_success_username_150_chars(self):
        """REG-TC03: HTTP 201, username đúng 150 ký tự."""
        long_username = "u" * 150
        res = self._post(self._valid_payload(username=long_username))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["user"]["username"], long_username)

    def test_register_success_password_8_chars(self):
        """REG-TC01: HTTP 201, mật khẩu đúng 8 ký tự, response có id/username/email."""
        res = self._post(self._valid_payload(password="abcd1234", password_confirm="abcd1234"))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", res.data)
        self.assertIn("id", res.data["user"])
        self.assertIn("username", res.data["user"])
        self.assertIn("email", res.data["user"])
        self.assertNotIn("password", str(res.data))

class LoginTests(TestCase):
    """
    Cover CustomTokenObtainPairSerializer — đăng nhập bằng username/email.
    LOGIN-TC01 đến TC10.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="loginuser",
            email="loginuser@example.com",
            password=TEST_PASSWORD,  
            first_name="Login",
            last_name="User",
        )
        self.disabled_user = User.objects.create_user(
            username="disableduser",
            email="disabled@example.com",
            password=TEST_PASSWORD,  
            is_active=False,
        )

    def _post(self, username, password):
        return self.client.post(
            LOGIN_URL,
            {"username": username, "password": password},
            format="json",
        )

    def test_login_success_by_username(self):
        """LOGIN-TC01: HTTP 200, trả về access/refresh token và username."""
        res = self._post("loginuser", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["username"], "loginuser")

    def test_login_success_by_email(self):
        """LOGIN-TC02: HTTP 200, trả về đầy đủ token và thông tin tài khoản."""
        res = self._post("loginuser@example.com", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertIn("email", res.data["user"])

    def test_login_success_email_case_insensitive(self):
        """LOGIN-TC03: HTTP 200, email viết hoa vẫn xác thực thành công."""
        res = self._post("LOGINUSER@EXAMPLE.COM", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_login_fail_username_blank(self):
        """LOGIN-TC04: HTTP 400, thông báo yêu cầu nhập username/email."""
        res = self._post("", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Vui lòng nhập email hoặc tên đăng nhập và mật khẩu",
            str(res.data["detail"]),
        )

    def test_login_fail_password_blank(self):
        """LOGIN-TC05: HTTP 400, thông báo yêu cầu nhập mật khẩu."""
        res = self._post("loginuser", "")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Vui lòng nhập email hoặc tên đăng nhập và mật khẩu",
            str(res.data["detail"]),
        )

    def test_login_fail_both_blank(self):
        """LOGIN-TC05b: HTTP 400, cả username và password đều trống."""
        res = self._post("", "")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Vui lòng nhập email hoặc tên đăng nhập và mật khẩu",
            str(res.data["detail"]),
        )

    def test_login_fail_username_not_found(self):
        """LOGIN-TC06: HTTP 400, username không tồn tại trong hệ thống."""
        res = self._post("nonexistentuser_xyz", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Email/tên đăng nhập hoặc mật khẩu không đúng",
            str(res.data["detail"]),
        )

    def test_login_fail_email_not_found(self):
        """LOGIN-TC07: HTTP 400, email không tồn tại trong hệ thống."""
        res = self._post("notfound@example.com", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Email/tên đăng nhập hoặc mật khẩu không đúng",
            str(res.data["detail"]),
        )

    def test_login_fail_wrong_password(self):
        """LOGIN-TC08: HTTP 400, mật khẩu không đúng."""
        res = self._post("loginuser", "wrongpassword999")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Email/tên đăng nhập hoặc mật khẩu không đúng",
            str(res.data["detail"]),
        )

    def test_login_fail_account_disabled(self):
        """LOGIN-TC09: HTTP 400, tài khoản chưa được kích hoạt."""
        res = self._post("disableduser", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)
        self.assertIn(
            "Tài khoản chưa được kích hoạt",
            str(res.data["detail"]),
        )

    def test_login_response_structure_complete(self):
        """LOGIN-TC10: Phản hồi chứa đủ access, refresh, id, username, email, first_name, last_name."""
        res = self._post("loginuser", TEST_PASSWORD)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertIsInstance(res.data["access"], str)
        self.assertIsInstance(res.data["refresh"], str)
        self.assertTrue(len(res.data["access"]) > 0)
        user_data = res.data["user"]
        self.assertIn("id", user_data)
        self.assertIn("username", user_data)
        self.assertIn("email", user_data)
        self.assertIn("first_name", user_data)
        self.assertIn("last_name", user_data)
        self.assertNotIn("password", str(res.data))
        
class GoogleAuthUrlViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
 
    @override_settings(GOOGLE_CLIENT_ID="")
    def test_missing_client_id_returns_400(self):
        """Nhánh: chưa cấu hình GOOGLE_CLIENT_ID -> 400."""
        res = self.client.get("/api/auth/google/url/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
 
    @override_settings(
        GOOGLE_CLIENT_ID="fake-client-id",
        GOOGLE_REDIRECT_URI="http://localhost:5173/auth/google/callback",
    )
    def test_returns_auth_url_when_configured(self):
        """Nhánh: đã cấu hình -> trả về auth_url hợp lệ."""
        res = self.client.get("/api/auth/google/url/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("auth_url", res.data)
        self.assertIn("accounts.google.com", res.data["auth_url"])
        self.assertIn("fake-client-id", res.data["auth_url"])
 
class FacebookAuthUrlViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
 
    @override_settings(FACEBOOK_APP_ID="")
    def test_missing_app_id_returns_400(self):
        """Nhánh: chưa cấu hình FACEBOOK_APP_ID -> 400."""
        res = self.client.get("/api/auth/facebook/url/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
 
    @override_settings(
        FACEBOOK_APP_ID="fake-app-id",
        FACEBOOK_REDIRECT_URI="http://localhost:5173/auth/facebook/callback",
    )
    def test_returns_auth_url_when_configured(self):
        """Nhánh: đã cấu hình -> trả về auth_url hợp lệ."""
        res = self.client.get("/api/auth/facebook/url/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("auth_url", res.data)
        self.assertIn("facebook.com", res.data["auth_url"])
        self.assertIn("fake-app-id", res.data["auth_url"])

class GoogleLoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
 
    def test_missing_id_token_returns_400(self):
        res = self.client.post("/api/auth/google/login/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Thiếu ID token", str(res.data))
 
    @patch("accounts.views.requests.get")
    def test_no_email_returns_400(self, mock_get):
        mock_get.return_value.json.return_value = {"sub": "g-sub-1"}
        mock_get.return_value.raise_for_status.return_value = None
 
        res = self.client.post(
            "/api/auth/google/login/", {"id_token": "fake"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(res.data))
 
    @patch("accounts.views.requests.get")
    def test_creates_new_user(self, mock_get):
        mock_get.return_value.json.return_value = {
            "email": "newgooglelogin@example.com",
            "sub": "g-sub-2",
            "given_name": "New",
            "family_name": "User",
        }
        mock_get.return_value.raise_for_status.return_value = None
 
        res = self.client.post(
            "/api/auth/google/login/", {"id_token": "fake"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        user = User.objects.get(email="newgooglelogin@example.com")
        self.assertEqual(Profile.objects.get(user=user).google_id, "g-sub-2")
 
    @patch("accounts.views.requests.get")
    def test_links_existing_user(self, mock_get):
        existing = User.objects.create_user(
            username="existing_glogin",
            email="existingglogin@example.com",
            password=TEST_PASSWORD,
        )
        mock_get.return_value.json.return_value = {
            "email": "existingglogin@example.com",
            "sub": "g-sub-3",
        }
        mock_get.return_value.raise_for_status.return_value = None

        res = self.client.post(
            "/api/auth/google/login/", {"id_token": "fake"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        profile = Profile.objects.get(user=existing)
        self.assertEqual(profile.google_id, "g-sub-3")
 
    @patch("accounts.views.requests.get")
    def test_request_exception_returns_400(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("network down")
        res = self.client.post(
            "/api/auth/google/login/", {"id_token": "fake"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    @patch("accounts.views.requests.get")
    def test_generic_exception_returns_400(self, mock_get):
        """Cover nhánh except Exception (khác RequestException) trong post()."""
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.side_effect = ValueError("bad json")
 
        res = self.client.post(
            "/api/auth/google/login/", {"id_token": "fake"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
class FacebookLoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
 
    def _fake_get(self, debug_valid=True, userinfo_data=None, json_error_on_userinfo=False):
        """Trả về side_effect cho requests.get phân biệt theo URL được gọi."""
        userinfo_data = userinfo_data or {"id": "fb-login-1", "first_name": "Face", "last_name": "Book"}
 
        def fake_get(url, params=None, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            if "debug_token" in url:
                mock_resp.json.return_value = {"data": {"is_valid": debug_valid}}
            else:
                if json_error_on_userinfo:
                    mock_resp.json.side_effect = ValueError("bad json")
                else:
                    mock_resp.json.return_value = userinfo_data
            return mock_resp
 
        return fake_get
 
    def test_missing_access_token_returns_400(self):
        res = self.client.post("/api/auth/facebook/login/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Thiếu access token", str(res.data))
 
    @patch("accounts.views.requests.get")
    def test_invalid_token_returns_400(self, mock_get):
        mock_get.side_effect = self._fake_get(debug_valid=False)
        res = self.client.post(
            "/api/auth/facebook/login/", {"access_token": "tok"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Access token không hợp lệ", str(res.data))
 
    @patch("accounts.views.requests.get")
    def test_no_id_from_facebook_returns_400(self, mock_get):
        mock_get.side_effect = self._fake_get(userinfo_data={"first_name": "NoId"})
        res = self.client.post(
            "/api/auth/facebook/login/", {"access_token": "tok"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    @patch("accounts.views.requests.get")
    def test_creates_new_user_with_placeholder_email(self, mock_get):
        mock_get.side_effect = self._fake_get(
            userinfo_data={"id": "fb-login-2", "first_name": "Face", "last_name": "Book"}
        )
        res = self.client.post(
            "/api/auth/facebook/login/", {"access_token": "tok"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="fb_fb-login-2@placeholder.local")
        self.assertEqual(Profile.objects.get(user=user).facebook_id, "fb-login-2")
 
    @patch("accounts.views.requests.get")
    def test_links_existing_user_by_facebook_id(self, mock_get):
        existing = User.objects.create_user(
            username="existing_fblogin",
            email="existingfblogin@example.com",
            password=TEST_PASSWORD,  
        )
        profile = Profile.objects.get(user=existing)
        profile.facebook_id = "fb-login-3"
        profile.save(update_fields=["facebook_id"])
 
        mock_get.side_effect = self._fake_get(
            userinfo_data={"id": "fb-login-3", "email": "existingfblogin@example.com"}
        )
        res = self.client.post(
            "/api/auth/facebook/login/", {"access_token": "tok"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["user"]["id"], existing.id)
 
    @patch("accounts.views.requests.get")
    def test_request_exception_returns_400(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("network down")
        res = self.client.post(
            "/api/auth/facebook/login/", {"access_token": "tok"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
    @patch("accounts.views.requests.get")
    def test_generic_exception_returns_400(self, mock_get):
        """Cover nhánh except Exception (khác RequestException) trong post()."""
        mock_get.side_effect = self._fake_get(json_error_on_userinfo=True)
        res = self.client.post(
            "/api/auth/facebook/login/", {"access_token": "tok"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
 
class GoogleCallbackViewRedirectUriTests(TestCase):
    def setUp(self):
        self.client = APIClient()
 
    @override_settings(
        GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback/",
        FRONTEND_ORIGIN="http://localhost:5173",
    )
    @patch("accounts.views.requests.get")
    @patch("accounts.views.requests.post")
    def test_explicit_matching_redirect_uri_accepted(self, mock_post, mock_get):
        mock_post.return_value.json.return_value = {"access_token": "tok-x"}
        mock_post.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "email": "explicituri@example.com",
            "id": "g-id-explicit",
        }
        mock_get.return_value.raise_for_status.return_value = None
 
        res = self.client.post(
            "/api/auth/google/callback/",
            {
                "code": "fake-code",
                "redirect_uri": "http://localhost:5173/auth/google/callback",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email="explicituri@example.com").exists())

class FacebookProfilePictureUrlTests(TestCase):
    def test_none_picture_returns_empty(self):
        self.assertEqual(_facebook_profile_picture_url({"picture": None}), "")
 
    def test_missing_picture_key_returns_empty(self):
        self.assertEqual(_facebook_profile_picture_url({}), "")
 
    def test_data_not_dict_returns_empty(self):
        self.assertEqual(
            _facebook_profile_picture_url({"picture": {"data": None}}), ""
        )
 
    def test_valid_picture_returns_url(self):
        userinfo = {"picture": {"data": {"url": "http://example.com/a.jpg"}}}
        self.assertEqual(
            _facebook_profile_picture_url(userinfo), "http://example.com/a.jpg"
        )
 
 
class AllowedGoogleRedirectUrisTests(TestCase):
    @override_settings(
        GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback/",
        FRONTEND_ORIGIN="http://localhost:5173",
    )
    def test_includes_localhost_and_ip_variants(self):
        """Cover nhánh mở rộng localhost <-> 127.0.0.1 trong _allowed_google_oauth_redirect_uris."""
        uris = _allowed_google_oauth_redirect_uris()
        self.assertIn("http://localhost:8000/api/auth/google/callback", uris)
        self.assertIn("http://127.0.0.1:8000/api/auth/google/callback", uris)
        self.assertIn("http://localhost:5173/auth/google/callback", uris)
 
    @override_settings(GOOGLE_REDIRECT_URI="", FRONTEND_ORIGIN="")
    def test_empty_settings_returns_empty_set(self):
        """Cover nhánh primary/fe rỗng -> không thêm gì vào set."""
        uris = _allowed_google_oauth_redirect_uris()
        self.assertEqual(uris, set())