"""Event, taxonomy and saved-event admin (§17)."""

from django.contrib import admin, messages

from apps.events.models import Category, Event, EventCategory, SavedEvent, SchoolLevel
from apps.events.services import set_event_verified


class EventCategoryInline(admin.TabularInline):
    model = EventCategory
    extra = 1
    autocomplete_fields = ("category",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "institution", "start_time", "school_level", "is_verified")
    list_filter = ("is_verified", "is_virtual", "school_level", "categories", "institution")
    search_fields = ("title", "description", "venue", "location")
    date_hierarchy = "start_time"
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at", "verified_at")
    autocomplete_fields = ("institution", "created_by", "verified_by", "school_level")
    inlines = (EventCategoryInline,)
    actions = ("verify_selected",)

    @admin.action(description="Verify selected events")
    def verify_selected(self, request, queryset):
        for event in queryset:
            set_event_verified(actor=request.user, event=event, verified=True)
        self.message_user(request, f"Verified {queryset.count()} event(s).", messages.SUCCESS)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SchoolLevel)
class SchoolLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SavedEvent)
class SavedEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "saved_at")
    search_fields = ("user__email", "event__title")
    autocomplete_fields = ("user", "event")
    readonly_fields = ("id", "saved_at")
