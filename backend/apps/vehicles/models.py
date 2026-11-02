"""
SIH26002 — Vehicle model with PostGIS location.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.core.models import BaseModel


class VehicleType(models.TextChoices):
    MINI_TRUCK = "MINI_TRUCK", "Mini Truck (< 1T)"
    LIGHT_TRUCK = "LIGHT_TRUCK", "Light Truck (1–3.5T)"
    MEDIUM_TRUCK = "MEDIUM_TRUCK", "Medium Truck (3.5–12T)"
    HEAVY_TRUCK = "HEAVY_TRUCK", "Heavy Truck (> 12T)"
    PICKUP = "PICKUP", "Pickup / SCV"
    CONTAINER = "CONTAINER", "Container Truck"


class FuelType(models.TextChoices):
    DIESEL = "DIESEL", "Diesel"
    CNG = "CNG", "CNG"
    ELECTRIC = "ELECTRIC", "Electric"
    HYBRID = "HYBRID", "Hybrid"
    PETROL = "PETROL", "Petrol"


class VehicleStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    ASSIGNED = "ASSIGNED", "Assigned to Load"
    ON_TRIP = "ON_TRIP", "On Trip"
    OFFLINE = "OFFLINE", "Offline / No GPS"
    MAINTENANCE = "MAINTENANCE", "Under Maintenance"
    EMERGENCY = "EMERGENCY", "In Emergency / Distress"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"
    INACTIVE = "INACTIVE", "Inactive"


class Vehicle(BaseModel):
    """
    Vehicle registered in the SIH26002 platform.

    Tracks registration, capacity, current location (PostGIS Point),
    and operational status.
    """

    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
        db_index=True,
    )

    # Driver assignment
    assigned_driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_vehicles",
        db_index=True,
    )

    # Identity
    registration_number = models.CharField(max_length=20, unique=True, db_index=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    make = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)

    # Capacity
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    capacity_cbm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Fuel & Operational Efficiency
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices, default=FuelType.DIESEL)
    fuel_efficiency_kmpl = models.FloatField(
        default=4.5,
        help_text="Estimated fuel economy in km per liter under mountain corridor conditions.",
    )

    # Operational status
    status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        default=VehicleStatus.AVAILABLE,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Operating Constraints & Fleet Routing
    operating_region = models.CharField(
        max_length=100,
        default="NER_CORRIDOR",
        blank=True,
        help_text="Assigned operational sector (e.g. ASSAM_MEGHALAYA, SILCHAR_CORRIDOR)",
    )
    supported_modes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of transport modes this vehicle can operate on, e.g. ['ROAD', 'FERRY_COMPATIBLE']",
    )
    maintenance_status = models.CharField(
        max_length=50,
        default="HEALTHY",
        blank=True,
        help_text="Vehicle mechanical health: HEALTHY, DUE, CRITICAL",
    )
    availability_start = models.DateTimeField(null=True, blank=True)
    availability_end = models.DateTimeField(null=True, blank=True)

    # Current GPS location (PostGIS Point, WGS84)
    # SRID 4326 = standard GPS (longitude, latitude)
    current_location = gis_models.PointField(srid=4326, null=True, blank=True, spatial_index=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    last_gps_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vehicles_vehicle"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["vehicle_type", "is_active"]),
            models.Index(fields=["status", "is_active"]),
            models.Index(fields=["operating_region"]),
        ]
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"

    def __str__(self) -> str:
        return f"{self.registration_number} ({self.get_vehicle_type_display()})"
