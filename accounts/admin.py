from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


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
