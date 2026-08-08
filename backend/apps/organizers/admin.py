from django.contrib import admin

from .models import Follow, Organizer


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "years_hosting", "followers_count", "created_at"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["user", "organizer", "created_at"]
    search_fields = ["user__email", "organizer__name"]
