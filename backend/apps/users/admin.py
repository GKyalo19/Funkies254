"""User admin (§17)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.users.models import User


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "name")


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreateForm
    form = UserEditForm
    model = User

    list_display = (
        "email",
        "name",
        "role",
        "institution_affiliation",
        "institution",
        "email_verified",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_active", "email_verified", "is_staff", "institution")
    search_fields = ("email", "name", "institution_affiliation")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
    autocomplete_fields = ("institution",)

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Profile",
            {"fields": ("name", "avatar_url", "role", "institution_affiliation", "institution")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "role",
                    "institution_affiliation",
                    "institution",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.email_verified = True
        super().save_model(request, obj, form, change)
