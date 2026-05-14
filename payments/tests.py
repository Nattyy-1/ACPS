from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from applications.models import Application, ApplicationHistory
from .models import Payment, FeeSchedule

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pay@test.com", full_name="Payer",
            phone="+251911111111", password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.user, arn="ACPS-2026-000010",
            subcity_id="SC-01", woreda="W1", plot_address="1 Pay Rd",
            plot_gps_lat=9.0, plot_gps_lng=38.7, height_m=5.0,
            floors_above=1, floor_area_sqm=100.0, intended_use="Residential",
            architect_name="Arch", architect_license="L-001", project_value_etb=500000,
        )
        self.payment = Payment.objects.create(
            application=self.app, invoice_id="INV-001", amount_etb=1050.00,
            payment_method=Payment.PaymentMethod.TELEBIRR,
            transaction_reference="TXN-001", status=Payment.Status.CONFIRMED,
        )

    def test_payment_created(self):
        self.assertEqual(self.payment.invoice_id, "INV-001")
        self.assertEqual(self.payment.amount_etb, 1050.00)

    def test_payment_str(self):
        self.assertIn(self.app.arn, str(self.payment))


class FeeScheduleModelTests(TestCase):
    def setUp(self):
        self.fee = FeeSchedule.objects.create(
            min_value_etb=2500000, max_value_etb=5000000,
            fee_percentage=0.001, fixed_fee_etb=500,
        )

    def test_fee_schedule_created(self):
        self.assertEqual(self.fee.min_value_etb, 2500000)

    def test_fee_schedule_str(self):
        self.assertIn("2500000", str(self.fee))


@override_settings(MEDIA_ROOT="/tmp/test_media")
class PaymentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.applicant = User.objects.create_user(
            email="app@pay.com", full_name="Applicant",
            phone="+251911111111", password="pass123", role="APPLICANT",
        )
        self.admin = User.objects.create_user(
            email="admin@pay.com", full_name="Admin",
            phone="+251911111112", password="pass123", role="ADMIN",
        )
        self.app = Application.objects.create(
            applicant=self.applicant, arn="ACPS-2026-000020",
            status=Application.Status.PAYMENT_PENDING,
            subcity_id="SC-01", woreda="W1", plot_address="1 Pay Rd",
            plot_gps_lat=9.0, plot_gps_lng=38.7, height_m=5.0,
            floors_above=1, floor_area_sqm=100.0, intended_use="Residential",
            architect_name="Arch", architect_license="L-001", project_value_etb=500000,
            calculated_fee=550.00,
        )
        self.payment = Payment.objects.create(
            application=self.app, invoice_id="INV-2026-000001",
            amount_etb=550.00, status=Payment.Status.PENDING,
        )

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_invoice_detail(self):
        self._login(self.applicant)
        resp = self.client.get(f"/api/v1/payments/invoices/{self.payment.invoice_id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["invoice_id"], self.payment.invoice_id)

    def test_invoice_detail_unauthorized(self):
        resp = self.client.get(f"/api/v1/payments/invoices/{self.payment.invoice_id}/")
        self.assertEqual(resp.status_code, 401)

    def test_telebirr_payment(self):
        self._login(self.applicant)
        resp = self.client.post(
            f"/api/v1/payments/invoices/{self.payment.invoice_id}/pay/",
            {"payment_method": "TELEBIRR"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.CONFIRMED)

    def test_bank_transfer_flow(self):
        self._login(self.applicant)
        resp = self.client.post(
            f"/api/v1/payments/invoices/{self.payment.invoice_id}/pay/",
            {"payment_method": "BANK_TRANSFER"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.AWAITING_MANUAL_CONFIRMATION)

    def test_payment_list_admin(self):
        self._login(self.admin)
        resp = self.client.get("/api/v1/payments/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.data)

    def test_payment_list_rejects_applicant(self):
        self._login(self.applicant)
        resp = self.client.get("/api/v1/payments/")
        self.assertEqual(resp.status_code, 403)

    def test_invalid_method(self):
        self._login(self.applicant)
        resp = self.client.post(
            f"/api/v1/payments/invoices/{self.payment.invoice_id}/pay/",
            {"payment_method": "INVALID"}, format="json",
        )
        self.assertEqual(resp.status_code, 400)
