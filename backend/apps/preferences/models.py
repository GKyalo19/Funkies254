from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """
    Drives the "Preferences" page from the Figma design and is the main
    signal `apps.recommendations` uses to curate each student's home feed.

    `education_levels` / `preferred_locations` are stored as JSON lists
    (rather than a fixed choices field) because a student can select several
    tags at once (e.g. both "High School" and "College" events, or several
    cities) — mirrored directly from the multi-tag pills in the design.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preference")
    categories = models.ManyToManyField(
        "events.Category", related_name="preferred_by", blank=True,
        help_text="Combines academic subjects and activity types the student is interested in.",
    )
    education_levels = models.JSONField(default=list, blank=True, help_text='e.g. ["high_school", "college"]')
    preferred_locations = models.JSONField(default=list, blank=True, help_text='e.g. ["Nairobi", "Thika"]')
    max_days_ahead = models.PositiveIntegerField(
        default=30, help_text="Only recommend events happening within this many days."
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user}"
