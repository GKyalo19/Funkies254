"""Serializers for shared resources."""

from rest_framework import serializers

from apps.common.models import AdminActivityLog


class AdminActivityLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AdminActivityLog
        fields = ("id", "actor", "action", "table_name", "record_id", "created_at")
        read_only_fields = fields

    def get_actor(self, obj):
        if not obj.user_id:
            return None
        return {
            "id": str(obj.user_id),
            "name": obj.user.name,
            "email": obj.user.email,
            "role": obj.user.role,
        }
