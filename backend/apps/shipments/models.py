"""
SIH26002 — Digital Shipment Documents, Tracking Timeline & Cold-Chain IoT Models.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class DocumentStatus(models.TextChoices):
    """Lifecycle status of a digital freight e-way manifest."""
    ACTIVE = "ACTIVE", "Active / In Effect"
    VERIFIED = "VERIFIED", "Verified at Checkpost"
    EXPIRED = "EXPIRED", "Expired Validity Window"
    REVOKED = "REVOKED", "Revoked / Suspended"


class TrackingEventType(models.TextChoices):
    """Shipment journey milestone events."""
    CREATED = "CREATED", "Shipment Document Created"
    PUBLISHED = "PUBLISHED", "Published to Marketplace"
    BID_ACCEPTED = "BID_ACCEPTED", "Carrier Bid Accepted"
    ASSIGNED = "ASSIGNED", "Vehicle & Driver Dispatched"
    PICKED_UP = "PICKED_UP", "Cargo Picked Up from Shipper"
    IN_TRANSIT = "IN_TRANSIT", "In Transit along Corridor"
    CHECKPOST_VERIFIED = "CHECKPOST_VERIFIED", "Inspected & Cleared at Checkpost"
    DELIVERED = "DELIVERED", "Delivered & Signed Off"


class ColdChainStatus(models.TextChoices):
    """Thermal condition status of refrigerated cargo."""
    NORMAL = "NORMAL", "Optimal / Within Safe Range"
    WARNING = "WARNING", "Thermal Variance Warning"
    CRITICAL = "CRITICAL", "Critical Thermal Breach"
    SENSOR_OFFLINE = "SENSOR_OFFLINE", "Sensor Signal Offline"


class ShipmentRiskLevel(models.TextChoices):
    """Composite shipment risk classification."""
    LOW = "LOW", "Low Risk / On Track"
    MEDIUM = "MEDIUM", "Moderate Risk / Advisory"
    HIGH = "HIGH", "High Risk / Action Needed"
    CRITICAL = "CRITICAL", "Critical Risk / Emergency Threat"


def generate_shipment_number() -> str:
    return f"SHIP-{uuid.uuid4().hex[:8].upper()}"


class DigitalShipmentDocument(BaseModel):
    """
    Cryptographically verifiable digital freight manifest / e-way document.
    Embeds an HMAC-signed opaque reference token.
    """
    shipment_number = models.CharField(
        max_length=32,
        unique=True,
        default=generate_shipment_number,
        db_index=True,
    )
    load = models.ForeignKey(
        "fleet.FreightLoad",
        on_delete=models.CASCADE,
        related_name="shipment_documents",
        null=True,
        blank=True,
        db_index=True,
    )
    listing = models.ForeignKey(
        "marketplace.MarketplaceListing",
        on_delete=models.SET_NULL,
        related_name="shipment_documents",
        null=True,
        blank=True,
    )
    shipper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issued_shipment_documents",
        db_index=True,
    )
    carrier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carrier_shipment_documents",
    )
    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipment_documents",
    )
    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipment_documents",
    )
    origin_name = models.CharField(max_length=200)
    destination_name = models.CharField(max_length=200)
    cargo_summary = models.CharField(max_length=255)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    route_version = models.CharField(max_length=32, default="1.0.0")

    # Cryptographic HMAC token (opaque, contains no plain PII)
    secure_qr_token = models.CharField(max_length=512, unique=True, db_index=True)
    qr_code_base64 = models.TextField(blank=True, help_text="Renderable Base64 PNG QR code")

    document_status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.ACTIVE,
        db_index=True,
    )
    generated_at = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "shipments_digital_document"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["document_status", "valid_until"]),
            models.Index(fields=["vehicle", "document_status"]),
        ]
        verbose_name = "Digital Shipment Document"
        verbose_name_plural = "Digital Shipment Documents"

    def __str__(self) -> str:
        return f"{self.shipment_number} ({self.cargo_summary} - {self.document_status})"


class ShipmentTrackingEvent(BaseModel):
    """
    Immutable milestone event in the end-to-end shipment lifecycle.
    """
    document = models.ForeignKey(
        DigitalShipmentDocument,
        on_delete=models.CASCADE,
        related_name="tracking_events",
        db_index=True,
    )
    event_type = models.CharField(
        max_length=32,
        choices=TrackingEventType.choices,
        db_index=True,
    )
    location_name = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "shipments_tracking_event"
        ordering = ["recorded_at"]
        indexes = [
            models.Index(fields=["document", "event_type"]),
        ]
        verbose_name = "Shipment Tracking Event"
        verbose_name_plural = "Shipment Tracking Events"

    def __str__(self) -> str:
        return f"{self.document.shipment_number} - {self.event_type} at {self.recorded_at.isoformat()}"


class ColdChainSensor(BaseModel):
    """
    IoT sensor tag attached to perishable/refrigerated cargo container.
    """
    sensor_code = models.CharField(max_length=64, unique=True, db_index=True)
    document = models.ForeignKey(
        DigitalShipmentDocument,
        on_delete=models.CASCADE,
        related_name="cold_chain_sensors",
        null=True,
        blank=True,
        db_index=True,
    )
    current_temperature = models.FloatField(default=4.0)
    current_humidity = models.FloatField(default=65.0)
    battery_percentage = models.FloatField(default=95.0)
    status = models.CharField(
        max_length=20,
        choices=ColdChainStatus.choices,
        default=ColdChainStatus.NORMAL,
        db_index=True,
    )
    min_threshold = models.FloatField(default=2.0, help_text="Minimum allowed temperature in Celsius")
    max_threshold = models.FloatField(default=8.0, help_text="Maximum allowed temperature in Celsius")
    last_reading_at = models.DateTimeField(null=True, blank=True)
    is_simulation = models.BooleanField(default=True)

    class Meta:
        db_table = "shipments_cold_chain_sensor"
        ordering = ["-created_at"]
        verbose_name = "Cold Chain Sensor"
        verbose_name_plural = "Cold Chain Sensors"

    def __str__(self) -> str:
        return f"Sensor {self.sensor_code} ({self.status} | {self.current_temperature}°C)"


class ColdChainReading(BaseModel):
    """
    Individual temperature/humidity/battery telemetry packet.
    """
    sensor = models.ForeignKey(
        ColdChainSensor,
        on_delete=models.CASCADE,
        related_name="readings",
        db_index=True,
    )
    document = models.ForeignKey(
        DigitalShipmentDocument,
        on_delete=models.CASCADE,
        related_name="cold_chain_readings",
        null=True,
        blank=True,
        db_index=True,
    )
    temperature = models.FloatField()
    humidity = models.FloatField(default=60.0)
    battery_percentage = models.FloatField(default=90.0)
    is_simulation = models.BooleanField(default=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "shipments_cold_chain_reading"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["sensor", "-recorded_at"]),
        ]
        verbose_name = "Cold Chain Reading"
        verbose_name_plural = "Cold Chain Readings"

    def __str__(self) -> str:
        return f"Reading({self.sensor.sensor_code}: {self.temperature}°C at {self.recorded_at.isoformat()})"


class ColdChainAlert(BaseModel):
    """
    Thermal breach alert with hysteresis state tracking.
    """
    sensor = models.ForeignKey(
        ColdChainSensor,
        on_delete=models.CASCADE,
        related_name="alerts",
        db_index=True,
    )
    document = models.ForeignKey(
        DigitalShipmentDocument,
        on_delete=models.CASCADE,
        related_name="cold_chain_alerts",
        null=True,
        blank=True,
        db_index=True,
    )
    severity = models.CharField(
        max_length=20,
        choices=[("WARNING", "Warning"), ("CRITICAL", "Critical Breach")],
        default="WARNING",
        db_index=True,
    )
    reading_value = models.FloatField()
    threshold_value = models.FloatField()
    message = models.TextField()
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "shipments_cold_chain_alert"
        ordering = ["-created_at"]
        verbose_name = "Cold Chain Alert"
        verbose_name_plural = "Cold Chain Alerts"

    def __str__(self) -> str:
        return f"Alert({self.severity} on {self.sensor.sensor_code}: {self.reading_value}°C vs limit {self.threshold_value}°C)"
