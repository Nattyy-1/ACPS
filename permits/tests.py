from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Permit
from datetime import date

User = get_user_model()


class PermitModelTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(
            email="officer@test.com",
            full_name="Officer",
            phone="+251911111111",
            password="pass123",
        )
        from applications.models import Application

        self.app = Application.objects.create(
            applicant=self.officer,
            arn="ACPS-2026-000040",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Permit Rd",
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
        self.permit = Permit.objects.create(
            application=self.app,
            permit_number="CP-2026-000001",
            permit_type=Permit.PermitType.CONSTRUCTION,
            issued_by=self.officer,
            issue_date=date.today(),
            expiry_date=date.today(),
        )

    def test_permit_created(self):
        self.assertEqual(self.permit.permit_number, "CP-2026-000001")
        self.assertEqual(self.permit.permit_type, "CONSTRUCTION")
        self.assertEqual(self.permit.status, Permit.Status.ACTIVE)

    def test_permit_str(self):
        self.assertEqual(str(self.permit), "CP-2026-000001 (CONSTRUCTION)")
