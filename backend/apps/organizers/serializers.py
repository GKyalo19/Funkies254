"""Institution serializers."""

from rest_framework import serializers

from apps.organizers.models import Institution
from apps.users.serializers import UserBriefSerializer


class InstitutionBriefSerializer(serializers.ModelSerializer):
    """Nested representation used inside event payloads."""

    class Meta:
        model = Institution
        fields = ("id", "name", "slug", "logo_url", "location", "verified")
        read_only_fields = fields


class InstitutionSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Institution
        fields = (
            "id",
            "name",
            "slug",
            "email",
            "phone",
            "logo_url",
            "location",
            "website",
            "verified",
            "created_by",
            "event_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "verified",
            "created_by",
            "event_count",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value
