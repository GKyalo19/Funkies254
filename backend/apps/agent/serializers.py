"""Review-queue serializers."""

from rest_framework import serializers

from apps.agent.models import Proposal
from apps.events.serializers import EventSerializer


class ProposalSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.name", read_only=True)

    class Meta:
        model = Proposal
        fields = (
            "id",
            "kind",
            "status",
            "payload",
            "source_url",
            "external_mentions",
            "event",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        )
        read_only_fields = fields
