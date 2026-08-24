"""Single entry point for writing audit records (§13)."""

from apps.common.enums import AuditAction
from apps.common.models import AdminActivityLog


def log_action(*, actor, action: str, instance=None, table_name=None, record_id=None):
    """
    Write one AdminActivityLog row.

    ``instance`` is the convenient form: the model's db_table and pk are
    derived from it. ``table_name``/``record_id`` allow logging a record that
    has already been deleted.
    """
    if action not in AuditAction.values:
        raise ValueError(f"Unknown audit action: {action}")

    if instance is not None:
        table_name = table_name or instance._meta.db_table
        record_id = record_id or str(instance.pk)

    return AdminActivityLog.objects.create(
        user=actor if (actor is not None and actor.is_authenticated) else None,
        action=action,
        table_name=table_name or "",
        record_id=str(record_id) if record_id is not None else None,
    )
