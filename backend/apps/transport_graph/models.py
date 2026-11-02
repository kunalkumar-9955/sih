"""
SIH26002 — Transport graph models.

Implements the multimodal transport network as a directed graph:
- TransportNode: physical location (road intersection, rail yard, port, hub, warehouse, etc.)
- TransportEdge: connection between nodes with mode (road/rail/water/transfer)

PostGIS geometry fields:
- TransportNode.geometry → Point (WGS84, SRID 4326)
- TransportEdge.geometry → LineString (WGS84, SRID 4326)

Spatial indexes are created automatically by Django's GIS backend.
"""
from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.core.models import BaseModel


class NodeType(models.TextChoices):
    """Types of nodes in the multimodal transport graph."""
    ROAD_INTERSECTION = "ROAD_INTERSECTION", "Road Intersection"
    RAIL_YARD = "RAIL_YARD", "Railway Freight Yard"
    RAIL_SIDING = "RAIL_SIDING", "Rail Siding"
    WATERWAY_TERMINAL = "WATERWAY_TERMINAL", "Inland Waterway Terminal"
    RIVER_JETTY = "RIVER_JETTY", "River Jetty"
    MULTIMODAL_HUB = "MULTIMODAL_HUB", "Multimodal Logistics Park"
    LOCAL_HUB = "LOCAL_HUB", "Local Logistics Hub"
    LOGISTICS_HUB = "LOGISTICS_HUB", "Regional Logistics Hub"
    WAREHOUSE = "WAREHOUSE", "Warehouse / Storage Depot"
    CHECKPOST = "CHECKPOST", "Road Checkpost"
    PORT = "PORT", "Port / Dock"


class TransportMode(models.TextChoices):
    """Transport modes for edges."""
    ROAD = "ROAD", "Road"
    RAIL = "RAIL", "Rail"
    WATER = "WATER", "Inland Waterway"
    WATERWAY = "WATERWAY", "Inland Waterway (Legacy Alias)"
    TRANSFER = "TRANSFER", "Transfer / Intermodal"

    @classmethod
    def normalize(cls, mode_str: str) -> str:
        """Normalizes WATERWAY -> WATER for standard internal representation."""
        if mode_str in (cls.WATER, cls.WATERWAY):
            return cls.WATER
        return mode_str


class EdgeStatus(models.TextChoices):
    """Operational status of a transport edge."""
    OPEN = "OPEN", "Open"
    RESTRICTED = "RESTRICTED", "Restricted (weight/height/hazard)"
    BLOCKED = "BLOCKED", "Blocked"
    CRITICAL = "CRITICAL", "Critically Blocked (emergency override)"
    SEASONAL = "SEASONAL", "Seasonal Closure"
    UNDER_REPAIR = "UNDER_REPAIR", "Under Repair"


class TransportNode(BaseModel):
    """
    A node in the multimodal transport graph.

    Represents any physical point where freight can originate,
    terminate, or transfer between modes.
    """

    name = models.CharField(max_length=255, db_index=True)
    short_code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    node_type = models.CharField(max_length=30, choices=NodeType.choices, db_index=True)

    # Spatial location (WGS84)
    geometry = gis_models.PointField(srid=4326, spatial_index=True)

    # Physical attributes
    elevation_m = models.FloatField(null=True, blank=True)

    # Administrative
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)

    # Operational
    is_active = models.BooleanField(default=True, db_index=True)

    # Metadata
    data_source = models.CharField(max_length=100, blank=True, default="manual")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "transport_graph_transportnode"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["node_type", "is_active"]),
            models.Index(fields=["state", "district"]),
        ]
        verbose_name = "Transport Node"
        verbose_name_plural = "Transport Nodes"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_node_type_display()})"

    @property
    def longitude(self) -> float:
        return self.geometry.x if self.geometry else 0.0

    @property
    def latitude(self) -> float:
        return self.geometry.y if self.geometry else 0.0

    @property
    def is_intermodal_hub(self) -> bool:
        """True if freight can transition between different modes here."""
        return self.node_type in (
            NodeType.MULTIMODAL_HUB,
            NodeType.LOGISTICS_HUB,
            NodeType.RAIL_YARD,
            NodeType.WATERWAY_TERMINAL,
            NodeType.RIVER_JETTY,
            NodeType.PORT,
        )


class TransportEdge(BaseModel):
    """
    A directed edge in the multimodal transport graph.

    Represents a traversable segment between two nodes.
    The routing engine uses this model directly to build the cost graph.
    """

    source_node = models.ForeignKey(
        TransportNode,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
        db_index=True,
    )
    target_node = models.ForeignKey(
        TransportNode,
        on_delete=models.CASCADE,
        related_name="incoming_edges",
        db_index=True,
    )

    mode = models.CharField(max_length=20, choices=TransportMode.choices, db_index=True)

    # Geometry (WGS84 LineString)
    geometry = gis_models.LineStringField(srid=4326, spatial_index=True, null=True, blank=True)

    # Physical properties
    distance_m = models.FloatField(help_text="Segment distance in metres.")
    base_transit_time_min = models.FloatField(
        help_text="Expected transit time in minutes under normal conditions."
    )
    cost_inr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Approximate freight cost in INR for this segment."
    )
    capacity_kg = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Maximum payload capacity for this segment in kg."
    )

    # Availability
    is_available = models.BooleanField(default=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=EdgeStatus.choices,
        default=EdgeStatus.OPEN,
        db_index=True,
    )

    # Hazard (0.0 = safe, 1.0 = maximum hazard)
    hazard_score = models.FloatField(
        default=0.0,
        help_text="Hazard score [0.0–1.0]. 0.0 = safe, 1.0 = maximum hazard.",
    )

    # Intermodal transfer properties (applicable when mode=TRANSFER)
    transfer_time_min = models.FloatField(
        null=True, blank=True,
        help_text="Time penalty for intermodal transfer at this edge (minutes)."
    )
    transfer_cost_inr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Cost of intermodal transfer in INR."
    )

    # Waterway specific constraints (applicable when mode=WATER/WATERWAY)
    water_level_m = models.FloatField(
        null=True, blank=True,
        help_text="Current navigable water level in metres (DEMO/sensor data).",
    )
    min_required_depth_m = models.FloatField(
        null=True, blank=True,
        help_text="Minimum required draft depth in metres for vessel navigation.",
    )
    draft_requirement_m = models.FloatField(
        null=True, blank=True,
        help_text="Vessel draft requirement in metres for this water segment.",
    )

    # Time-dependent operational windows
    operating_hours_start = models.TimeField(
        null=True, blank=True,
        help_text="Daily operational opening time (e.g. 06:00:00).",
    )
    operating_hours_end = models.TimeField(
        null=True, blank=True,
        help_text="Daily operational closing time (e.g. 20:00:00).",
    )
    seasonal_open_month = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Month number (1-12) when seasonal edge opens.",
    )
    seasonal_close_month = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Month number (1-12) when seasonal edge closes.",
    )

    # Metadata
    road_name = models.CharField(max_length=200, blank=True)
    data_source = models.CharField(max_length=100, blank=True, default="manual")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transport_graph_transportedge"
        ordering = ["source_node", "target_node"]
        indexes = [
            models.Index(fields=["source_node", "target_node"]),
            models.Index(fields=["mode", "is_available"]),
            models.Index(fields=["status"]),
            models.Index(fields=["hazard_score"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hazard_score__gte=0.0) & models.Q(hazard_score__lte=1.0),
                name="hazard_score_range",
            )
        ]
        verbose_name = "Transport Edge"
        verbose_name_plural = "Transport Edges"

    def __str__(self) -> str:
        return (
            f"{self.source_node.name} → {self.target_node.name} "
            f"[{self.get_mode_display()}] {self.distance_m:.0f}m"
        )

    @property
    def normalized_mode(self) -> str:
        """Returns standard normalized mode (WATER instead of WATERWAY)."""
        return TransportMode.normalize(self.mode)

    @property
    def is_waterway(self) -> bool:
        return self.mode in (TransportMode.WATER, TransportMode.WATERWAY)

    @property
    def is_transfer(self) -> bool:
        return self.mode == TransportMode.TRANSFER

    @property
    def is_traversable(self) -> bool:
        """
        Returns True if the routing engine can consider this edge under open conditions.
        BLOCKED edges are never traversable.
        """
        return self.is_available and self.status != EdgeStatus.BLOCKED
