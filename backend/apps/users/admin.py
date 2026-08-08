from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Reuses Django's battle-tested UserAdmin UI but points every field
    reference at our email-based model instead of the default username one.
    """

    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "institution", "education_level", "is_staff", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_active", "education_level"]
    search_fields = ["email", "first_name", "last_name", "institution"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "institution", "education_level", "phone_number", "avatar_url")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    readonly_fields = ["date_joined", "last_login"]
