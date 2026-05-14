import uuid
from django.db import models
from django.conf import settings


class NotificationTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(max_length=50, unique=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["notification_type"]

    def __str__(self):
        return self.notification_type


class OfficerSignature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    officer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signature",
    )
    signature_image = models.ImageField(upload_to="signatures/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Signature: {self.officer.full_name}"
