from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

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
