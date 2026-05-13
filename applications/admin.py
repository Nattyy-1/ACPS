from django.contrib import admin
from .models import Application, Document, ApplicationHistory, NeighborConsent


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("arn", "applicant", "building_category", "status", "created_at")
    list_filter = ("status", "building_category")
    search_fields = ("arn", "applicant__email")
    readonly_fields = (
        "arn",
        "calculated_fee",
        "revision_cycle",
        "created_at",
        "updated_at",
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "document_type",
        "application",
        "validation_status",
        "version_number",
        "is_current",
    )
    list_filter = ("document_type", "validation_status")
    search_fields = ("application__arn", "file_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ApplicationHistory)
class ApplicationHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "previous_status",
        "new_status",
        "actor",
        "created_at",
    )
    list_filter = ("new_status",)
    search_fields = ("application__arn",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NeighborConsent)
class NeighborConsentAdmin(admin.ModelAdmin):
    list_display = ("neighbor_name", "application", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("neighbor_name", "application__arn")
