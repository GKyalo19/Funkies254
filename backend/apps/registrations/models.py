"""Event registration (§4.8)."""

from django.conf import settings
from django.db import models

from apps.common.enums import RegistrationStatus
from apps.common.models import UUIDPrimaryKeyModel


class EventRegistration(UUIDPrimaryKeyModel):
    #: The status that occupies a seat; cancelled rows are kept for history.
    ACTIVE_STATUS = RegistrationStatus.REGISTERED

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registrations",
        db_column="user_id",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="registrations",
        db_column="event_id",
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.REGISTERED,
    )

    class Meta:
        db_table = "event_registrations"
        ordering = ("-registered_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "event"), name="unique_event_registration"
            )
        ]
        indexes = [
            models.Index(fields=["user"], name="registration_user_idx"),
            models.Index(fields=["event"], name="registration_event_idx"),
            models.Index(fields=["status"], name="registration_status_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.event_id} · {self.status}"

    @property
    def is_active(self) -> bool:
        return self.status == self.ACTIVE_STATUS
