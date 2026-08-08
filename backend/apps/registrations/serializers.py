from rest_framework import serializers

from apps.events.models import Event
from apps.events.serializers import EventListSerializer

from .models import Registration


class RegistrationSerializer(serializers.ModelSerializer):
    event = EventListSerializer(read_only=True)
    event_slug = serializers.SlugRelatedField(
        source="event", slug_field="slug", queryset=Event.objects.all(), write_only=True
    )

    class Meta:
        model = Registration
        fields = ["id", "event", "event_slug", "status", "registered_at"]
        read_only_fields = ["id", "status", "registered_at"]

    def validate_event_slug(self, event):
        if event.status != "published":
            raise serializers.ValidationError("This event is not open for registration.")
        if event.is_past:
            raise serializers.ValidationError("This event has already happened.")
        if event.capacity is not None and event.spots_left <= 0:
            raise serializers.ValidationError("This event is fully booked.")
        return event

    def create(self, validated_data):
        user = self.context["request"].user
        event = validated_data["event"]
        registration, _created = Registration.objects.update_or_create(
            user=user, event=event, defaults={"status": "registered"}
        )
        return registration
