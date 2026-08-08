from django.contrib import admin

from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ["user", "event", "status", "registered_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "event__title"]
    autocomplete_fields = ["user", "event"]
