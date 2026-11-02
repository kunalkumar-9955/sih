"""
SIH26002 — Data Ingestion, Provenance, & Scenario Models.

Implements normalized real-world data tracking for:
- External data provider registry & health metrics
- Ingestion audit logs and execution traces
- Normalized weather observations with freshness states
- Normalized terrain and InSAR deformation observations
- Controlled Demo Scenario state tracking for SIH demonstrations
"""
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class FreshnessState(models.TextChoices):
    """Lifecycle freshness classification for ingested observations."""
    FRESH = "FRESH", "Fresh (< 3 hours old)"
    AGING = "AGING", "Aging (3 to 12 hours old)"
    STALE = "STALE", "Stale (> 12 hours old, warning applied)"
    INVALID = "INVALID", "Invalid (Failed validation checks)"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable (Provider unreachable)"


class ProviderSourceType(models.TextChoices):
    """Domain categorization of external data sources."""
    WEATHER = "WEATHER", "Meteorological Data (IMD / Open-Meteo / Sensors)"
    TERRAIN = "TERRAIN", "Geological / InSAR / DEM (ISRO Bhuvan / Sentinel-1)"
    ROAD = "ROAD", "Road Network & Maintenance (PM Gati Shakti / PWD)"
    RAIL = "RAIL", "Railway Freight & Terminals (FOIS)"
    WATERWAY = "WATERWAY", "Inland Waterways & Jetties (IWAI NW-2)"
    INCIDENT = "INCIDENT", "Disaster & Emergency Reports (MDoNER / SDMA)"


class DataProvider(BaseModel):
    """
    Registry of external and federated real-world data sources.
    Tracks authentication, sync frequency, reliability metrics, and fallback status.
    """

    source_code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    source_type = models.CharField(max_length=32, choices=ProviderSourceType.choices, db_index=True)
    version = models.CharField(max_length=32, default="v1.0")
    base_url = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    is_mock_fallback = models.BooleanField(
        default=False,
        help_text="True if currently operating on deterministic synthetic data due to offline/private access",
    )
    last_successful_sync = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    sync_interval_min = models.PositiveIntegerField(default=60)
    provenance_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="License, publisher, citation, or API specifications",
    )

    class Meta:
        db_table = "ingestion_dataprovider"
        ordering = ["source_type", "source_code"]
        verbose_name = "Data Provider"
        verbose_name_plural = "Data Providers"

    def __str__(self) -> str:
        status_tag = "FALLBACK" if self.is_mock_fallback else ("ACTIVE" if self.is_active else "INACTIVE")
        return f"{self.name} [{self.source_code}] ({status_tag})"


class IngestionLog(BaseModel):
    """
    Execution trace of a periodic or manual data sync run.
    """

    class IngestionStatus(models.TextChoices):
        SUCCESS = "SUCCESS", "Completed Successfully"
        PARTIAL = "PARTIAL", "Completed with Warnings / Invalids"
        FAILED = "FAILED", "Failed Execution"

    provider = models.ForeignKey(
        DataProvider,
        on_delete=models.CASCADE,
        related_name="ingestion_logs",
        db_index=True,
    )
    status = models.CharField(max_length=20, choices=IngestionStatus.choices, default=IngestionStatus.SUCCESS)
    records_received = models.PositiveIntegerField(default=0)
    records_normalized = models.PositiveIntegerField(default=0)
    records_invalid = models.PositiveIntegerField(default=0)
    execution_duration_sec = models.FloatField(default=0.0)
    error_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_log"
        ordering = ["-created_at"]
        verbose_name = "Ingestion Log"
        verbose_name_plural = "Ingestion Logs"

    def __str__(self) -> str:
        return f"Ingest({self.provider.source_code} @ {self.created_at.strftime('%Y-%m-%d %H:%M')}: {self.status})"


class NormalizedWeatherRecord(BaseModel):
    """
    Normalized, PostGIS-validated meteorological observation.
    """

    edge = models.ForeignKey(
        "transport_graph.TransportEdge",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="normalized_weather",
        db_index=True,
    )
    location = gis_models.PointField(srid=4326, null=True, blank=True, spatial_index=True)
    rainfall_1h_mm = models.FloatField(default=0.0)
    rainfall_6h_mm = models.FloatField(default=0.0)
    rainfall_24h_mm = models.FloatField(default=0.0)
    precipitation_probability = models.FloatField(default=0.0)
    temperature_c = models.FloatField(null=True, blank=True)
    humidity_pct = models.FloatField(null=True, blank=True)
    wind_speed_mps = models.FloatField(default=0.0)
    weather_severity = models.CharField(max_length=32, default="CLEAR")
    observation_time = models.DateTimeField(db_index=True)
    freshness_state = models.CharField(
        max_length=20,
        choices=FreshnessState.choices,
        default=FreshnessState.FRESH,
        db_index=True,
    )
    provider_source = models.CharField(max_length=64, default="IMD_WEATHER")
    provenance = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_weather_record"
        ordering = ["-observation_time"]
        indexes = [
            models.Index(fields=["edge", "-observation_time"]),
            models.Index(fields=["freshness_state", "-observation_time"]),
        ]
        verbose_name = "Normalized Weather Record"
        verbose_name_plural = "Normalized Weather Records"


class NormalizedTerrainRecord(BaseModel):
    """
    Normalized geological, elevation, and Sentinel-1 InSAR ground deformation record.
    """

    edge = models.ForeignKey(
        "transport_graph.TransportEdge",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="normalized_terrain",
        db_index=True,
    )
    location = gis_models.PointField(srid=4326, null=True, blank=True, spatial_index=True)
    elevation_m = models.FloatField(default=0.0)
    slope_deg = models.FloatField(default=0.0)
    surface_deformation_mm_yr = models.FloatField(
        default=0.0,
        help_text="InSAR surface displacement velocity in mm/year (negative indicates subsidence/downslope creep)",
    )
    soil_moisture_index = models.FloatField(default=0.30)
    rockfall_hazard_indicator = models.FloatField(default=0.10)
    freshness_state = models.CharField(
        max_length=20,
        choices=FreshnessState.choices,
        default=FreshnessState.FRESH,
        db_index=True,
    )
    provider_source = models.CharField(max_length=64, default="BHUVAN_TERRAIN")
    observation_time = models.DateTimeField(default=timezone.now, db_index=True)
    provenance = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_terrain_record"
        ordering = ["-observation_time"]
        indexes = [
            models.Index(fields=["edge", "-observation_time"]),
        ]
        verbose_name = "Normalized Terrain Record"
        verbose_name_plural = "Normalized Terrain Records"


class DemoScenarioRecord(BaseModel):
    """
    Controlled simulation scenario state for reproducible SIH jury demonstrations.
    Guarantees full transparency by flagging mock/scenario states as DEMO.
    """

    name = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.CharField(max_length=128, default="ADMIN")
    affected_edges_count = models.PositiveIntegerField(default=0)
    affected_edge_ids = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Simulated rainfall, hazard shock multipliers, or blocked edge IDs",
    )

    class Meta:
        db_table = "ingestion_demo_scenario"
        ordering = ["name"]
        verbose_name = "Demo Scenario Record"
        verbose_name_plural = "Demo Scenario Records"

    def __str__(self) -> str:
        state = "ACTIVE" if self.is_active else "INACTIVE"
        return f"Scenario({self.name} | {state})"
