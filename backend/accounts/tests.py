from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.birthday_reminder import (
    _is_anniversary_birthday,
    iter_profiles_birthday_tomorrow,
    send_birthday_reminder_emails,
)
from accounts.models import Profile
from core.permissions import RoleChoices


class ProfileRolePermissionTests(TestCase):
    """Đảm bảo chỉ admin/superuser mới PATCH được field role."""

    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username="cust",
            email="cust@example.com",
            password="secret12345",
        )
        self.customer_profile = Profile.objects.get(user=self.customer)

        self.other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="secret12345",
        )
        self.other_profile = Profile.objects.get(user=self.other)

        self.admin_user = User.objects.create_user(
            username="adm",
            email="adm@example.com",
            password="secret12345",
        )
        p = Profile.objects.get(user=self.admin_user)
        p.role = RoleChoices.ADMIN
        p.save()

        self.staff_user = User.objects.create_user(
            username="staff1",
            email="staff1@example.com",
            password="secret12345",
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
            password="secret12345",
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
            password="OldSecret12345",
        )

    def test_confirm_valid_token_changes_password(self):
        token = default_token_generator.make_token(self.user)
        res = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "user_id": self.user.id,
                "token": token,
                "new_password": "NewSecret12345",
                "new_password_confirm": "NewSecret12345",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecret12345"))

    def test_confirm_invalid_token_rejected(self):
        res = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "user_id": self.user.id,
                "token": "invalid-token",
                "new_password": "NewSecret12345",
                "new_password_confirm": "NewSecret12345",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldSecret12345"))


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
            password="secret12345",
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
            password="secret12345",
        )
        p = Profile.objects.get(user=user)
        p.role = RoleChoices.STAFF
        p.birth_date = date(1990, 6, 1)
        p.save(update_fields=["role", "birth_date"])
        self.assertEqual(iter_profiles_birthday_tomorrow(), [])
