from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import ReviewComment, SLAConfig

User = get_user_model()


class ReviewCommentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reviewer@test.com",
            full_name="Reviewer",
            phone="+251911111111",
            password="pass123",
        )
        from applications.models import Application

        self.app = Application.objects.create(
            applicant=self.user,
            arn="ACPS-2026-000020",
            subcity_id="SC-01",
            woreda="W1",
            plot_address="1 Review Rd",
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
        self.comment = ReviewComment.objects.create(
            application=self.app,
            author=self.user,
            category=ReviewComment.Category.MISSING_INFO,
            content="Please upload structural drawings.",
        )

    def test_comment_created(self):
        self.assertEqual(self.comment.category, "MISSING_INFO")
        self.assertEqual(self.comment.resolution_status, ReviewComment.Resolution.OPEN)
        self.assertEqual(self.comment.content, "Please upload structural drawings.")

    def test_comment_str(self):
        self.assertEqual(str(self.comment), f"MISSING_INFO - {self.app.arn}")


class SLAConfigModelTests(TestCase):
    def setUp(self):
        self.sla = SLAConfig.objects.create(
            stage="technical_review",
            target_days=10,
            reminder_days=7,
            escalation_days=10,
        )

    def test_sla_created(self):
        self.assertEqual(self.sla.stage, "technical_review")
        self.assertEqual(self.sla.target_days, 10)

    def test_sla_str(self):
        self.assertEqual(str(self.sla), "technical_review: 10 days")
