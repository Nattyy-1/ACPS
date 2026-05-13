from django.contrib import admin
from .models import Permit


@admin.register(Permit)
class PermitAdmin(admin.ModelAdmin):
    list_display = (
        "permit_number",
        "permit_type",
        "application",
        "status",
        "issue_date",
        "expiry_date",
    )
    list_filter = ("status", "permit_type")
    search_fields = ("permit_number", "application__arn")
    readonly_fields = ("created_at", "updated_at")
