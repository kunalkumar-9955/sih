"""
SIH26002 — Hazard Intelligence & Risk Prediction Models.

Defines spatial and temporal entities for:
- HazardSeverity: Centralized risk classification with configurable thresholds
- HazardScore: Edge-level predicted risk index, confidence, validity, and metadata
- WeatherObservation: Weather readings and forecasts (precipitation, intensity)
- TerrainFeature: Geological, elevation, slope, and soil characteristics
- HazardIncident: Verified and driver-reported historical and active incidents
- HazardModelRecord: ML model registry tracking algorithm, version, metrics, and artifacts
"""
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.transport_graph.models import TransportEdge


class HazardSeverity(models.TextChoices):
    """
    Centralized severity classification across backend, API, web, and mobile.
    """
    LOW = "LOW", "Low Risk"
    MODERATE = "MODERATE", "Moderate Risk"
    HIGH = "HIGH", "High Risk"
    CRITICAL = "CRITICAL", "Critical Risk"

    @classmethod
    def get_thresholds(cls) -> Dict[str, float]:
        """
        Retrieves configurable severity thresholds from Django settings,
        defaulting to standard NER corridor safety boundaries.
        """
        config = getattr(settings, "HAZARD_SEVERITY_THRESHOLDS", {})
        return {
            "MODERATE": float(config.get("MODERATE", 0.25)),
            "HIGH": float(config.get("HIGH", 0.55)),
            "CRITICAL": float(config.get("CRITICAL", 0.85)),
        }

    @classmethod
    def classify(cls, score: float) -> str:
        """
        Deterministic classification of hazard score H in [0.0, 1.0].
        """
        score = max(0.0, min(1.0, float(score)))
        thresholds = cls.get_thresholds()

        if score >= thresholds["CRITICAL"]:
            return cls.CRITICAL
        elif score >= thresholds["HIGH"]:
            return cls.HIGH
        elif score >= thresholds["MODERATE"]:
            return cls.MODERATE
        return cls.LOW


class HazardScore(BaseModel):
    """
    Historical and real-time hazard evaluation for a transport edge.
    Supports versioned ML predictions, confidence levels, and stale tracking.
    """
    edge = models.ForeignKey(
        TransportEdge,
        on_delete=models.CASCADE,
        related_name="hazard_scores",
        db_index=True,
    )
    hazard_index = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        db_index=True,
        help_text="Predicted hazard index H in range [0.0, 1.0]",
    )
    confidence = models.FloatField(
        default=0.85,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Model prediction confidence in range [0.0, 1.0]",
    )
    severity = models.CharField(
        max_length=20,
        choices=HazardSeverity.choices,
        default=HazardSeverity.LOW,
        db_index=True,
    )
    model_version = models.CharField(
        max_length=64,
        default="baseline-v1",
        help_text="Model registry identifier that produced this prediction",
    )
    feature_version = models.CharField(
        max_length=32,
        default="fv1",
    )
    predicted_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp after which prediction is considered stale",
    )
    source = models.CharField(
        max_length=64,
        default="ml_inference",
        help_text="Data origin: ml_inference, weather_propagation, manual_override, fallback",
    )
    contributing_factors = models.JSONField(
        default=dict,
        blank=True,
        help_text="Feature contributions to the hazard score (e.g. recent rainfall, slope)",
    )
    features_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Normalized input feature snapshot utilized during inference",
    )
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True if this is the active operational score for the edge",
    )

    class Meta:
        ordering = ["-predicted_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hazard_index__gte=0.0) & models.Q(hazard_index__lte=1.0),
                name="hazard_index_range_0_to_1",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0.0) & models.Q(confidence__lte=1.0),
                name="hazard_confidence_range_0_to_1",
            ),
        ]
        indexes = [
            models.Index(fields=["edge", "is_current"]),
            models.Index(fields=["edge", "-predicted_at"]),
        ]

    def __str__(self) -> str:
        return f"HazardScore({self.edge_id} -> H={self.hazard_index:.2f} [{self.severity}])"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Automatically assign severity according to centralized thresholds
        self.severity = HazardSeverity.classify(self.hazard_index)
        # Default validity window: 6 hours if not specified
        if not self.valid_until:
            freshness_hours = getattr(settings, "HAZARD_PREDICTION_VALIDITY_HOURS", 6)
            self.valid_until = self.predicted_at + timedelta(hours=freshness_hours)
        super().save(*args, **kwargs)

    @property
    def is_stale(self) -> bool:
        """Indicates whether this prediction has expired past its validity window."""
        if not self.valid_until:
            return False
        return timezone.now() > self.valid_until


class WeatherObservation(BaseModel):
    """
    Observed or forecasted meteorological measurements associated with edges or spatial coordinates.
    """
    edge = models.ForeignKey(
        TransportEdge,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="weather_observations",
        db_index=True,
    )
    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
    )
    rainfall_mm = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Instantaneous or latest rainfall reading in mm",
    )
    rainfall_1h_mm = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Accumulated rainfall in the past 1 hour (mm)",
    )
    rainfall_6h_mm = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Accumulated rainfall in the past 6 hours (mm)",
    )
    rainfall_24h_mm = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Accumulated rainfall in the past 24 hours (mm)",
    )
    temperature_c = models.FloatField(
        null=True,
        blank=True,
        help_text="Ambient surface temperature in Celsius",
    )
    humidity_pct = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Relative humidity percentage [0-100]",
    )
    precipitation_probability = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    observation_time = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    source = models.CharField(
        max_length=64,
        default="SYNTHETIC_DEMO",
        help_text="Weather observation source: SYNTHETIC_DEMO, IMD_API, OPENMETEO, AWS_SENSOR",
    )
    is_forecast = models.BooleanField(
        default=False,
        help_text="True if this record represents a forward forecast, False if observation",
    )

    class Meta:
        ordering = ["-observation_time"]
        indexes = [
            models.Index(fields=["edge", "-observation_time"]),
        ]

    def __str__(self) -> str:
        return f"Weather(edge={self.edge_id}, 24h={self.rainfall_24h_mm}mm @ {self.observation_time})"


class TerrainFeature(BaseModel):
    """
    Physical terrain, soil, and geological attributes of a transport edge.
    """
    edge = models.OneToOneField(
        TransportEdge,
        on_delete=models.CASCADE,
        related_name="terrain_feature",
    )
    slope_deg = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(90.0)],
        help_text="Average gradient slope in degrees [0.0 - 90.0]",
    )
    elevation_m = models.FloatField(
        default=100.0,
        help_text="Mean elevation in meters above sea level",
    )
    elevation_change_m = models.FloatField(
        default=0.0,
        help_text="Total elevation ascent/descent delta along edge (meters)",
    )
    soil_type = models.CharField(
        max_length=64,
        default="sandy_loam",
        help_text="Soil taxonomy: clay, sandy_loam, silt, rocky, gravel",
    )
    soil_saturation = models.FloatField(
        default=0.30,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Estimated pore-water soil saturation index [0.0 - 1.0]",
    )
    drainage_density = models.FloatField(
        default=1.2,
        help_text="Regional stream/drainage channel density (km/km²)",
    )
    fault_line_distance_km = models.FloatField(
        default=15.0,
        validators=[MinValueValidator(0.0)],
        help_text="Distance to closest documented tectonic lineament/fault (km)",
    )
    source = models.CharField(
        max_length=64,
        default="SYNTHETIC_DEMO",
        help_text="Origin of terrain data: SYNTHETIC_DEMO, SRTM_DEM, BHUVAN_ISRO",
    )

    def __str__(self) -> str:
        return f"Terrain(edge={self.edge_id}, slope={self.slope_deg}°, elev={self.elevation_m}m)"


class HazardIncident(BaseModel):
    """
    Disruption and hazard events (historical and crowd-sourced active reports).
    """
    class IncidentType(models.TextChoices):
        LANDSLIDE = "LANDSLIDE", "Landslide / Slope Failure"
        FLOOD = "FLOOD", "Flash Flood / Waterlogging"
        ROAD_WASHOUT = "ROAD_WASHOUT", "Road Washout / Bridge Collapse"
        ROCKFALL = "ROCKFALL", "Rockfall"
        OTHER = "OTHER", "Other Disruption"

    class IncidentStatus(models.TextChoices):
        REPORTED = "REPORTED", "Reported (Unverified)"
        VERIFIED = "VERIFIED", "Verified by Operations"
        RESOLVED = "RESOLVED", "Cleared / Resolved"
        REJECTED = "REJECTED", "Rejected (False Alarm)"

    class IncidentSource(models.TextChoices):
        DRIVER = "DRIVER", "Driver Mobile Report"
        OFFICIAL = "OFFICIAL", "MDoNER / State PWD Dispatch"
        IOT_SENSOR = "IOT_SENSOR", "Roadside Sensor Station"
        SYNTHETIC_DEMO = "SYNTHETIC_DEMO", "Synthetic Development Dataset"

    edge = models.ForeignKey(
        TransportEdge,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
        db_index=True,
    )
    incident_type = models.CharField(
        max_length=32,
        choices=IncidentType.choices,
        default=IncidentType.LANDSLIDE,
        db_index=True,
    )
    severity = models.CharField(
        max_length=20,
        choices=HazardSeverity.choices,
        default=HazardSeverity.MODERATE,
    )
    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
    )
    description = models.TextField(
        blank=True,
        default="",
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    rainfall_context_mm = models.FloatField(
        null=True,
        blank=True,
        help_text="Estimated 24h rainfall preceding the incident (mm)",
    )
    source = models.CharField(
        max_length=32,
        choices=IncidentSource.choices,
        default=IncidentSource.SYNTHETIC_DEMO,
    )
    status = models.CharField(
        max_length=20,
        choices=IncidentStatus.choices,
        default=IncidentStatus.VERIFIED,
        db_index=True,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reported_hazards",
    )

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["edge", "status"]),
            models.Index(fields=["-occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"Incident({self.incident_type} on edge {self.edge_id} [{self.severity}])"


class HazardModelRecord(BaseModel):
    """
    Model Registry tracking trained hazard assessment models, metadata, and actual performance metrics.
    """
    model_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )
    model_version = models.CharField(
        max_length=64,
        unique=True,
    )
    algorithm = models.CharField(
        max_length=64,
        help_text="XGBOOST, RANDOM_FOREST, ENSEMBLE",
    )
    feature_version = models.CharField(
        max_length=32,
        default="fv1",
    )
    dataset_type = models.CharField(
        max_length=32,
        default="SYNTHETIC_DEMO",
    )
    training_samples = models.IntegerField(
        default=0,
    )
    metrics = models.JSONField(
        default=dict,
        help_text="Actual evaluated metrics: precision, recall, f1, roc_auc, pr_auc, false_negatives",
    )
    feature_importances = models.JSONField(
        default=dict,
        blank=True,
        help_text="Ranking of contributing features from model training",
    )
    artifact_path = models.CharField(
        max_length=255,
        help_text="Local filesystem path to serialized model artifact",
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this is the active operational model for real-time inference",
    )
    trained_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-trained_at"]

    def __str__(self) -> str:
        status_str = "ACTIVE" if self.is_active else "INACTIVE"
        return f"HazardModelRecord({self.model_version} [{self.algorithm}] - {status_str})"
