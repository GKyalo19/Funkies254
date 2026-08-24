"""Registration serializers."""

from rest_framework import serializers

from apps.common.enums import RegistrationStatus
from apps.events.models import Event
from apps.events.serializers import EventSerializer
from apps.registrations.models import EventRegistration
from apps.users.serializers import UserBriefSerializer


class EventRegistrationSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = EventRegistration
        fields = ("id", "user", "event", "status", "registered_at")
        read_only_fields = fields


class RegistrationCreateSerializer(serializers.Serializer):
    """``POST /api/registrations/`` accepts either the event id or its slug."""

    event_id = serializers.UUIDField(required=False)
    event_slug = serializers.SlugField(required=False)

    def validate(self, attrs):
        if not attrs.get("event_id") and not attrs.get("event_slug"):
            raise serializers.ValidationError(
                {"event_id": "Provide either event_id or event_slug."}
            )

        queryset = Event.objects.visible_to(self.context["request"].user)
        event = (
            queryset.filter(pk=attrs["event_id"]).first()
            if attrs.get("event_id")
            else queryset.filter(slug=attrs["event_slug"]).first()
        )
        if event is None:
            raise serializers.ValidationError({"event_id": "Event does not exist."})

        attrs["event"] = event
        return attrs


class RegistrationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RegistrationStatus.choices)
