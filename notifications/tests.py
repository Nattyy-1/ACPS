from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from .models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notif@test.com", full_name="Notified",
            phone="+251911111111", password="pass123",
        )
        self.notification = Notification.objects.create(
            recipient=self.user, title="Permit Approved",
            body="Your construction permit has been approved.",
            notification_type="PERMIT_APPROVED",
            reference_id="CP-2026-000001", reference_type="PERMIT",
        )

    def test_notification_created(self):
        self.assertEqual(self.notification.title, "Permit Approved")
        self.assertFalse(self.notification.is_read)

    def test_notification_str(self):
        self.assertIn(self.user.email, str(self.notification))

    def test_mark_as_read(self):
        self.notification.is_read = True
        self.notification.save()
        self.assertTrue(Notification.objects.get(id=self.notification.id).is_read)


class NotificationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com", full_name="User",
            phone="+251911111111", password="pass123",
        )
        self.other = User.objects.create_user(
            email="other@test.com", full_name="Other",
            phone="+251911111112", password="pass123",
        )
        for i in range(5):
            Notification.objects.create(
                recipient=self.user, title=f"Notif {i}",
                body=f"Body {i}", notification_type="TEST",
                is_read=(i >= 3),
            )

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_list_notifications(self):
        self._login(self.user)
        resp = self.client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 5)
        self.assertEqual(resp.data["unread_count"], 3)

    def test_list_unread_only(self):
        self._login(self.user)
        resp = self.client.get("/api/v1/notifications/?unread_only=true")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 3)

    def test_list_unauthenticated(self):
        resp = self.client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, 401)

    def test_mark_read(self):
        self._login(self.user)
        n = Notification.objects.filter(recipient=self.user, is_read=False).first()
        resp = self.client.put(f"/api/v1/notifications/{n.id}/read/")
        self.assertEqual(resp.status_code, 200)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_read_not_found(self):
        self._login(self.user)
        resp = self.client.put("/api/v1/notifications/00000000-0000-0000-0000-000000000000/read/")
        self.assertEqual(resp.status_code, 404)

    def test_mark_read_other_user_notification(self):
        self._login(self.user)
        n = Notification.objects.create(
            recipient=self.other, title="Other's", body="Not mine", notification_type="TEST",
        )
        resp = self.client.put(f"/api/v1/notifications/{n.id}/read/")
        self.assertEqual(resp.status_code, 404)

    def test_read_all(self):
        self._login(self.user)
        resp = self.client.put("/api/v1/notifications/read-all/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["marked_read"], 3)
        self.assertEqual(
            Notification.objects.filter(recipient=self.user, is_read=False).count(), 0,
        )
