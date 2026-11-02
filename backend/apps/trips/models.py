"""
SIH26002 — Trips models.
"""
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.drivers.models import Driver
from apps.routing.models import Route
from apps.transport_graph.models import TransportNode
from apps.vehicles.models import Vehicle, VehicleStatus


class TripStatus(models.TextChoices):
    """Lifecycle stages of a multi-modal freight trip."""
    PLANNED = "PLANNED", "Planned"
    ACTIVE = "ACTIVE", "Active / In Transit"
    PAUSED = "PAUSED", "Paused / Delayed"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Trip(BaseModel):
    """
    Core logistics trip entity tracking driver, vehicle, origin, destination,
    assigned route, and real-time state.
    """

    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips",
        db_index=True,
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips",
        db_index=True,
    )
    origin_node = models.ForeignKey(
        TransportNode,
        on_delete=models.PROTECT,
        related_name="outbound_trips",
        db_index=True,
    )
    destination_node = models.ForeignKey(
        TransportNode,
        on_delete=models.PROTECT,
        related_name="inbound_trips",
        db_index=True,
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips",
    )

    status = models.CharField(
        max_length=20,
        choices=TripStatus.choices,
        default=TripStatus.PLANNED,
        db_index=True,
    )

    # Schedule & execution
    planned_departure = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    # Immutable snapshot of the route chosen at trip initiation
    route_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of the chosen route geometry and metrics at start.",
    )

    # ── Phase 4: Route Version Tracking ──────────────────────────────────────
    route_version = models.PositiveIntegerField(
        default=1,
        help_text="Monotonically incremented each time the trip route is replaced.",
    )
    route_assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the current route was assigned to this trip.",
    )
    route_hazard_snapshot_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the hazard state at last route risk evaluation.",
    )

    # Cargo details
    cargo_description = models.CharField(max_length=255, blank=True)
    cargo_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Last reported GPS position
    current_location = gis_models.PointField(srid=4326, spatial_index=True, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "trips_trip"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "driver"]),
            models.Index(fields=["status", "vehicle"]),
        ]
        verbose_name = "Trip"
        verbose_name_plural = "Trips"

    def __str__(self) -> str:
        return (
            f"Trip {self.id} [{self.get_status_display()}]: "
            f"{self.origin_node.name} → {self.destination_node.name}"
        )

    def transition_status(self, new_status: str):
        """
        Transition trip status and perform side-effects:
        - Set departure / arrival timestamps
        - Synchronize linked Vehicle status (ON_TRIP vs AVAILABLE)
        """
        now = timezone.now()
        self.status = new_status

        if new_status == TripStatus.ACTIVE:
            if not self.actual_departure:
                self.actual_departure = now
            if self.vehicle:
                self.vehicle.status = VehicleStatus.ON_TRIP
                self.vehicle.save(update_fields=["status", "updated_at"])

        elif new_status in [TripStatus.COMPLETED, TripStatus.CANCELLED]:
            if new_status == TripStatus.COMPLETED and not self.actual_arrival:
                self.actual_arrival = now
            if self.vehicle:
                self.vehicle.status = VehicleStatus.AVAILABLE
                self.vehicle.save(update_fields=["status", "updated_at"])

        self.save()


class RerouteEventStatus(models.TextChoices):
    """Lifecycle states of a reroute event."""
    PENDING = "PENDING", "Pending — not yet sent to driver"
    SENT = "SENT", "Sent — driver notified"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged — driver responded"
    APPLIED = "APPLIED", "Applied — driver accepted new route"
    FAILED = "FAILED", "Failed — reroute calculation failed"
    DISMISSED = "DISMISSED", "Dismissed — driver declined new route"


class RerouteEvent(BaseModel):
    """
    SIH26002 Phase 4 — Auditable record of every dynamic reroute decision.

    Created whenever the hazard risk on an active trip's route increases
    materially and a safer alternative is identified. Persists for full
    auditability even if the driver declines the new route.
    """

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="reroute_events",
        db_index=True,
    )
    old_route = models.ForeignKey(
        "routing.Route",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaced_by_events",
        help_text="The route that was active before this reroute.",
    )
    new_route = models.ForeignKey(
        "routing.Route",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_by_events",
        help_text="The new safer route proposed/applied.",
    )

    trigger_reason = models.CharField(
        max_length=255,
        help_text="Human-readable reason for reroute trigger.",
    )
    triggering_edge_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of edge UUIDs whose hazard increase triggered this event.",
    )

    old_hazard_exposure = models.FloatField(
        default=0.0,
        help_text="Aggregate route hazard score before reroute.",
    )
    new_hazard_exposure = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        help_text="Aggregate route hazard score of proposed new route.",
    )
    improvement_pct = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        help_text="Fractional hazard reduction: (old - new) / old.",
    )

    # Route version at time of event — for stale detection
    trip_route_version = models.PositiveIntegerField(
        default=1,
        help_text="Value of trip.route_version when this event was created.",
    )

    status = models.CharField(
        max_length=20,
        choices=RerouteEventStatus.choices,
        default=RerouteEventStatus.PENDING,
        db_index=True,
    )

    driver_acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when driver acknowledged this reroute event.",
    )

    # Driver-facing notification payload (no internal ML details)
    notification_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured notification content for driver app.",
    )

    class Meta:
        db_table = "trips_reroute_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["trip", "status"]),
            models.Index(fields=["trip", "-created_at"]),
        ]
        verbose_name = "Reroute Event"
        verbose_name_plural = "Reroute Events"

    def __str__(self) -> str:
        return (
            f"RerouteEvent({self.trip_id} | {self.trigger_reason[:40]} | {self.status})"
        )
