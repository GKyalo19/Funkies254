from django.conf import settings
from django.db import models


class RegistrationStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    CANCELLED = "cancelled", "Cancelled"


class Registration(models.Model):
    """A student's RSVP to an event — powers the Register button + capacity tracking."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registrations")
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="registrations")
    status = models.CharField(max_length=20, choices=RegistrationStatus.choices, default=RegistrationStatus.REGISTERED)
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "event"]
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.user} -> {self.event} ({self.status})"
