"""
SIH26002 — Offline Sync & Resilient Navigation Models.

Provides:
- OfflineGraphBundle: Versioned offline graph exports with SHA256 integrity checksums.
- SyncQueueRecord: Server-side audit, idempotency, and conflict history for batched client sync.
- EmergencySOS: Offline-distress and real-time emergency signals from drivers in dead zones.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class OfflineGraphBundle(BaseModel):
    """
    Versioned export bundle of the transport graph and geohazard snapshot
    downloadable by mobile clients for on-device A* navigation.
    """

    version = models.CharField(max_length=64, default="1.0.0", db_index=True)
    corridor_name = models.CharField(max_length=128, default="NER_GLOBAL", db_index=True)
    checksum_sha256 = models.CharField(max_length=64, help_text="SHA256 hex digest of the graph payload")
    node_count = models.PositiveIntegerField(default=0)
    edge_count = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True, help_text="Serialized graph nodes, edges, and hazard weights")
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "sync_offline_graph_bundle"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["corridor_name", "is_active"]),
            models.Index(fields=["version", "is_active"]),
        ]
        verbose_name = "Offline Graph Bundle"
        verbose_name_plural = "Offline Graph Bundles"

    def __str__(self) -> str:
        return f"OfflineGraph({self.corridor_name} v{self.version} | {self.node_count} nodes, {self.edge_count} edges)"

    @property
    def version_tag(self) -> str:
        return self.version

    @property
    def region(self) -> str:
        return self.corridor_name

    @property
    def bundle_data(self) -> dict:
        return self.payload


class SyncEventType(models.TextChoices):
    """Types of offline-queued synchronization events."""
    LOCATION_UPDATE = "LOCATION_UPDATE", "Location Update"
    TRIP_STATUS = "TRIP_STATUS", "Trip Status Transition"
    HAZARD_REPORT = "HAZARD_REPORT", "Driver Hazard Report"
    ROUTE_ACK = "ROUTE_ACK", "Route Acknowledgement"
    SOS_EMERGENCY = "SOS_EMERGENCY", "SOS Emergency Distress"
    LOAD_STATUS = "LOAD_STATUS", "Freight Load Status Update"
    CHECKPOST_EVENT = "CHECKPOST_EVENT", "Checkpost Verification Event"
    COLD_CHAIN_READING = "COLD_CHAIN_READING", "Cold Chain Sensor Reading"
    SMS_COMMAND = "SMS_COMMAND", "SMS Fallback Command"
    IVR_SESSION = "IVR_SESSION", "IVR Fallback Session"


class SyncEventStatus(models.TextChoices):
    """Processing and conflict resolution status."""
    APPLIED = "APPLIED", "Applied Successfully"
    CONFLICT = "CONFLICT", "Conflict Detected"
    REJECTED = "REJECTED", "Validation Rejected"
    DUPLICATE = "DUPLICATE", "Idempotent Duplicate"


class SyncQueueRecord(BaseModel):
    """
    Server audit record of every offline event synchronized by a client.
    Guarantees strict idempotency via unique idempotency_key.
    """

    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Client-generated unique UUID preventing duplicate submissions.",
    )
    event_type = models.CharField(
        max_length=32,
        choices=SyncEventType.choices,
        db_index=True,
    )
    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_records",
    )
    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_records",
    )
    client_timestamp = models.DateTimeField(
        db_index=True,
        help_text="Device timestamp when the event was generated offline.",
    )
    server_timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    payload = models.JSONField(
        default=dict,
        help_text="Full event payload submitted by client.",
    )
    status = models.CharField(
        max_length=20,
        choices=SyncEventStatus.choices,
        default=SyncEventStatus.APPLIED,
        db_index=True,
    )
    conflict_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Details of conflict resolution if conflict was detected.",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if event validation failed.",
    )

    class Meta:
        db_table = "sync_queue_record"
        ordering = ["-server_timestamp"]
        indexes = [
            models.Index(fields=["event_type", "status"]),
            models.Index(fields=["driver", "-client_timestamp"]),
            models.Index(fields=["trip", "-client_timestamp"]),
        ]
        verbose_name = "Sync Queue Record"
        verbose_name_plural = "Sync Queue Records"

    def __str__(self) -> str:
        return f"SyncEvent({self.idempotency_key[:8]} | {self.event_type} | {self.status})"


class EmergencySOSStatus(models.TextChoices):
    """Lifecycle stages of an emergency SOS signal."""
    TRIGGERED = "TRIGGERED", "Triggered / Active"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged by Control Room"
    DISPATCHED = "DISPATCHED", "Rescue / Emergency Dispatched"
    RESOLVED = "RESOLVED", "Resolved / Cleared"
    FALSE_ALARM = "FALSE_ALARM", "False Alarm / Dismissed"


class EmergencySOS(BaseModel):
    """
    Emergency distress beacon generated by drivers in network dead zones
    or during critical corridor landslides/accidents.
    """

    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.CASCADE,
        related_name="sos_events",
        db_index=True,
    )
    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sos_events",
        db_index=True,
    )
    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        spatial_index=True,
        help_text="Last known GPS or dead-reckoning position",
    )
    status = models.CharField(
        max_length=20,
        choices=EmergencySOSStatus.choices,
        default=EmergencySOSStatus.TRIGGERED,
        db_index=True,
    )
    message = models.TextField(
        blank=True,
        default="Emergency distress signal triggered by driver.",
    )
    triggered_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Phase 7: Emergency Operations Triage & Dispatch
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_sos_events",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    dispatched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatched_sos_events",
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    nearest_hub = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nearby_emergencies",
    )
    nearest_hub_distance_km = models.FloatField(null=True, blank=True)
    audit_log = models.JSONField(
        default=list,
        blank=True,
        help_text="Complete chronological audit trail of operator actions and timestamps.",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Battery level, network strength, offline queue latency, vehicle diagnostics",
    )

    class Meta:
        db_table = "sync_emergency_sos"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(fields=["status", "-triggered_at"]),
        ]
        verbose_name = "Emergency SOS Beacon"
        verbose_name_plural = "Emergency SOS Beacons"

    def __str__(self) -> str:
        return f"SOS({self.driver} @ {self.triggered_at.strftime('%Y-%m-%d %H:%M')} | {self.status})"
