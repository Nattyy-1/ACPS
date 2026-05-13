import uuid
from django.db import models
from django.conf import settings


class InspectionChecklistTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection_type = models.CharField(max_length=50)
    item_text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["inspection_type", "order"]

    def __str__(self):
        return f"{self.inspection_type} - #{self.order}: {self.item_text[:50]}"


class Inspection(models.Model):
    class InspectionType(models.TextChoices):
        FOUNDATION = "FOUNDATION", "Foundation Inspection"
        STRUCTURAL_FRAME = "STRUCTURAL_FRAME", "Structural Frame Inspection"
        FINAL_COMPLETION = "FINAL_COMPLETION", "Final Completion Inspection"
        RE_INSPECTION = "RE_INSPECTION", "Re-Inspection"

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        related_name="inspections",
    )
    inspection_type = models.CharField(max_length=30, choices=InspectionType.choices)
    scheduled_date = models.DateTimeField()
    assigned_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inspections",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    start_timestamp = models.DateTimeField(null=True, blank=True)
    overall_result = models.CharField(max_length=10, blank=True, default="")
    failure_summary = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.inspection_type} - {self.application.arn}"


class InspectionChecklistItem(models.Model):
    class Result(models.TextChoices):
        PASS = "PASS", "Pass"
        FAIL = "FAIL", "Fail"
        NA = "NA", "N/A"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(
        Inspection, on_delete=models.CASCADE, related_name="checklist_items"
    )
    item_template = models.ForeignKey(
        InspectionChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    item_text = models.TextField()
    result = models.CharField(
        max_length=10, choices=Result.choices, blank=True, default=""
    )
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.item_text[:40]} - {self.result}"


class InspectionPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(
        Inspection, on_delete=models.CASCADE, related_name="photos"
    )
    file = models.ImageField(upload_to="inspections/%Y/%m/%d/")
    taken_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo {self.id} - {self.inspection}"
