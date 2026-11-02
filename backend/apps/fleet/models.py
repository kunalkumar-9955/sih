"""
SIH26002 — Fleet Intelligence, Load Management & Disaster Mode Models.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class CargoPriority(models.TextChoices):
    """Priority classifications for freight demands."""
    LOW = "LOW", "Low Priority / Deferred"
    NORMAL = "NORMAL", "Normal Commercial Freight"
    HIGH = "HIGH", "High Priority / Express"
    URGENT = "URGENT", "Urgent / Essential Supplies"
    EMERGENCY = "EMERGENCY", "Disaster Relief / Medical Emergency"


class CargoStatus(models.TextChoices):
    """Lifecycle stages of a freight load."""
    CREATED = "CREATED", "Created / Staged"
    AVAILABLE = "AVAILABLE", "Available for Matching"
    MATCHED = "MATCHED", "Matched to Vehicle"
    PICKED_UP = "PICKED_UP", "Picked Up / In Depot"
    IN_TRANSIT = "IN_TRANSIT", "In Transit"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired Window"


class CargoType(models.TextChoices):
    """Cargo physical classification."""
    GENERAL = "GENERAL", "General Freight"
    PERISHABLE = "PERISHABLE", "Perishable / Agricultural"
    HAZMAT = "HAZMAT", "Hazardous Material / Flammable"
    FRAGILE = "FRAGILE", "Fragile Goods"
    COLD_CHAIN = "COLD_CHAIN", "Cold Chain / Pharmaceutical"
    EMERGENCY_AID = "EMERGENCY_AID", "Disaster / Emergency Relief Aid"
    BULK = "BULK", "Heavy Bulk / Construction Material"


class FreightLoad(BaseModel):
    """
    Core freight demand entity requiring vehicle assignment and multimodal routing.
    """
    shipper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="freight_loads",
        db_index=True,
    )
    title = models.CharField(max_length=200, blank=True)
    origin_node = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.PROTECT,
        related_name="freight_loads_origin",
        db_index=True,
    )
    destination_node = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.PROTECT,
        related_name="freight_loads_destination",
        db_index=True,
    )

    cargo_type = models.CharField(
        max_length=30,
        choices=CargoType.choices,
        default=CargoType.GENERAL,
        db_index=True,
    )
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Weight in kg")
    volume_cbm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Volume in cubic meters")

    priority = models.CharField(
        max_length=20,
        choices=CargoPriority.choices,
        default=CargoPriority.NORMAL,
        db_index=True,
    )
    is_perishable = models.BooleanField(default=False, db_index=True)

    # Time Windows
    pickup_window_start = models.DateTimeField(null=True, blank=True)
    pickup_window_end = models.DateTimeField(null=True, blank=True)
    delivery_window_start = models.DateTimeField(null=True, blank=True)
    delivery_window_end = models.DateTimeField(null=True, blank=True, db_index=True)
    required_delivery_time = models.DateTimeField(null=True, blank=True)

    # Special constraints
    special_handling_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g. ['REFRIGERATION_REQUIRED', 'NO_WATERWAY_SHOCK', 'DOUBLE_TIE_DOWN']",
    )
    preferred_modes = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g. ['ROAD', 'RAIL', 'WATER']",
    )

    # Status & Assignment
    status = models.CharField(
        max_length=20,
        choices=CargoStatus.choices,
        default=CargoStatus.CREATED,
        db_index=True,
    )
    assigned_vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="freight_loads",
        db_index=True,
    )
    assigned_trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="freight_loads",
        db_index=True,
    )

    class Meta:
        db_table = "fleet_freight_load"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["origin_node", "destination_node"]),
            models.Index(fields=["delivery_window_end"]),
        ]
        verbose_name = "Freight Load"
        verbose_name_plural = "Freight Loads"

    def __str__(self) -> str:
        return f"Load #{str(self.id)[:8]} ({self.get_cargo_type_display()} - {self.weight_kg}kg - {self.priority})"


class LoadAssignment(BaseModel):
    """
    Audit record binding a FreightLoad to a Vehicle, Driver, and Trip.
    Tracks automated matching recommendations vs manual operator overrides.
    """
    load = models.ForeignKey(
        FreightLoad,
        on_delete=models.CASCADE,
        related_name="assignments",
        db_index=True,
    )
    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="load_assignments",
        db_index=True,
    )
    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="load_assignments",
    )
    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="load_assignments",
    )

    matched_score = models.FloatField(default=0.0)
    matching_factors = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed explainability breakdown of capacity, distance, safety, deadline scores",
    )

    is_manual_override = models.BooleanField(
        default=False,
        help_text="True if an operator explicitly overrode the automated ranking",
    )
    override_reason = models.TextField(blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatched_assignments",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "fleet_load_assignment"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["load", "is_active"]),
            models.Index(fields=["vehicle", "is_active"]),
        ]
        verbose_name = "Load Assignment"
        verbose_name_plural = "Load Assignments"

    def __str__(self) -> str:
        return f"Assignment(Load {str(self.load.id)[:6]} -> Vehicle {self.vehicle.registration_number})"


class MatchingRecommendation(BaseModel):
    """
    Persisted ranking candidate generated by the Automated Load Matching Engine.
    """
    load = models.ForeignKey(
        FreightLoad,
        on_delete=models.CASCADE,
        related_name="recommendations",
        db_index=True,
    )
    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="matching_recommendations",
        db_index=True,
    )
    rank = models.PositiveIntegerField(default=1)
    final_score = models.FloatField(default=0.0)

    # Subscores (0 - 100)
    capacity_score = models.FloatField(default=0.0)
    distance_score = models.FloatField(default=0.0)
    availability_score = models.FloatField(default=0.0)
    safety_score = models.FloatField(default=0.0)
    cost_score = models.FloatField(default=0.0)
    deadline_score = models.FloatField(default=0.0)
    compatibility_score = models.FloatField(default=0.0)

    estimated_cost_inr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_travel_time_min = models.FloatField(null=True, blank=True)
    explanation = models.TextField(blank=True)
    recommended_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fleet_matching_recommendation"
        ordering = ["load", "rank"]
        indexes = [
            models.Index(fields=["load", "rank"]),
        ]
        verbose_name = "Matching Recommendation"
        verbose_name_plural = "Matching Recommendations"

    def __str__(self) -> str:
        return f"Rank #{self.rank} for Load {str(self.load.id)[:6]}: {self.vehicle.registration_number} ({self.final_score:.1f})"


class DisasterFleetModeState(BaseModel):
    """
    Singleton system state managing NORMAL_OPERATIONS vs DISASTER_RESPONSE mode.
    """
    is_disaster_mode = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.CharField(max_length=255, blank=True)
    affected_corridors = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "fleet_disaster_mode_state"
        verbose_name = "Disaster Fleet Mode State"
        verbose_name_plural = "Disaster Fleet Mode States"

    @classmethod
    def get_current(cls) -> "DisasterFleetModeState":
        obj, _ = cls.objects.get_or_create(id="00000000-0000-0000-0000-000000000001")
        return obj


class OptimizationRun(BaseModel):
    """
    Audit record of a multi-vehicle / multi-depot fleet optimization or consolidation run.
    """
    class RunMode(models.TextChoices):
        FLEET_DISPATCH = "FLEET_DISPATCH", "Multi-Depot Fleet Dispatch"
        CONSOLIDATION = "CONSOLIDATION", "Dynamic Load Consolidation"
        MULTIMODAL_FLEET = "MULTIMODAL_FLEET", "Multimodal Fleet & Transfer Routing"

    class RunStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    name = models.CharField(max_length=200, blank=True)
    mode = models.CharField(
        max_length=30,
        choices=RunMode.choices,
        default=RunMode.FLEET_DISPATCH,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.PENDING,
        db_index=True,
    )

    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optimization input constraints and configuration.",
    )
    baseline_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metrics of initial/unoptimized plan.",
    )
    optimized_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metrics of optimized multi-vehicle solution.",
    )

    improvement_pct = models.FloatField(default=0.0, help_text="Composite improvement score percentage.")
    total_distance_saved_km = models.FloatField(default=0.0)
    estimated_cost_savings_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    vehicle_utilization_avg_pct = models.FloatField(default=0.0)

    assigned_loads_count = models.PositiveIntegerField(default=0)
    unassigned_loads = models.JSONField(
        default=list,
        blank=True,
        help_text="Unassigned loads with explicit constraint violation reasons.",
    )

    algorithm_used = models.CharField(max_length=100, default="clarke-wright-savings-v2")
    execution_time_ms = models.FloatField(default=0.0)
    is_simulation = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="optimization_runs",
    )

    class Meta:
        db_table = "fleet_optimization_run"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["mode", "status"]),
            models.Index(fields=["is_simulation", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"OptimizationRun #{str(self.id)[:6]} [{self.mode}]: {self.improvement_pct:.1f}% improved"


class OptimizationAssignment(BaseModel):
    """
    Vehicle route assignment generated by an OptimizationRun.
    """
    optimization_run = models.ForeignKey(
        OptimizationRun,
        on_delete=models.CASCADE,
        related_name="assignments",
        db_index=True,
    )
    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.CASCADE,
        related_name="fleet_optimization_assignments",
    )
    depot = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    assigned_loads = models.ManyToManyField(
        FreightLoad,
        related_name="fleet_optimization_assignments",
    )
    stop_sequence = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of stops (node_id, action, load_id).",
    )

    total_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_volume_cbm = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    capacity_utilization_pct = models.FloatField(default=0.0)
    total_distance_km = models.FloatField(default=0.0)
    estimated_cost_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    estimated_duration_min = models.FloatField(default=0.0)
    delay_risk_score = models.FloatField(default=0.0)

    explanation = models.TextField(
        blank=True,
        help_text="Explainable justification for this assignment sequence.",
    )

    class Meta:
        db_table = "fleet_optimization_assignment"
        ordering = ["optimization_run", "-capacity_utilization_pct"]

    def __str__(self) -> str:
        return f"Assignment for {self.vehicle.registration_number}: {self.capacity_utilization_pct:.1f}% util, {self.total_distance_km:.1f}km"


class ConsolidationBundle(BaseModel):
    """
    Consolidated multi-shipment grouping recommendation.
    """
    class BundleStatus(models.TextChoices):
        RECOMMENDED = "RECOMMENDED", "Recommended"
        ACCEPTED = "ACCEPTED", "Accepted by Operator"
        DISPATCHED = "DISPATCHED", "Dispatched to Vehicle"
        REJECTED = "REJECTED", "Rejected / Infeasible"

    bundle_code = models.CharField(max_length=64, unique=True, db_index=True)
    loads = models.ManyToManyField(
        FreightLoad,
        related_name="consolidation_bundles",
    )

    origin_hub = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    destination_hub = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    total_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_volume_cbm = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    expected_utilization_pct = models.FloatField(default=0.0)

    estimated_cost_savings_inr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        help_text="Estimated INR savings compared to separate single-load trips.",
    )
    estimated_delay_impact_min = models.FloatField(
        default=0.0,
        help_text="Estimated detour delay in minutes for multi-stop collection.",
    )
    risk_impact_score = models.FloatField(default=0.0, help_text="Route hazard risk impact delta.")

    compatibility_checks = models.JSONField(
        default=dict,
        blank=True,
        help_text="Validation results: cargo compatibility, volume/weight limits, windows.",
    )
    consolidation_reasons = models.JSONField(
        default=list,
        blank=True,
        help_text="Human-readable points explaining why loads can be bundled.",
    )

    status = models.CharField(
        max_length=20,
        choices=BundleStatus.choices,
        default=BundleStatus.RECOMMENDED,
        db_index=True,
    )
    is_estimate = models.BooleanField(
        default=True,
        help_text="Strictly True to prevent claiming fabricated savings.",
    )
    is_simulation = models.BooleanField(default=False)

    class Meta:
        db_table = "fleet_consolidation_bundle"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_simulation"]),
        ]

    def __str__(self) -> str:
        return f"Bundle {self.bundle_code} ({self.total_weight_kg}kg, ~INR {self.estimated_cost_savings_inr} saved)"
