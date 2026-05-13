import uuid
from django.db import models
from django.conf import settings


class Application(models.Model):
    class Category(models.TextChoices):
        A = "A", "Category A"
        B = "B", "Category B"
        C = "C", "Category C"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        PAYMENT_EXPIRED = "PAYMENT_EXPIRED", "Payment Expired"
        AWAITING_ASSIGNMENT = "AWAITING_ASSIGNMENT", "Awaiting Assignment"
        REVISION_REQUIRED = "REVISION_REQUIRED", "Revision Required"
        AWAITING_SENIOR_APPROVAL = (
            "AWAITING_SENIOR_APPROVAL",
            "Awaiting Senior Approval",
        )
        CONSENT_ISSUED = "CONSENT_ISSUED", "Consent Issued"
        PERMIT_ISSUED = "PERMIT_ISSUED", "Permit Issued"
        UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION", "Under Construction"
        COMPLETION_DECLARED = "COMPLETION_DECLARED", "Completion Declared"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    arn = models.CharField(max_length=20, unique=True, editable=False)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    building_category = models.CharField(
        max_length=1, choices=Category.choices, blank=True
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.DRAFT
    )
    subcity_id = models.CharField(max_length=50)
    woreda = models.CharField(max_length=100)
    plot_address = models.TextField()
    plot_gps_lat = models.DecimalField(max_digits=9, decimal_places=6)
    plot_gps_lng = models.DecimalField(max_digits=9, decimal_places=6)
    height_m = models.DecimalField(max_digits=7, decimal_places=2)
    floors_above = models.PositiveIntegerField()
    floors_below = models.PositiveIntegerField(default=0)
    floor_area_sqm = models.DecimalField(max_digits=10, decimal_places=2)
    intended_use = models.CharField(max_length=255)
    architect_name = models.CharField(max_length=255)
    architect_license = models.CharField(max_length=100)
    contractor_name = models.CharField(max_length=255, blank=True, default="")
    contractor_license = models.CharField(max_length=100, blank=True, default="")
    project_value_etb = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_fee = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications",
    )
    revision_cycle = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.arn or str(self.id)

    @staticmethod
    def generate_arn():
        import datetime

        year = datetime.date.today().year
        prefix = f"ACPS-{year}-"
        last = Application.objects.filter(arn__startswith=prefix).order_by("arn").last()
        if last:
            parts = last.arn.split("-")
            next_num = int(parts[-1]) + 1
        else:
            next_num = 1
        return f"{prefix}{next_num:06d}"

    def auto_classify(self):
        floors = self.floors_above if self.floors_above else 0
        if floors <= 1:
            return self.Category.A
        elif floors <= 4:
            return self.Category.B
        return self.Category.C

    def save(self, *args, **kwargs):
        if not self.building_category:
            self.building_category = self.auto_classify()
        super().save(*args, **kwargs)

    @staticmethod
    def calculate_fee(project_value_etb):
        from decimal import Decimal

        if project_value_etb < Decimal("2500000"):
            return project_value_etb / Decimal("2000") + Decimal("300")
        from payments.models import FeeSchedule

        tier = (
            FeeSchedule.objects.filter(
                min_value_etb__lte=project_value_etb,
            )
            .filter(
                models.Q(max_value_etb__isnull=True)
                | models.Q(max_value_etb__gte=project_value_etb)
            )
            .order_by("min_value_etb")
            .first()
        )
        if tier:
            return project_value_etb * tier.fee_percentage + tier.fixed_fee_etb
        return project_value_etb / Decimal("2000") + Decimal("300")


class Document(models.Model):
    class DocumentType(models.TextChoices):
        ARCHITECTURAL = "ARCHITECTURAL", "Architectural Drawings"
        STRUCTURAL = "STRUCTURAL", "Structural Drawings"
        SANITARY = "SANITARY", "Sanitary Design"
        ELECTRICAL = "ELECTRICAL", "Electrical Design"
        SOIL_TEST = "SOIL_TEST", "Soil Test Report"
        PROFESSIONAL_LICENSE = "PROFESSIONAL_LICENSE", "Professional License"
        FIRE_SAFETY = "FIRE_SAFETY", "Fire Safety Plans"
        NATIONAL_ID = "NATIONAL_ID", "National ID/Passport"
        TIN_CERTIFICATE = "TIN_CERTIFICATE", "TIN Certificate"

    class ValidationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file_path = models.FileField(upload_to="documents/%Y/%m/%d/")
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100, blank=True, default="")
    validation_status = models.CharField(
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True, default="")
    version_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        ref = self.application.arn if self.application else self.uploader.email
        return f"{self.document_type} v{self.version_number} - {ref}"


class ApplicationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="history"
    )
    previous_status = models.CharField(max_length=30, blank=True, default="")
    new_status = models.CharField(max_length=30)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="application_actions",
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "application history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application.arn}: {self.previous_status} -> {self.new_status}"


class NeighborConsent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="neighbors"
    )
    neighbor_name = models.CharField(max_length=255)
    neighbor_phone = models.CharField(max_length=20)
    consent_file = models.FileField(upload_to="consents/%Y/%m/%d/")
    status = models.CharField(
        max_length=20,
        choices=[("UPLOADED", "Uploaded"), ("VERIFIED", "Verified")],
        default="UPLOADED",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.neighbor_name} - {self.application.arn}"
