import uuid
from django.db import models
from django.conf import settings


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        TELEBIRR = "TELEBIRR", "Telebirr"
        CBEBIRR = "CBEBIRR", "CBE Birr"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AWAITING_MANUAL_CONFIRMATION = (
            "AWAITING_MANUAL_CONFIRMATION",
            "Awaiting Manual Confirmation",
        )
        CONFIRMED = "CONFIRMED", "Confirmed"
        EXPIRED = "EXPIRED", "Expired"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    invoice_id = models.CharField(max_length=50, unique=True)
    amount_etb = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True, default=""
    )
    transaction_reference = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_payments",
    )
    receipt_path = models.FileField(
        upload_to="receipts/%Y/%m/%d/", blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.invoice_id} - {self.application.arn}"


class FeeSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    min_value_etb = models.DecimalField(max_digits=12, decimal_places=2)
    max_value_etb = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=4)
    fixed_fee_etb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["min_value_etb"]

    def __str__(self):
        return (
            f"ETB {self.min_value_etb} - {self.max_value_etb or '∞'}: "
            f"{self.fee_percentage * 100}% + {self.fixed_fee_etb}"
        )
