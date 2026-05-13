from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Payment, FeeSchedule

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pay@test.com",
            full_name="Payer",
            phone="+251911111111",
            password="pass123",
        )
        from applications.models import Application

        self.app = Application.objects.create(
            applicant=self.user,
            arn="ACPS-2026-000010",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Pay Rd",
            plot_gps_lat=9.0,
            plot_gps_lng=38.7,
            height_m=5.0,
            floors_above=1,
            floor_area_sqm=100.0,
            intended_use="Residential",
            architect_name="Arch",
            architect_license="L-001",
            project_value_etb=500000,
        )
        self.payment = Payment.objects.create(
            application=self.app,
            invoice_id="INV-001",
            amount_etb=1050.00,
            payment_method=Payment.PaymentMethod.TELEBIRR,
            transaction_reference="TXN-001",
            status=Payment.Status.CONFIRMED,
        )

    def test_payment_created(self):
        self.assertEqual(self.payment.invoice_id, "INV-001")
        self.assertEqual(self.payment.amount_etb, 1050.00)
        self.assertEqual(self.payment.status, Payment.Status.CONFIRMED)

    def test_payment_str(self):
        self.assertEqual(str(self.payment), f"Payment INV-001 - {self.app.arn}")


class FeeScheduleModelTests(TestCase):
    def setUp(self):
        self.fee = FeeSchedule.objects.create(
            min_value_etb=2500000,
            max_value_etb=5000000,
            fee_percentage=0.001,
            fixed_fee_etb=500,
        )

    def test_fee_schedule_created(self):
        self.assertEqual(self.fee.min_value_etb, 2500000)
        self.assertEqual(self.fee.max_value_etb, 5000000)
        self.assertEqual(self.fee.fee_percentage, 0.001)

    def test_fee_schedule_str(self):
        self.assertIn("2500000", str(self.fee))
        self.assertIn("5000000", str(self.fee))
