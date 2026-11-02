"""
SIH26002 — Routing models.
"""
from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.core.models import BaseModel
from apps.transport_graph.models import TransportNode


class RouteType(models.TextChoices):
    """Routing optimization strategy / policy."""
    SAFEST = "SAFEST", "Safest (Hazard-Minimizing)"
    FASTEST = "FASTEST", "Fastest (Time-Optimized)"
    CHEAPEST = "CHEAPEST", "Cheapest (Cost-Optimized)"
    MULTIMODAL = "MULTIMODAL", "Multimodal (Intermodal Transfer)"
    LOWEST_RISK = "LOWEST_RISK", "Lowest Risk (Resilience-Optimized)"
    BALANCED = "BALANCED", "Balanced (Pareto Composite)"
    EMERGENCY_CORRIDOR = "EMERGENCY_CORRIDOR", "Emergency Relief Corridor"


class Route(BaseModel):
    """
    Computed route between two transport nodes.
    Stores composite geometry, aggregate metrics, segment-level details,
    and human-readable explanation of why this path was recommended.
    """

    origin_node = models.ForeignKey(
        TransportNode,
        on_delete=models.CASCADE,
        related_name="originating_routes",
        db_index=True,
    )
    destination_node = models.ForeignKey(
        TransportNode,
        on_delete=models.CASCADE,
        related_name="destination_routes",
        db_index=True,
    )

    route_type = models.CharField(
        max_length=20,
        choices=RouteType.choices,
        default=RouteType.SAFEST,
        db_index=True,
    )

    # Computed metrics
    total_distance_m = models.FloatField(help_text="Total route distance in metres.")
    total_time_min = models.FloatField(help_text="Total estimated transit time in minutes.")
    total_cost_inr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total estimated cost in INR.",
    )
    hazard_penalty_score = models.FloatField(
        default=0.0,
        help_text="Aggregate hazard score along the route [0.0 to 1.0].",
    )

    # Multimodal & policy metadata
    modes_used = models.JSONField(
        default=list,
        help_text="Distinct transport modes utilized across this route.",
    )
    transfer_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of intermodal transfers along the route.",
    )
    explanation = models.TextField(
        blank=True,
        help_text="Contextual human-readable explanation of why this route was selected.",
    )

    # Full route geometry (LineString WGS84)
    geometry = gis_models.LineStringField(srid=4326, spatial_index=True, null=True, blank=True)

    # Ordered segment list (JSON array of segment dictionaries)
    segments = models.JSONField(
        default=list,
        help_text="List of individual edges making up this route.",
    )

    # Engine parameters used at computation time
    alpha_used = models.FloatField(
        default=1.5,
        help_text="Hazard weight alpha used during Dijkstra computation.",
    )

    # ── Phase 4: Route Safety Summary ────────────────────────────────────────
    max_hazard_score = models.FloatField(
        default=0.0,
        help_text="Maximum single-edge hazard score along this route [0.0–1.0].",
    )
    risky_edge_count = models.IntegerField(
        default=0,
        help_text="Number of edges with hazard score >= MODERATE threshold (0.25).",
    )
    critical_edge_count = models.IntegerField(
        default=0,
        help_text="Number of edges with hazard score >= CRITICAL threshold (0.85).",
    )
    safety_level = models.CharField(
        max_length=20,
        default="LOW",
        help_text="Overall route safety classification: LOW/MODERATE/HIGH/CRITICAL.",
    )

    is_current = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True if route is considered active and not superseded.",
    )
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "routing_route"
        ordering = ["-computed_at"]
        indexes = [
            models.Index(fields=["origin_node", "destination_node"]),
            models.Index(fields=["route_type", "is_current"]),
        ]
        verbose_name = "Route"
        verbose_name_plural = "Routes"

    def __str__(self) -> str:
        return (
            f"{self.get_route_type_display()} Route: {self.origin_node.name} → "
            f"{self.destination_node.name} ({self.total_distance_m / 1000.0:.1f} km, "
            f"{self.total_time_min:.0f} min)"
        )

    @property
    def risk_score(self) -> float:
        """Alias for hazard_penalty_score matching API specification."""
        return self.hazard_penalty_score

    @property
    def routing_policy(self) -> str:
        """Alias for route_type matching API specification."""
        return self.route_type


class ETAPredictionRecord(BaseModel):
    """
    Historical and predictive ETA calculation audit record.
    Stores feature inputs, delay probability, expected minutes of delay,
    confidence intervals, and explainable factor attributions.
    """
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eta_predictions",
        db_index=True,
    )
    trip_id = models.CharField(max_length=64, blank=True, db_index=True)
    vehicle_id = models.CharField(max_length=64, blank=True, db_index=True)

    origin_node = models.ForeignKey(
        TransportNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    destination_node = models.ForeignKey(
        TransportNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    departure_time = models.DateTimeField()
    base_transit_time_min = models.FloatField(help_text="Unimpeded travel time.")
    route_distance_km = models.FloatField(default=0.0)

    predicted_transit_time_min = models.FloatField(help_text="Delay-adjusted transit time in minutes.")
    predicted_eta = models.DateTimeField(db_index=True)
    delay_probability = models.FloatField(default=0.0, help_text="Estimated probability of delay [0.0 - 1.0].")
    expected_delay_min = models.FloatField(default=0.0, help_text="Expected delay in minutes beyond base transit.")
    confidence_score = models.FloatField(default=0.85, help_text="Model confidence [0.0 - 1.0].")

    # Contributing factor attributions
    contributing_factors = models.JSONField(
        default=dict,
        blank=True,
        help_text="Breakdown of delays: weather, terrain, congestion, transfer, hazard.",
    )

    model_version = models.CharField(max_length=64, default="ner-eta-v1")
    data_source_mode = models.CharField(
        max_length=32,
        default="CONFIGURED",
        help_text="REAL, CONFIGURED, SIMULATION, SYNTHETIC.",
    )

    class Meta:
        db_table = "routing_eta_prediction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["trip_id", "-created_at"]),
            models.Index(fields=["predicted_eta"]),
        ]

    def __str__(self) -> str:
        return f"ETA Pred #{str(self.id)[:6]}: +{self.expected_delay_min:.0f}m ({self.delay_probability*100:.0f}% risk)"
