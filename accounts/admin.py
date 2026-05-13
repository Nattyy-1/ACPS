from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, LoginAttemptLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "role", "status", "subcity_id", "is_active")
    list_filter = ("role", "status", "is_active")
    search_fields = ("email", "full_name", "phone")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name", "phone")}),
        ("Account Info", {"fields": ("role", "status", "subcity_id")}),
        ("Documents", {"fields": ("land_certificate_number", "tin")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone",
                    "password1",
                    "password2",
                    "role",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")


@admin.register(LoginAttemptLog)
class LoginAttemptLogAdmin(admin.ModelAdmin):
    list_display = ("email", "success", "ip_address", "timestamp")
    list_filter = ("success",)
    search_fields = ("email", "ip_address")
    readonly_fields = ("email", "ip_address", "success", "timestamp")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
