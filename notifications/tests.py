from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notif@test.com",
            full_name="Notified",
            phone="+251911111111",
            password="pass123",
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Permit Approved",
            body="Your construction permit has been approved.",
            notification_type="PERMIT_APPROVED",
            reference_id="CP-2026-000001",
            reference_type="PERMIT",
        )

    def test_notification_created(self):
        self.assertEqual(self.notification.title, "Permit Approved")
        self.assertEqual(self.notification.recipient, self.user)
        self.assertFalse(self.notification.is_read)

    def test_notification_str(self):
        self.assertEqual(
            str(self.notification), f"Permit Approved -> {self.user.email}"
        )

    def test_mark_as_read(self):
        self.notification.is_read = True
        self.notification.save()
        self.assertTrue(Notification.objects.get(id=self.notification.id).is_read)
