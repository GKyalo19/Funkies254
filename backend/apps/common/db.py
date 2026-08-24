"""Database helpers that keep transactional code portable."""

from django.db import connection


def for_update(queryset):
    """
    Apply ``SELECT ... FOR UPDATE`` where the backend supports it.

    Supabase PostgreSQL locks the row; SQLite (local development and the test
    suite) has no row-level locking, so the queryset is returned unchanged
    instead of raising NotSupportedError.
    """
    if connection.features.has_select_for_update:
        return queryset.select_for_update()
    return queryset
