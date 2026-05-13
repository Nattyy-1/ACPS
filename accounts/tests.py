import io
import django.core.mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.views import APIView
from .permissions import (
    IsApplicant,
    IsReviewOfficer,
    IsInspector,
    IsSeniorOfficer,
    IsAdmin,
    IsAdminOrSeniorOfficer,
)

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            phone="+251911111111",
            password="testpass123",
            role=User.Role.APPLICANT,
        )

    def test_create_user(self):
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.full_name, "Test User")
        self.assertEqual(self.user.phone, "+251911111111")
        self.assertEqual(self.user.role, User.Role.APPLICANT)
        self.assertEqual(self.user.status, "ACTIVE")
        self.assertTrue(self.user.check_password("testpass123"))

    def test_email_unique(self):
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="test@example.com",
                full_name="Another",
                phone="+251922222222",
                password="pass123",
            )

    def test_user_str(self):
        self.assertEqual(str(self.user), "Test User (test@example.com)")

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_required_fields(self):
        self.assertIn("full_name", User.REQUIRED_FIELDS)
        self.assertIn("phone", User.REQUIRED_FIELDS)

    def test_create_officer_roles(self):
        for role in [
            User.Role.REVIEW_OFFICER,
            User.Role.INSPECTOR,
            User.Role.SENIOR_OFFICER,
            User.Role.ADMIN,
        ]:
            user = User.objects.create_user(
                email=f"{role.lower()}@test.com",
                full_name=f"{role} User",
                phone="+251933333333",
                password="pass123",
                role=role,
            )
            self.assertEqual(user.role, role)


class RegisterAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/register/"
        self.valid_payload = {
            "email": "newuser@example.com",
            "full_name": "New User",
            "phone": "+251911111111",
            "password": "strongpass123",
        }

    def test_register_success(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertIn("user_id", response.data)
        self.assertEqual(response.data["message"], "Account created")
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="newuser@example.com",
            full_name="Existing",
            phone="+251922222222",
            password="pass123",
        )
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_fields(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("full_name", response.data)
        self.assertIn("phone", response.data)
        self.assertIn("password", response.data)

    def test_register_short_password(self):
        payload = {**self.valid_payload, "password": "short"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_creates_applicant_role(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="newuser@example.com")
        self.assertEqual(user.role, User.Role.APPLICANT)
        self.assertTrue(user.is_active)


class LoginAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/login/"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            email="login@example.com",
            full_name="Login User",
            phone="+251911111111",
            password=self.password,
            role=User.Role.APPLICANT,
        )

    def test_login_success(self):
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("role", response.data)
        self.assertIn("user_id", response.data)
        self.assertEqual(response.data["role"], User.Role.APPLICANT)
        self.assertEqual(response.data["user_id"], str(self.user.id))

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": "wrongpassword"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        response = self.client.post(
            self.url,
            {"email": "noone@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_returns_valid_token(self):
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": self.password},
            format="json",
        )
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken(response.data["access"])
        self.assertEqual(token.payload.get("user_id"), str(self.user.id))

    def test_login_logs_successful_attempt(self):
        self.client.post(
            self.url,
            {"email": "login@example.com", "password": self.password},
            format="json",
        )
        from .models import LoginAttemptLog

        log = LoginAttemptLog.objects.last()
        self.assertIsNotNone(log)
        self.assertEqual(log.email, "login@example.com")
        self.assertTrue(log.success)

    def test_login_logs_failed_attempt(self):
        self.client.post(
            self.url,
            {"email": "login@example.com", "password": "wrongpassword"},
            format="json",
        )
        from .models import LoginAttemptLog

        log = LoginAttemptLog.objects.last()
        self.assertIsNotNone(log)
        self.assertEqual(log.email, "login@example.com")
        self.assertFalse(log.success)

    def test_login_logs_nonexistent_email(self):
        self.client.post(
            self.url,
            {"email": "ghost@example.com", "password": "somepass"},
            format="json",
        )
        from .models import LoginAttemptLog

        log = LoginAttemptLog.objects.last()
        self.assertIsNotNone(log)
        self.assertEqual(log.email, "ghost@example.com")
        self.assertFalse(log.success)


class RefreshAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/refresh/"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            email="refresh@example.com",
            full_name="Refresh User",
            phone="+251911111111",
            password=self.password,
        )

    def _get_tokens(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "refresh@example.com", "password": self.password},
            format="json",
        )
        return response.data

    def test_refresh_success(self):
        tokens = self._get_tokens()
        response = self.client.post(
            self.url, {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_invalid_token(self):
        response = self.client.post(
            self.url, {"refresh": "invalidtoken123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_new_access_token(self):
        tokens = self._get_tokens()
        response = self.client.post(
            self.url, {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertNotEqual(response.data["access"], tokens["access"])


class LogoutAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/logout/"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            email="logout@example.com",
            full_name="Logout User",
            phone="+251911111111",
            password=self.password,
        )

    def _login(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "logout@example.com", "password": self.password},
            format="json",
        )
        return response.data

    def _auth_header(self, token):
        return f"Bearer {token}"

    def test_logout_success(self):
        tokens = self._login()
        response = self.client.post(
            self.url,
            {"refresh": tokens["refresh"]},
            format="json",
            HTTP_AUTHORIZATION=self._auth_header(tokens["access"]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_auth(self):
        tokens = self._login()
        response = self.client.post(
            self.url,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalid_token(self):
        tokens = self._login()
        response = self.client.post(
            self.url,
            {"refresh": "invalidtoken"},
            format="json",
            HTTP_AUTHORIZATION=self._auth_header(tokens["access"]),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        tokens = self._login()
        self.client.post(
            self.url,
            {"refresh": tokens["refresh"]},
            format="json",
            HTTP_AUTHORIZATION=self._auth_header(tokens["access"]),
        )
        response = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ForgotPasswordAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/forgot-password/"
        self.user = User.objects.create_user(
            email="forgot@example.com",
            full_name="Forgot User",
            phone="+251911111111",
            password="testpass123",
        )

    def test_forgot_password_success(self):
        response = self.client.post(
            self.url, {"email": "forgot@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Password reset link sent to your email"
        )
        self.assertEqual(len(django.core.mail.outbox), 1)
        self.assertIn("forgot@example.com", django.core.mail.outbox[0].to)

    def test_forgot_password_nonexistent_email(self):
        response = self.client.post(
            self.url, {"email": "noone@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Password reset link sent to your email"
        )
        self.assertEqual(len(django.core.mail.outbox), 0)

    def test_forgot_password_missing_email(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_email_contains_reset_link(self):
        response = self.client.post(
            self.url, {"email": "forgot@example.com"}, format="json"
        )
        self.assertIn("reset-password", django.core.mail.outbox[0].body)
        self.assertIn("Password Reset", django.core.mail.outbox[0].subject)


class ResetPasswordAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/reset-password/"
        self.password = "oldpass123"
        self.new_password = "newpass456"
        self.user = User.objects.create_user(
            email="reset@example.com",
            full_name="Reset User",
            phone="+251911111111",
            password=self.password,
        )
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from django.contrib.auth.tokens import PasswordResetTokenGenerator

        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = PasswordResetTokenGenerator().make_token(self.user)

    def test_reset_password_success(self):
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Password has been reset successfully"
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_reset_password_can_login_with_new_password(self):
        self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password,
            },
            format="json",
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "reset@example.com", "password": self.new_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_reset_password_cannot_login_with_old_password(self):
        self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password,
            },
            format="json",
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "reset@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reset_password_invalid_uid(self):
        response = self.client.post(
            self.url,
            {
                "uid": "invalid-uid",
                "token": self.token,
                "new_password": self.new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_invalid_token(self):
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": "bad-token",
                "new_password": self.new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_short_new_password(self):
        response = self.client.post(
            self.url,
            {"uid": self.uid, "token": self.token, "new_password": "short"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PermissionClassesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="perm@example.com",
            full_name="Perm User",
            phone="+251911111111",
            password="testpass123",
            role=User.Role.APPLICANT,
        )
        self.review_officer = User.objects.create_user(
            email="review@example.com",
            full_name="Review Officer",
            phone="+251922222222",
            password="testpass123",
            role=User.Role.REVIEW_OFFICER,
        )
        self.inspector = User.objects.create_user(
            email="inspector@example.com",
            full_name="Inspector",
            phone="+251933333333",
            password="testpass123",
            role=User.Role.INSPECTOR,
        )
        self.senior = User.objects.create_user(
            email="senior@example.com",
            full_name="Senior Officer",
            phone="+251944444444",
            password="testpass123",
            role=User.Role.SENIOR_OFFICER,
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            full_name="Admin",
            phone="+251955555555",
            password="testpass123",
            role=User.Role.ADMIN,
        )

    def _check(self, permission_class, user, expected):
        request = type("Request", (), {"user": user})()
        perm = permission_class()
        result = perm.has_permission(request, None)
        self.assertEqual(result, expected)

    def test_is_applicant_allows_applicant(self):
        self._check(IsApplicant, self.user, True)

    def test_is_applicant_denies_others(self):
        for u in [self.review_officer, self.inspector, self.senior, self.admin]:
            self._check(IsApplicant, u, False)

    def test_is_review_officer_allows_review_officer(self):
        self._check(IsReviewOfficer, self.review_officer, True)

    def test_is_review_officer_denies_others(self):
        for u in [self.user, self.inspector, self.senior, self.admin]:
            self._check(IsReviewOfficer, u, False)

    def test_is_inspector_allows_inspector(self):
        self._check(IsInspector, self.inspector, True)

    def test_is_inspector_denies_others(self):
        for u in [self.user, self.review_officer, self.senior, self.admin]:
            self._check(IsInspector, u, False)

    def test_is_senior_officer_allows_senior_officer(self):
        self._check(IsSeniorOfficer, self.senior, True)

    def test_is_senior_officer_denies_others(self):
        for u in [self.user, self.review_officer, self.inspector, self.admin]:
            self._check(IsSeniorOfficer, u, False)

    def test_is_admin_allows_admin(self):
        self._check(IsAdmin, self.admin, True)

    def test_is_admin_denies_others(self):
        for u in [self.user, self.review_officer, self.inspector, self.senior]:
            self._check(IsAdmin, u, False)

    def test_is_admin_or_senior_officer_allows_both(self):
        self._check(IsAdminOrSeniorOfficer, self.admin, True)
        self._check(IsAdminOrSeniorOfficer, self.senior, True)

    def test_is_admin_or_senior_officer_denies_others(self):
        for u in [self.user, self.review_officer, self.inspector]:
            self._check(IsAdminOrSeniorOfficer, u, False)

    def test_all_permissions_deny_unauthenticated(self):
        anon = type("User", (), {"is_authenticated": False, "role": ""})()
        for cls in [
            IsApplicant,
            IsReviewOfficer,
            IsInspector,
            IsSeniorOfficer,
            IsAdmin,
            IsAdminOrSeniorOfficer,
        ]:
            self._check(cls, anon, False)


class LoginAttemptLogModelTests(TestCase):
    def setUp(self):
        from .models import LoginAttemptLog

        self.LoginAttemptLog = LoginAttemptLog
        self.entry = LoginAttemptLog.objects.create(
            email="test@example.com",
            ip_address="192.168.1.1",
            success=True,
        )

    def test_create_login_attempt_log(self):
        self.assertEqual(self.entry.email, "test@example.com")
        self.assertEqual(self.entry.ip_address, "192.168.1.1")
        self.assertTrue(self.entry.success)

    def test_log_failed_attempt(self):
        entry = self.LoginAttemptLog.objects.create(
            email="nonexistent@example.com",
            ip_address="10.0.0.1",
            success=False,
        )
        self.assertFalse(entry.success)

    def test_log_str(self):
        self.assertIn("SUCCESS", str(self.entry))
        self.assertIn("test@example.com", str(self.entry))

    def test_log_ordering(self):
        from .models import LoginAttemptLog
        from django.utils import timezone

        older = LoginAttemptLog.objects.create(
            email="older@example.com",
            ip_address="1.1.1.1",
            success=False,
        )
        older.timestamp = timezone.now() - timezone.timedelta(hours=1)
        older.save(update_fields=["timestamp"])
        latest = LoginAttemptLog.objects.first()
        self.assertEqual(latest.email, "test@example.com")


class CurrentUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/users/me/"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            email="profile@example.com",
            full_name="Profile User",
            phone="+251911111111",
            password=self.password,
            role=User.Role.APPLICANT,
        )

    def _auth(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "profile@example.com", "password": self.password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def test_get_profile_success(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION=self._auth())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "profile@example.com")
        self.assertEqual(response.data["full_name"], "Profile User")
        self.assertEqual(response.data["phone"], "+251911111111")
        self.assertEqual(response.data["role"], User.Role.APPLICANT)
        self.assertIn("id", response.data)
        self.assertIn("subcity_id", response.data)

    def test_get_profile_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        response = self.client.put(
            self.url,
            {"full_name": "Updated Name", "phone": "+251922222222"},
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Updated Name")
        self.assertEqual(response.data["phone"], "+251922222222")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")

    def test_update_profile_unauthenticated(self):
        response = self.client.put(
            self.url,
            {"full_name": "Updated Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_read_only_fields(self):
        response = self.client.put(
            self.url,
            {"email": "hacked@example.com", "role": "ADMIN"},
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "profile@example.com")
        self.assertEqual(self.user.role, User.Role.APPLICANT)

    def test_update_profile_partial(self):
        response = self.client.put(
            self.url,
            {"subcity_id": "SUBCITY_01"},
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["subcity_id"], "SUBCITY_01")


class AdminUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_password = "adminpass123"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            full_name="Admin User",
            phone="+251900000000",
            password=self.admin_password,
            role=User.Role.ADMIN,
        )
        self.target_user = User.objects.create_user(
            email="target@example.com",
            full_name="Target User",
            phone="+251911111111",
            password="testpass123",
            role=User.Role.APPLICANT,
        )

    def _admin_auth(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "admin@example.com", "password": self.admin_password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def test_admin_get_user_detail(self):
        response = self.client.get(
            f"/api/v1/users/{self.target_user.id}/",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "target@example.com")
        self.assertEqual(response.data["full_name"], "Target User")
        self.assertIn("date_joined", response.data)
        self.assertIn("is_active", response.data)

    def test_admin_get_user_detail_nonexistent(self):
        response = self.client.get(
            "/api/v1/users/999999/",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_get_user_detail_unauthorized_role(self):
        applicant = User.objects.create_user(
            email="applicant@example.com",
            full_name="Applicant",
            phone="+251922222222",
            password="pass123",
            role=User.Role.APPLICANT,
        )
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "applicant@example.com", "password": "pass123"},
            format="json",
        )
        response = self.client.get(
            f"/api/v1/users/{self.target_user.id}/",
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_get_user_detail_unauthenticated(self):
        response = self.client.get(f"/api/v1/users/{self.target_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminUserListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_password = "adminpass123"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            full_name="Admin User",
            phone="+251900000000",
            password=self.admin_password,
            role=User.Role.ADMIN,
        )
        User.objects.create_user(
            email="officer1@example.com",
            full_name="Officer One",
            phone="+251911111111",
            password="pass123",
            role=User.Role.REVIEW_OFFICER,
        )
        User.objects.create_user(
            email="officer2@example.com",
            full_name="Officer Two",
            phone="+251922222222",
            password="pass123",
            role=User.Role.INSPECTOR,
        )

    def _admin_auth(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "admin@example.com", "password": self.admin_password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def test_admin_list_users(self):
        response = self.client.get(
            "/api/v1/users/",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertGreaterEqual(len(response.data["results"]), 3)

    def test_admin_list_users_filter_by_role(self):
        response = self.client.get(
            "/api/v1/users/?role=REVIEW_OFFICER",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for user in response.data["results"]:
            self.assertEqual(user["role"], "REVIEW_OFFICER")

    def test_admin_list_users_unauthenticated(self):
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminCreateUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_password = "adminpass123"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            full_name="Admin User",
            phone="+251900000000",
            password=self.admin_password,
            role=User.Role.ADMIN,
        )

    def _admin_auth(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "admin@example.com", "password": self.admin_password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def test_admin_create_officer(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "newofficer@example.com",
                "full_name": "New Officer",
                "phone": "+251933333333",
                "role": "REVIEW_OFFICER",
                "subcity_id": "SUBCITY_01",
            },
            format="json",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "newofficer@example.com")
        self.assertEqual(response.data["role"], "REVIEW_OFFICER")
        self.assertIn("password", response.data)
        self.assertTrue(User.objects.filter(email="newofficer@example.com").exists())

    def test_admin_create_officer_rejects_applicant_role(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "applicantofficer@example.com",
                "full_name": "Not Allowed",
                "phone": "+251944444444",
                "role": "APPLICANT",
            },
            format="json",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_create_officer_unauthenticated(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "noauth@example.com",
                "full_name": "No Auth",
                "phone": "+251955555555",
                "role": "INSPECTOR",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminDeactivateUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_password = "adminpass123"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            full_name="Admin User",
            phone="+251900000000",
            password=self.admin_password,
            role=User.Role.ADMIN,
        )
        self.target = User.objects.create_user(
            email="todeactivate@example.com",
            full_name="To Deactivate",
            phone="+251911111111",
            password="pass123",
            role=User.Role.REVIEW_OFFICER,
        )

    def _admin_auth(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "admin@example.com", "password": self.admin_password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def test_admin_deactivate_user(self):
        response = self.client.put(
            f"/api/v1/users/{self.target.id}/deactivate/",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, "INACTIVE")
        self.assertFalse(self.target.is_active)

    def test_admin_deactivate_nonexistent_user(self):
        response = self.client.put(
            "/api/v1/users/999999/deactivate/",
            HTTP_AUTHORIZATION=self._admin_auth(),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_deactivate_unauthorized_role(self):
        applicant = User.objects.create_user(
            email="applicant@example.com",
            full_name="Applicant",
            phone="+251922222222",
            password="pass123",
            role=User.Role.APPLICANT,
        )
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "applicant@example.com", "password": "pass123"},
            format="json",
        )
        response = self.client.put(
            f"/api/v1/users/{self.target.id}/deactivate/",
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class VaultDocumentUploadAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/users/me/documents/"
        self.password = "testpass123"
        self.applicant = User.objects.create_user(
            email="applicant@example.com",
            full_name="Test Applicant",
            phone="+251911111111",
            password=self.password,
            role=User.Role.APPLICANT,
        )

    def _auth_header(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "applicant@example.com", "password": self.password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def _valid_jpeg(self):
        img = io.BytesIO()
        img.write(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f\x1a'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x11\x04\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xdb\x00C\x01\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xd9"
        )
        img.seek(0)
        return SimpleUploadedFile("test.jpg", img.getvalue(), content_type="image/jpeg")

    def _valid_png(self):
        return SimpleUploadedFile(
            "test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, content_type="image/png"
        )

    def _valid_pdf(self):
        return SimpleUploadedFile(
            "test.pdf",
            b"%PDF-1.4 test pdf content",
            content_type="application/pdf",
        )

    def test_upload_jpeg_success(self):
        response = self.client.post(
            self.url,
            {"file": self._valid_jpeg(), "document_type": "NATIONAL_ID"},
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("document_id", response.data)
        self.assertIn("status", response.data)
        self.assertIn("validation_result", response.data)
        self.assertEqual(response.data["validation_result"], "valid")

    def test_upload_png_success(self):
        response = self.client.post(
            self.url,
            {"file": self._valid_png(), "document_type": "NATIONAL_ID"},
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["validation_result"], "valid")

    def test_upload_pdf_success(self):
        response = self.client.post(
            self.url,
            {"file": self._valid_pdf(), "document_type": "TIN_CERTIFICATE"},
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["validation_result"], "valid")

    def test_upload_unauthenticated(self):
        response = self.client.post(
            self.url,
            {"file": self._valid_jpeg(), "document_type": "NATIONAL_ID"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_unauthorized_role(self):
        officer = User.objects.create_user(
            email="officer@example.com",
            full_name="Officer",
            phone="+251922222222",
            password="pass123",
            role=User.Role.REVIEW_OFFICER,
        )
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "officer@example.com", "password": "pass123"},
            format="json",
        )
        response = self.client.post(
            self.url,
            {"file": self._valid_jpeg(), "document_type": "NATIONAL_ID"},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_invalid_file_type(self):
        response = self.client.post(
            self.url,
            {
                "file": SimpleUploadedFile(
                    "test.txt", b"text content", content_type="text/plain"
                ),
                "document_type": "NATIONAL_ID",
            },
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_file_too_large(self):
        response = self.client.post(
            self.url,
            {
                "file": SimpleUploadedFile(
                    "large.jpg", b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg"
                ),
                "document_type": "NATIONAL_ID",
            },
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_zero_byte_file(self):
        response = self.client.post(
            self.url,
            {
                "file": SimpleUploadedFile("empty.jpg", b"", content_type="image/jpeg"),
                "document_type": "NATIONAL_ID",
            },
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_missing_document_type(self):
        response = self.client.post(
            self.url,
            {"file": self._valid_jpeg()},
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_missing_file(self):
        response = self.client.post(
            self.url,
            {"document_type": "NATIONAL_ID"},
            format="multipart",
            HTTP_AUTHORIZATION=self._auth_header(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
