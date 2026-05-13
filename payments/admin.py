from django.contrib import admin
from .models import Payment, FeeSchedule


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_id",
        "application",
        "amount_etb",
        "payment_method",
        "status",
        "paid_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = ("invoice_id", "application__arn", "transaction_reference")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FeeSchedule)
class FeeScheduleAdmin(admin.ModelAdmin):
    list_display = ("min_value_etb", "max_value_etb", "fee_percentage", "fixed_fee_etb")
    list_filter = ("min_value_etb",)
