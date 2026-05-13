import uuid
from django.db import models
from django.conf import settings


class ReviewComment(models.Model):
    class Category(models.TextChoices):
        MISSING_INFO = "MISSING_INFO", "Missing Information"
        DRAWING_ERROR = "DRAWING_ERROR", "Drawing Error"
        CODE_NON_COMPLIANCE = "CODE_NON_COMPLIANCE", "Code Non-Compliance"
        CLARIFICATION = "CLARIFICATION", "Clarification Needed"
        OTHER = "OTHER", "Other"

    class Resolution(models.TextChoices):
        OPEN = "OPEN", "Open"
        RESOLVED = "RESOLVED", "Resolved"
        ESCALATED = "ESCALATED", "Escalated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        related_name="review_comments",
    )
    document = models.ForeignKey(
        "applications.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_comments",
    )
    category = models.CharField(max_length=30, choices=Category.choices)
    content = models.TextField()
    resolution_status = models.CharField(
        max_length=20, choices=Resolution.choices, default=Resolution.OPEN
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_comments",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} - {self.application.arn}"


class SLAConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage = models.CharField(max_length=50, unique=True)
    target_days = models.PositiveIntegerField()
    reminder_days = models.PositiveIntegerField()
    escalation_days = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SLA Configuration"
        verbose_name_plural = "SLA Configurations"

    def __str__(self):
        return f"{self.stage}: {self.target_days} days"
