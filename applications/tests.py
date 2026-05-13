from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient
from .models import Application, Document, ApplicationHistory, NeighborConsent

User = get_user_model()


class ApplicationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="applicant@test.com",
            full_name="Applicant",
            phone="+251911111111",
            password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.user,
            arn="ACPS-2026-000001",
            subcity_id="SC-01",
            woreda="Woreda 1",
            plot_address="123 Main St",
            plot_gps_lat=9.0300,
            plot_gps_lng=38.7400,
            height_m=12.5,
            floors_above=3,
            floors_below=1,
            floor_area_sqm=250.0,
            intended_use="Residential",
            architect_name="Arch A",
            architect_license="AL-001",
            project_value_etb=1500000,
            building_category=Application.Category.B,
        )

    def test_application_created(self):
        self.assertEqual(self.app.arn, "ACPS-2026-000001")
        self.assertEqual(self.app.status, Application.Status.DRAFT)
        self.assertEqual(self.app.applicant, self.user)

    def test_arn_unique(self):
        with self.assertRaises(IntegrityError):
            Application.objects.create(
                applicant=self.user,
                arn="ACPS-2026-000001",
                subcity_id="SC-01",
                woreda="Woreda 1",
                plot_address="456 Other St",
                plot_gps_lat=9.0400,
                plot_gps_lng=38.7500,
                height_m=10.0,
                floors_above=2,
                floor_area_sqm=150.0,
                intended_use="Commercial",
                architect_name="Arch B",
                architect_license="AL-002",
                project_value_etb=2000000,
            )

    def test_application_str(self):
        self.assertEqual(str(self.app), "ACPS-2026-000001")

    def test_category_choices(self):
        expected = ["A", "B", "C"]
        for cat in expected:
            self.assertIn(cat, [c[0] for c in Application.Category.choices])

    def test_status_choices(self):
        expected = [
            "DRAFT",
            "PAYMENT_PENDING",
            "PAYMENT_EXPIRED",
            "AWAITING_ASSIGNMENT",
            "REVISION_REQUIRED",
            "AWAITING_SENIOR_APPROVAL",
            "CONSENT_ISSUED",
            "PERMIT_ISSUED",
            "UNDER_CONSTRUCTION",
            "COMPLETION_DECLARED",
            "COMPLETED",
            "REJECTED",
            "CANCELLED",
            "ARCHIVED",
        ]
        for s in expected:
            self.assertIn(s, [c[0] for c in Application.Status.choices])


class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="doc@test.com",
            full_name="Doc Tester",
            phone="+251911111111",
            password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.user,
            arn="ACPS-2026-000002",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Test Rd",
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
        self.doc = Document.objects.create(
            application=self.app,
            uploader=self.user,
            document_type=Document.DocumentType.ARCHITECTURAL,
            file_path="documents/test/arch.pdf",
            file_name="arch.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

    def test_document_created(self):
        self.assertEqual(self.doc.document_type, "ARCHITECTURAL")
        self.assertEqual(self.doc.validation_status, Document.ValidationStatus.PENDING)
        self.assertEqual(self.doc.version_number, 1)
        self.assertTrue(self.doc.is_current)

    def test_document_str(self):
        expected = f"ARCHITECTURAL v1 - {self.app.arn}"
        self.assertEqual(str(self.doc), expected)


class ApplicationHistoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="hist@test.com",
            full_name="History",
            phone="+251911111111",
            password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.user,
            arn="ACPS-2026-000003",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Hist Rd",
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
        self.history = ApplicationHistory.objects.create(
            application=self.app,
            previous_status="DRAFT",
            new_status="PAYMENT_PENDING",
            actor=self.user,
            note="Payment initiated",
        )

    def test_history_created(self):
        self.assertEqual(self.history.previous_status, "DRAFT")
        self.assertEqual(self.history.new_status, "PAYMENT_PENDING")
        self.assertEqual(self.history.actor, self.user)

    def test_history_str(self):
        expected = f"{self.app.arn}: DRAFT -> PAYMENT_PENDING"
        self.assertEqual(str(self.history), expected)

    def test_history_ordering(self):
        ApplicationHistory.objects.create(
            application=self.app,
            previous_status="PAYMENT_PENDING",
            new_status="AWAITING_ASSIGNMENT",
            actor=self.user,
        )
        qs = ApplicationHistory.objects.all()
        self.assertEqual(qs.first().new_status, "AWAITING_ASSIGNMENT")


class NeighborConsentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="neighbor@test.com",
            full_name="Neighbor",
            phone="+251911111111",
            password="pass123",
        )
        self.app = Application.objects.create(
            applicant=self.user,
            arn="ACPS-2026-000004",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Neighbor Rd",
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
        self.consent = NeighborConsent.objects.create(
            application=self.app,
            neighbor_name="John Neighbor",
            neighbor_phone="+251922222222",
            consent_file="consents/test/consent.pdf",
        )

    def test_consent_created(self):
        self.assertEqual(self.consent.neighbor_name, "John Neighbor")
        self.assertEqual(self.consent.status, "UPLOADED")

    def test_consent_str(self):
        self.assertEqual(str(self.consent), f"John Neighbor - {self.app.arn}")


class ApplicationCreateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/applications/"
        self.password = "pass123"
        self.applicant = User.objects.create_user(
            email="applicant@test.com",
            full_name="Test Applicant",
            phone="+251911111111",
            password=self.password,
            role=User.Role.APPLICANT,
        )

    def _auth(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "applicant@test.com", "password": self.password},
            format="json",
        )
        return f"Bearer {response.data['access']}"

    def _valid_data(self):
        return {
            "intended_use": "Residential",
            "height_m": 12.5,
            "floors_above": 3,
            "floors_below": 1,
            "floor_area_sqm": 250.0,
            "plot_address": "123 Main St",
            "plot_gps_lat": 9.0300,
            "plot_gps_lng": 38.7400,
            "subcity_id": "SC-01",
            "woreda": "Woreda 1",
            "architect_name": "Arch A",
            "architect_license": "AL-001",
            "contractor_name": "Contractor C",
            "contractor_license": "CL-001",
            "project_value_etb": 1500000,
        }

    def test_create_application_success(self):
        response = self.client.post(
            self.url, self._valid_data(), format="json", HTTP_AUTHORIZATION=self._auth()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("application_id", response.data)
        self.assertIn("arn", response.data)
        self.assertIn("status", response.data)
        self.assertIn("calculated_fee", response.data)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertTrue(response.data["arn"].startswith("ACPS-2026-"))

    def test_create_application_unauthenticated(self):
        response = self.client.post(self.url, self._valid_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_application_unauthorized_role(self):
        officer = User.objects.create_user(
            email="officer@test.com",
            full_name="Officer",
            phone="+251922222222",
            password="pass123",
            role=User.Role.REVIEW_OFFICER,
        )
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "officer@test.com", "password": "pass123"},
            format="json",
        )
        response = self.client.post(
            self.url,
            self._valid_data(),
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_application_arn_format(self):
        response = self.client.post(
            self.url, self._valid_data(), format="json", HTTP_AUTHORIZATION=self._auth()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        import re

        self.assertTrue(re.match(r"^ACPS-2026-\d{6}$", response.data["arn"]))

    def test_create_application_calculates_fee(self):
        data = self._valid_data()
        response = self.client.post(
            self.url, data, format="json", HTTP_AUTHORIZATION=self._auth()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_fee = float(1500000 / 2000 + 300)
        self.assertEqual(response.data["calculated_fee"], expected_fee)

    def test_create_application_sequential_arn(self):
        resp1 = self.client.post(
            self.url, self._valid_data(), format="json", HTTP_AUTHORIZATION=self._auth()
        )
        resp2 = self.client.post(
            self.url, self._valid_data(), format="json", HTTP_AUTHORIZATION=self._auth()
        )
        num1 = int(resp1.data["arn"].split("-")[-1])
        num2 = int(resp2.data["arn"].split("-")[-1])
        self.assertEqual(num2, num1 + 1)

    def test_auto_classify_category_a_single_story(self):
        data = self._valid_data()
        data["floors_above"] = 1
        response = self.client.post(
            self.url, data, format="json", HTTP_AUTHORIZATION=self._auth()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["building_category"], "A")

    def test_auto_classify_category_b_2_to_4_floors(self):
        for floors in [2, 3, 4]:
            data = self._valid_data()
            data["floors_above"] = floors
            response = self.client.post(
                self.url, data, format="json", HTTP_AUTHORIZATION=self._auth()
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["building_category"], "B")

    def test_auto_classify_category_c_5_plus_floors(self):
        data = self._valid_data()
        data["floors_above"] = 5
        response = self.client.post(
            self.url, data, format="json", HTTP_AUTHORIZATION=self._auth()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["building_category"], "C")
