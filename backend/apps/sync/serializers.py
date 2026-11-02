"""
SIH26002 — Sync Serializers.

Defines REST serializers for graph bundles, batch sync payloads, event results, and emergency beacons.
"""
from rest_framework import serializers

from apps.sync.models import (
    EmergencySOS,
    EmergencySOSStatus,
    OfflineGraphBundle,
    SyncEventStatus,
    SyncEventType,
    SyncQueueRecord,
)


class OfflineGraphVersionSerializer(serializers.ModelSerializer):
    """Metadata serializer for checking graph bundle updates without downloading payload."""

    version_tag = serializers.CharField(source="version", read_only=True)
    region = serializers.CharField(source="corridor_name", read_only=True)

    class Meta:
        model = OfflineGraphBundle
        fields = [
            "id",
            "version",
            "version_tag",
            "corridor_name",
            "region",
            "checksum_sha256",
            "node_count",
            "edge_count",
            "is_active",
            "created_at",
        ]


class OfflineGraphDownloadSerializer(serializers.ModelSerializer):
    """Full offline graph bundle serializer including node/edge payload."""

    version_tag = serializers.CharField(source="version", read_only=True)
    region = serializers.CharField(source="corridor_name", read_only=True)
    bundle_data = serializers.JSONField(source="payload", read_only=True)

    class Meta:
        model = OfflineGraphBundle
        fields = [
            "id",
            "version",
            "version_tag",
            "corridor_name",
            "region",
            "checksum_sha256",
            "node_count",
            "edge_count",
            "payload",
            "bundle_data",
            "created_at",
        ]


class SyncSingleEventSerializer(serializers.Serializer):
    """Validates individual offline event in a batch submission."""

    idempotency_key = serializers.CharField(max_length=128)
    event_type = serializers.ChoiceField(choices=SyncEventType.choices)
    client_timestamp = serializers.DateTimeField()
    payload = serializers.DictField(default=dict)


class SyncBatchRequestSerializer(serializers.Serializer):
    """Validates incoming batch of offline events."""

    events = serializers.ListField(
        child=SyncSingleEventSerializer(),
        allow_empty=False,
        help_text="List of offline queued events to process.",
    )


class SyncSingleResultSerializer(serializers.Serializer):
    """Output for individual processed event."""

    idempotency_key = serializers.CharField()
    event_type = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=SyncEventStatus.choices)
    message = serializers.CharField(required=False)
    details = serializers.DictField(required=False)
    server_state = serializers.DictField(required=False)


class SyncBatchResponseSerializer(serializers.Serializer):
    """Batch processing summary response."""

    total_events = serializers.IntegerField()
    applied_count = serializers.IntegerField()
    conflict_count = serializers.IntegerField()
    duplicate_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class EmergencySOSSerializer(serializers.ModelSerializer):
    """Emergency SOS beacon serializer."""

    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    driver_name = serializers.CharField(source="driver.name", read_only=True)

    class Meta:
        model = EmergencySOS
        fields = [
            "id",
            "driver",
            "driver_name",
            "trip",
            "status",
            "message",
            "triggered_at",
            "resolved_at",
            "metadata",
            "latitude",
            "longitude",
            "created_at",
        ]
        read_only_fields = ["id", "driver", "created_at"]
