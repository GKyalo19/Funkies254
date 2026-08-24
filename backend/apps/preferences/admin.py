"""Preference admin."""

from django.contrib import admin

from apps.preferences.models import UserPreference, UserPreferenceCategory


class UserPreferenceCategoryInline(admin.TabularInline):
    model = UserPreferenceCategory
    extra = 1
    autocomplete_fields = ("category",)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "school_level", "email_notifications", "push_notifications")
    list_filter = ("school_level", "email_notifications", "push_notifications")
    search_fields = ("user__email", "user__name")
    autocomplete_fields = ("user", "school_level")
    readonly_fields = ("id",)
    inlines = (UserPreferenceCategoryInline,)
