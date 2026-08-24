"""Audit log admin — read-only by design (§17)."""

from django.contrib import admin

from apps.common.models import AdminActivityLog


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "table_name", "record_id")
    list_filter = ("action", "table_name")
    search_fields = ("user__email", "record_id", "table_name")
    date_hierarchy = "created_at"
    readonly_fields = ("id", "user", "action", "table_name", "record_id", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
