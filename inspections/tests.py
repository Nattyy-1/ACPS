from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import (
    Inspection,
    InspectionChecklistItem,
    InspectionPhoto,
    InspectionChecklistTemplate,
)
from datetime import datetime, timezone

User = get_user_model()


class InspectionModelTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            email="inspector@test.com",
            full_name="Inspector",
            phone="+251911111111",
            password="pass123",
        )
        from applications.models import Application

        self.app = Application.objects.create(
            applicant=self.inspector,
            arn="ACPS-2026-000030",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Inspect Rd",
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
        self.inspection = Inspection.objects.create(
            application=self.app,
            inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=datetime.now(timezone.utc),
            assigned_inspector=self.inspector,
        )

    def test_inspection_created(self):
        self.assertEqual(self.inspection.inspection_type, "FOUNDATION")
        self.assertEqual(self.inspection.status, Inspection.Status.SCHEDULED)
        self.assertEqual(self.inspection.assigned_inspector, self.inspector)

    def test_inspection_str(self):
        self.assertIn("FOUNDATION", str(self.inspection))
        self.assertIn(self.app.arn, str(self.inspection))

    def test_inspection_results(self):
        self.inspection.status = Inspection.Status.PASSED
        self.inspection.save()
        self.assertEqual(self.inspection.status, "PASSED")


class InspectionChecklistTemplateModelTests(TestCase):
    def setUp(self):
        self.template = InspectionChecklistTemplate.objects.create(
            inspection_type="FOUNDATION",
            item_text="Check foundation depth",
            order=1,
        )

    def test_template_created(self):
        self.assertEqual(self.template.inspection_type, "FOUNDATION")
        self.assertTrue(self.template.is_active)

    def test_template_str(self):
        self.assertIn("FOUNDATION", str(self.template))


class InspectionChecklistItemModelTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            email="check@test.com",
            full_name="Checker",
            phone="+251911111111",
            password="pass123",
        )
        from applications.models import Application

        self.app = Application.objects.create(
            applicant=self.inspector,
            arn="ACPS-2026-000031",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Check Rd",
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
        self.inspection = Inspection.objects.create(
            application=self.app,
            inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=datetime.now(timezone.utc),
        )

    def test_checklist_item_created(self):
        item = InspectionChecklistItem.objects.create(
            inspection=self.inspection,
            item_text="Verify foundation depth meets spec",
            result=InspectionChecklistItem.Result.PASS,
        )
        self.assertEqual(item.result, "PASS")
        self.assertEqual(item.inspection, self.inspection)


class InspectionPhotoModelTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            email="photo@test.com",
            full_name="Photo Tester",
            phone="+251911111111",
            password="pass123",
        )
        from applications.models import Application

        self.app = Application.objects.create(
            applicant=self.inspector,
            arn="ACPS-2026-000032",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Photo Rd",
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
        self.inspection = Inspection.objects.create(
            application=self.app,
            inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=datetime.now(timezone.utc),
        )

    def test_photo_created(self):
        photo = InspectionPhoto.objects.create(
            inspection=self.inspection,
            file="inspections/test/photo.jpg",
        )
        self.assertIsNotNone(photo.id)
