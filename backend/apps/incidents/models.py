"""
SIH26002 — Disruption Scenario Simulator Models.

Provides models to capture simulated natural disasters, corridor blockages,
and infrastructure outages strictly isolated from production state.
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class ScenarioType(models.TextChoices):
    NORMAL = "NORMAL", "Normal Baseline Network"
    HEAVY_RAINFALL = "HEAVY_RAINFALL", "Monsoon Heavy Rainfall (IMD Red Alert)"
    LANDSLIDE = "LANDSLIDE", "Major Landslide Corridor Blockage"
    FLOOD = "FLOOD", "Brahmaputra Basin Flood"
    ROAD_CLOSURE = "ROAD_CLOSURE", "National Highway Road Closure"
    BRIDGE_CLOSURE = "BRIDGE_CLOSURE", "Strategic Bridge Outage"
    RAILWAY_DISRUPTION = "RAILWAY_DISRUPTION", "NF Railway Siding / Track Breach"
    WATERWAY_RESTRICTION = "WATERWAY_RESTRICTION", "NW-2 Waterway Low Draft Restriction"
    TERMINAL_OUTAGE = "TERMINAL_OUTAGE", "Multimodal Terminal Shutdown"
    CONNECTIVITY_DEGRADATION = "CONNECTIVITY_DEGRADATION", "Telecom & Sensor Network Blackout"
    CRITICAL_CORRIDOR = "CRITICAL_CORRIDOR", "Multi-Hazard Simultaneous Critical Corridor Failure"


DisruptionScenarioType = ScenarioType


class DisruptionSimulationRun(BaseModel):
    """
    Isolated scenario simulation run.
    Calculates the systemic network impacts of natural hazards, infrastructure failures,
    or multimodal terminal outages without mutating live production state.
    """
    scenario_name = models.CharField(max_length=200)
    scenario_type = models.CharField(
        max_length=40,
        choices=ScenarioType.choices,
        default=ScenarioType.HEAVY_RAINFALL,
        db_index=True,
    )
    severity_level = models.CharField(max_length=20, default="HIGH")  # LOW, MEDIUM, HIGH, CATASTROPHIC
    target_corridor = models.CharField(max_length=100, blank=True, help_text="e.g. NH-6, NH-27, NW-2")
    target_state = models.CharField(max_length=50, blank=True)

    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Simulated rainfall mm, affected edge IDs, blocked bridges, etc.",
    )

    # Network-wide impact calculations
    affected_edges_count = models.PositiveIntegerField(default=0)
    affected_nodes_count = models.PositiveIntegerField(default=0)
    impacted_shipments_count = models.PositiveIntegerField(default=0)
    impacted_vehicles_count = models.PositiveIntegerField(default=0)

    # Quantitative resilience metrics
    pre_disruption_accessibility_score = models.FloatField(default=100.0)
    post_disruption_accessibility_score = models.FloatField(default=100.0)
    accessibility_delta_pct = models.FloatField(default=0.0)

    multimodal_redundancy_before = models.FloatField(default=100.0)
    multimodal_redundancy_after = models.FloatField(default=100.0)
    redundancy_delta_pct = models.FloatField(default=0.0)

    estimated_network_delay_hours = models.FloatField(default=0.0)
    alternative_routes_available = models.PositiveIntegerField(default=0)

    impact_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured summary of affected corridors, vulnerable nodes, and detour routes.",
    )

    recovery_recommendations = models.JSONField(
        default=list,
        blank=True,
        help_text="Prioritized operational and infrastructure recovery actions.",
    )

    is_simulation = models.BooleanField(
        default=True,
        editable=False,
        help_text="Always True — strictly distinguishes simulation from live state.",
    )
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulations",
    )

    class Meta:
        db_table = "incidents_disruption_simulation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scenario_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Simulation #{str(self.id)[:6]} [{self.scenario_type}]: {self.accessibility_delta_pct:+.1f}% accessibility"


class SimulationImpact(BaseModel):
    """
    Detailed per-corridor or per-asset impact recorded during a simulation run.
    """
    simulation = models.ForeignKey(
        DisruptionSimulationRun,
        on_delete=models.CASCADE,
        related_name="impacts",
    )
    entity_type = models.CharField(max_length=30)  # EDGE, NODE, SHIPMENT, VEHICLE, CORRIDOR
    entity_id = models.CharField(max_length=64)
    entity_name = models.CharField(max_length=200, blank=True)

    impact_type = models.CharField(max_length=40)  # BLOCKED, DELAYED, REROUTED, ISOLATED
    hazard_score_delta = models.FloatField(default=0.0)
    delay_added_min = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "incidents_simulation_impact"
        ordering = ["simulation", "-delay_added_min"]

    def __str__(self) -> str:
        return f"{self.entity_type} {self.entity_id} impacted: {self.impact_type} (+{self.delay_added_min:.0f}m)"
