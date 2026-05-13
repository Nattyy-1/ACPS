from django.contrib import admin
from .models import ReviewComment, SLAConfig


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "category",
        "author",
        "resolution_status",
        "created_at",
    )
    list_filter = ("category", "resolution_status")
    search_fields = ("application__arn", "content")


@admin.register(SLAConfig)
class SLAConfigAdmin(admin.ModelAdmin):
    list_display = ("stage", "target_days", "reminder_days", "escalation_days")
