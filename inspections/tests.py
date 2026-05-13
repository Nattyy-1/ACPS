import io
import datetime
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Inspection, InspectionChecklistItem, InspectionPhoto, InspectionChecklistTemplate
from applications.models import Application

User = get_user_model()


class InspectionModelTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            email="inspector@test.com", full_name="Inspector",
            phone="+251911111111", password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.inspector, arn="ACPS-2026-000030",
            subcity_id="SC-01", woreda="W1", plot_address="1 Inspect Rd",
            plot_gps_lat=9.0, plot_gps_lng=38.7, height_m=5.0,
            floors_above=1, floor_area_sqm=100.0, intended_use="Residential",
            architect_name="Arch", architect_license="L-001", project_value_etb=500000,
        )
        self.inspection = Inspection.objects.create(
            application=self.app, inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=timezone.now(), assigned_inspector=self.inspector,
        )

    def test_inspection_created(self):
        self.assertEqual(self.inspection.inspection_type, "FOUNDATION")
        self.assertEqual(self.inspection.status, Inspection.Status.SCHEDULED)

    def test_inspection_str(self):
        self.assertIn("FOUNDATION", str(self.inspection))

    def test_inspection_results(self):
        self.inspection.status = Inspection.Status.PASSED
        self.inspection.save()
        self.assertEqual(self.inspection.status, "PASSED")


class InspectionChecklistTemplateModelTests(TestCase):
    def setUp(self):
        self.template = InspectionChecklistTemplate.objects.create(
            inspection_type="FOUNDATION", item_text="Check foundation depth", order=1,
        )

    def test_template_created(self):
        self.assertEqual(self.template.inspection_type, "FOUNDATION")
        self.assertTrue(self.template.is_active)


class InspectionChecklistItemModelTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            email="check@test.com", full_name="Checker",
            phone="+251911111111", password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.inspector, arn="ACPS-2026-000031",
            subcity_id="SC-01", woreda="W1", plot_address="1 Check Rd",
            plot_gps_lat=9.0, plot_gps_lng=38.7, height_m=5.0,
            floors_above=1, floor_area_sqm=100.0, intended_use="Residential",
            architect_name="Arch", architect_license="L-001", project_value_etb=500000,
        )
        self.inspection = Inspection.objects.create(
            application=self.app, inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=timezone.now(),
        )

    def test_checklist_item_created(self):
        item = InspectionChecklistItem.objects.create(
            inspection=self.inspection, item_text="Verify depth", result="PASS",
        )
        self.assertEqual(item.result, "PASS")


class InspectionPhotoModelTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            email="photo@test.com", full_name="Photo Tester",
            phone="+251911111111", password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.inspector, arn="ACPS-2026-000032",
            subcity_id="SC-01", woreda="W1", plot_address="1 Photo Rd",
            plot_gps_lat=9.0, plot_gps_lng=38.7, height_m=5.0,
            floors_above=1, floor_area_sqm=100.0, intended_use="Residential",
            architect_name="Arch", architect_license="L-001", project_value_etb=500000,
        )
        self.inspection = Inspection.objects.create(
            application=self.app, inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=timezone.now(),
        )

    def test_photo_created(self):
        photo = InspectionPhoto.objects.create(inspection=self.inspection, file="inspections/test/photo.jpg")
        self.assertIsNotNone(photo.id)


@override_settings(MEDIA_ROOT="/tmp/test_media")
class InspectionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.applicant = User.objects.create_user(
            email="app@test.com", full_name="Applicant",
            phone="+251911111111", password="pass123", role="APPLICANT",
        )
        self.inspector = User.objects.create_user(
            email="insp2@test.com", full_name="Inspector",
            phone="+251911111112", password="pass123", role="INSPECTOR",
        )
        self.senior = User.objects.create_user(
            email="senior@test.com", full_name="Senior",
            phone="+251911111113", password="pass123", role="SENIOR_OFFICER",
        )
        self.app = Application.objects.create(
            applicant=self.applicant, arn="ACPS-2026-000033",
            status=Application.Status.UNDER_CONSTRUCTION,
            subcity_id="SC-01", woreda="W1", plot_address="1 Test Rd",
            plot_gps_lat=9.0, plot_gps_lng=38.7, height_m=5.0,
            floors_above=1, floor_area_sqm=100.0, intended_use="Residential",
            architect_name="Arch", architect_license="L-001", project_value_etb=500000,
            contractor_name="Builder Inc", contractor_license="BL-001",
        )
        self.inspection = Inspection.objects.create(
            application=self.app, inspection_type=Inspection.InspectionType.FOUNDATION,
            scheduled_date=timezone.now(), assigned_inspector=self.inspector,
            status=Inspection.Status.SCHEDULED,
        )

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_inspector_schedule(self):
        self._login(self.inspector)
        resp = self.client.get("/api/v1/inspections/my-schedule/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_inspection_detail_populates_checklist(self):
        InspectionChecklistTemplate.objects.create(
            inspection_type="FOUNDATION", item_text="Check depth", order=1,
        )
        self._login(self.inspector)
        resp = self.client.get(f"/api/v1/inspections/{self.inspection.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("checklist_items", resp.data)

    def test_start_inspection(self):
        self._login(self.inspector)
        resp = self.client.post(f"/api/v1/inspections/{self.inspection.id}/start/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "IN_PROGRESS")

    def test_submit_inspection_missing_photos(self):
        self._login(self.inspector)
        resp = self.client.post(f"/api/v1/inspections/{self.inspection.id}/start/")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/api/v1/inspections/{self.inspection.id}/submit/",
                                {"overall_result": "PASSED"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("3 photos", str(resp.data["detail"]))

    def test_submit_inspection_passed(self):
        self._login(self.inspector)
        self.client.post(f"/api/v1/inspections/{self.inspection.id}/start/")
        for _ in range(3):
            img = io.BytesIO(b"fake-image-data")
            img.name = "test.png"
            self.client.post(f"/api/v1/inspections/{self.inspection.id}/photos/",
                             {"files": [img]}, format="multipart")
        resp = self.client.post(f"/api/v1/inspections/{self.inspection.id}/submit/",
                                {"overall_result": "PASSED"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["overall_result"], "PASSED")

    def test_submit_inspection_failed_requires_summary(self):
        self._login(self.inspector)
        self.client.post(f"/api/v1/inspections/{self.inspection.id}/start/")
        for _ in range(3):
            img = io.BytesIO(b"fake-image-data")
            img.name = "test.png"
            self.client.post(f"/api/v1/inspections/{self.inspection.id}/photos/",
                             {"files": [img]}, format="multipart")
        resp = self.client.post(f"/api/v1/inspections/{self.inspection.id}/submit/",
                                {"overall_result": "FAILED", "failure_summary": "Short"},
                                format="json")
        self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_access_denied(self):
        resp = self.client.get("/api/v1/inspections/my-schedule/")
        self.assertEqual(resp.status_code, 401)

    def test_applicant_cannot_start_inspection(self):
        self._login(self.applicant)
        resp = self.client.post(f"/api/v1/inspections/{self.inspection.id}/start/")
        self.assertEqual(resp.status_code, 403)
