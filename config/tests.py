from datetime import timedelta
from django.test import TestCase
from django.conf import settings
from rest_framework.settings import api_settings
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.authentication import JWTAuthentication


class Task1DjangoProjectSetupTests(TestCase):
    def test_project_installed(self):
        self.assertIn("rest_framework", settings.INSTALLED_APPS)
        self.assertIn("rest_framework_simplejwt", settings.INSTALLED_APPS)
        self.assertIn("corsheaders", settings.INSTALLED_APPS)

    def test_all_apps_registered(self):
        expected_apps = [
            "accounts",
            "applications",
            "payments",
            "reviews",
            "inspections",
            "permits",
            "notifications",
            "admin_config",
        ]
        for app in expected_apps:
            with self.subTest(app=app):
                self.assertIn(app, settings.INSTALLED_APPS)

    def test_drf_configured(self):
        auth_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
        self.assertIn(JWTAuthentication, auth_classes)

    def test_throttling_configured(self):
        self.assertIn("user", api_settings.DEFAULT_THROTTLE_RATES)
        self.assertIn("anon", api_settings.DEFAULT_THROTTLE_RATES)

    def test_pagination_configured(self):
        self.assertIs(
            api_settings.DEFAULT_PAGINATION_CLASS,
            PageNumberPagination,
        )


class Task3DatabaseMediaSettingsTests(TestCase):
    def test_media_settings(self):
        self.assertEqual(settings.MEDIA_URL, "/media/")
        self.assertTrue(settings.MEDIA_ROOT is not None)

    def test_static_settings(self):
        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertTrue(settings.STATIC_ROOT is not None)


class Task4JwtConfigurationTests(TestCase):
    def test_access_token_lifetime(self):
        from rest_framework_simplejwt.settings import api_settings as jwt_settings

        self.assertEqual(jwt_settings.ACCESS_TOKEN_LIFETIME, timedelta(minutes=60))

    def test_refresh_token_lifetime(self):
        from rest_framework_simplejwt.settings import api_settings as jwt_settings

        self.assertEqual(jwt_settings.REFRESH_TOKEN_LIFETIME, timedelta(days=7))

    def test_jwt_algorithm(self):
        from rest_framework_simplejwt.settings import api_settings as jwt_settings

        self.assertEqual(jwt_settings.ALGORITHM, "HS256")

    def test_jwt_auth_header(self):
        from rest_framework_simplejwt.settings import api_settings as jwt_settings

        self.assertIn("Bearer", jwt_settings.AUTH_HEADER_TYPES)


class Task5CorsConfigurationTests(TestCase):
    def test_cors_middleware_installed(self):
        self.assertIn(
            "corsheaders.middleware.CorsMiddleware",
            settings.MIDDLEWARE,
        )

    def test_cors_all_origins_allowed(self):
        self.assertTrue(settings.CORS_ALLOW_ALL_ORIGINS)


class Task6LibraryImportsTests(TestCase):
    def test_reportlab_importable(self):
        import importlib

        try:
            importlib.import_module("reportlab")
        except ImportError:
            self.fail("reportlab is not importable")

    def test_qrcode_importable(self):
        import importlib

        try:
            importlib.import_module("qrcode")
        except ImportError:
            self.fail("qrcode is not importable")

    def test_psycopg2_importable(self):
        import importlib

        try:
            importlib.import_module("psycopg2")
        except ImportError:
            self.fail("psycopg2 is not importable")


class Task7EmailBackendTests(TestCase):
    def test_email_backend_configured(self):
        self.assertTrue(settings.EMAIL_BACKEND is not None)
        self.assertIn("EmailBackend", settings.EMAIL_BACKEND)


class Task32BcryptConfigurationTests(TestCase):
    def test_bcrypt_is_first_hasher(self):
        self.assertEqual(
            settings.PASSWORD_HASHERS[0],
            "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
        )

    def test_bcrypt_has_cost_factor_12(self):
        from django.contrib.auth.hashers import BCryptSHA256PasswordHasher

        self.assertGreaterEqual(BCryptSHA256PasswordHasher.rounds, 12)

    def test_bcrypt_importable(self):
        try:
            import bcrypt
        except ImportError:
            self.fail("bcrypt package is not installed")

    def test_password_uses_bcrypt(self):
        from django.contrib.auth.hashers import make_password

        hashed = make_password("testpassword123")
        self.assertTrue(hashed.startswith("bcrypt"))
