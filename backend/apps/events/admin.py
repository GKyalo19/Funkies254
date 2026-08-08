from django.contrib import admin

from .models import Category, Event


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    This is the main curation tool: toggle `is_featured` to boost an event
    in every student's recommended feed, or flip `status` to hide/cancel it.
    """

    list_display = ["title", "organizer", "location", "start_datetime", "registration_fee", "status", "is_featured"]
    list_filter = ["status", "is_featured", "education_level", "location", "categories"]
    search_fields = ["title", "description", "venue_name", "location", "organizer__name"]
    autocomplete_fields = ["organizer"]
    filter_horizontal = ["categories"]
    date_hierarchy = "start_datetime"
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["created_at", "updated_at", "created_by"]
