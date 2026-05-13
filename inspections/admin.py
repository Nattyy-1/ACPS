from django.contrib import admin
from .models import (
    Inspection,
    InspectionChecklistItem,
    InspectionPhoto,
    InspectionChecklistTemplate,
)


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = (
        "inspection_type",
        "application",
        "assigned_inspector",
        "status",
        "scheduled_date",
    )
    list_filter = ("status", "inspection_type")
    search_fields = ("application__arn",)
    readonly_fields = ("start_timestamp", "submitted_at")


@admin.register(InspectionChecklistItem)
class InspectionChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("inspection", "item_text", "result")
    list_filter = ("result",)


@admin.register(InspectionPhoto)
class InspectionPhotoAdmin(admin.ModelAdmin):
    list_display = ("inspection", "taken_at")


@admin.register(InspectionChecklistTemplate)
class InspectionChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("inspection_type", "item_text", "order", "is_active")
    list_filter = ("inspection_type", "is_active")
    ordering = ("inspection_type", "order")
