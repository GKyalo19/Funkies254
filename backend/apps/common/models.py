"""Shared abstract bases and the admin activity log (§3, §4.11)."""

import uuid

from django.conf import settings
from django.db import models

from apps.common.enums import AuditAction


class UUIDPrimaryKeyModel(models.Model):
    """UUID primary keys for every record exposed through the API (§3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AdminActivityLog(UUIDPrimaryKeyModel):
    """Append-only record of privileged actions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
        help_text="Actor; null only for deliberate system actions.",
    )
    action = models.CharField(max_length=64, choices=AuditAction.choices)
    table_name = models.CharField(max_length=64)
    record_id = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_activity_log"
        ordering = ("-created_at",)
        verbose_name = "admin activity log entry"
        verbose_name_plural = "admin activity log"
        indexes = [
            models.Index(fields=["user"], name="audit_user_idx"),
            models.Index(fields=["table_name"], name="audit_table_idx"),
            models.Index(fields=["record_id"], name="audit_record_idx"),
            models.Index(fields=["created_at"], name="audit_created_idx"),
        ]

    def __str__(self):
        return f"{self.action} on {self.table_name} ({self.record_id})"
