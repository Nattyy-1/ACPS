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
        "uploader",
        "validation_status",
        "rejection_reason",
        "version_number",
        "is_current",
    )
    list_filter = ("document_type", "validation_status")
    list_editable = ("validation_status", "rejection_reason")
    search_fields = ("application__arn", "file_name", "uploader__email")
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_accepted", "mark_rejected"]

    def mark_accepted(self, request, queryset):
        updated = queryset.update(validation_status="ACCEPTED", rejection_reason="")
        self.message_user(request, f"{updated} document(s) marked as Accepted.")

    mark_accepted.short_description = "Mark selected documents as Accepted"

    def mark_rejected(self, request, queryset):
        updated = queryset.update(validation_status="REJECTED")
        self.message_user(request, f"{updated} document(s) marked as Rejected.")

    mark_rejected.short_description = "Mark selected documents as Rejected"


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
