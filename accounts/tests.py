from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

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
