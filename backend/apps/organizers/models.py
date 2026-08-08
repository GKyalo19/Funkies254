from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Organizer(models.Model):
    """
    The host behind an event — a school, club, company, or individual (e.g.
    "Brookside Kenya" on the Figma Event page). Kept separate from `User`
    because organizers are curated by admins, not self-registered students.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    logo_url = models.URLField(blank=True, help_text="Public Supabase Storage URL.")
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    years_hosting = models.PositiveIntegerField(default=0, help_text="Shown as '<n>y hosting' on the event page.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def followers_count(self):
        return self.followers.count()


class Follow(models.Model):
    """A student following an organizer, to see updates / feed boosts."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "organizer"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} follows {self.organizer}"
