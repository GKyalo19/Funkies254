"""Institution admin, including the verification action (§17)."""

from django.contrib import admin, messages

from apps.organizers.models import Institution
from apps.organizers.services import set_institution_verified


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "verified", "location", "created_at")
    list_filter = ("verified",)
    search_fields = ("name", "slug", "location", "email")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("created_by",)
    actions = ("verify_selected", "unverify_selected")

    @admin.action(description="Verify selected institutions")
    def verify_selected(self, request, queryset):
        for institution in queryset:
            set_institution_verified(
                actor=request.user, institution=institution, verified=True
            )
        self.message_user(
            request, f"Verified {queryset.count()} institution(s).", messages.SUCCESS
        )

    @admin.action(description="Remove verification from selected institutions")
    def unverify_selected(self, request, queryset):
        for institution in queryset:
            set_institution_verified(
                actor=request.user, institution=institution, verified=False
            )
        self.message_user(
            request, f"Unverified {queryset.count()} institution(s).", messages.SUCCESS
        )
