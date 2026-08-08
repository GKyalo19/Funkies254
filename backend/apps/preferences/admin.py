from django.contrib import admin

from .models import UserPreference


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "education_levels", "preferred_locations", "max_days_ahead", "updated_at"]
    search_fields = ["user__email"]
    filter_horizontal = ["categories"]
