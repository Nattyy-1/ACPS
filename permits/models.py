import uuid
from django.db import models
from django.conf import settings


class Permit(models.Model):
    class PermitType(models.TextChoices):
        PLANNING_CONSENT = "PLANNING_CONSENT", "Planning Consent"
        CONSTRUCTION = "CONSTRUCTION", "Construction Permit"
        COMPLETION = "COMPLETION", "Completion Certificate"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        related_name="permits",
    )
    permit_number = models.CharField(max_length=30, unique=True)
    permit_type = models.CharField(max_length=20, choices=PermitType.choices)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="issued_permits",
    )
    issue_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    document_path = models.FileField(upload_to="permits/%Y/%m/%d/", blank=True)
    qr_code_token = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.permit_number} ({self.permit_type})"
