"""Registration admin (§17)."""

from django.contrib import admin

from apps.registrations.models import EventRegistration


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "registered_at")
    list_filter = ("status", "event__institution")
    search_fields = ("user__email", "user__name", "event__title")
    autocomplete_fields = ("user", "event")
    readonly_fields = ("id", "registered_at")
