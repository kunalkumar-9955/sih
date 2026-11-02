"""
SIH26002 — Shipment & Cold-Chain Serializers.
"""
from rest_framework import serializers
from apps.shipments.models import (
    DigitalShipmentDocument,
    ShipmentTrackingEvent,
    ColdChainSensor,
    ColdChainReading,
    ColdChainAlert,
)


class ShipmentTrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTrackingEvent
        fields = ["id", "event_type", "location_name", "latitude", "longitude", "notes", "recorded_at"]
        read_only_fields = fields


class ColdChainReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColdChainReading
        fields = ["id", "sensor", "document", "temperature", "humidity", "battery_percentage", "is_simulation", "recorded_at"]
        read_only_fields = ["id", "is_simulation", "recorded_at"]


class ColdChainAlertSerializer(serializers.ModelSerializer):
    sensor_code = serializers.ReadOnlyField(source="sensor.sensor_code")
    shipment_number = serializers.ReadOnlyField(source="document.shipment_number")

    class Meta:
        model = ColdChainAlert
        fields = [
            "id",
            "sensor",
            "sensor_code",
            "document",
            "shipment_number",
            "severity",
            "reading_value",
            "threshold_value",
            "message",
            "is_resolved",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields


class ColdChainSensorSerializer(serializers.ModelSerializer):
    alerts = ColdChainAlertSerializer(many=True, read_only=True)
    recent_readings = serializers.SerializerMethodField()

    class Meta:
        model = ColdChainSensor
        fields = [
            "id",
            "sensor_code",
            "document",
            "current_temperature",
            "current_humidity",
            "battery_percentage",
            "status",
            "min_threshold",
            "max_threshold",
            "last_reading_at",
            "is_simulation",
            "recent_readings",
            "alerts",
        ]
        read_only_fields = fields

    def get_recent_readings(self, obj: ColdChainSensor):
        readings = obj.readings.order_by("-recorded_at")[:10]
        return ColdChainReadingSerializer(readings, many=True).data


class DigitalShipmentDocumentSerializer(serializers.ModelSerializer):
    tracking_events = ShipmentTrackingEventSerializer(many=True, read_only=True)
    cold_chain_sensors = ColdChainSensorSerializer(many=True, read_only=True)
    vehicle_registration = serializers.ReadOnlyField(source="vehicle.registration_number")
    driver_name = serializers.ReadOnlyField(source="driver.name")
    shipper_email = serializers.ReadOnlyField(source="shipper.email")
    carrier_email = serializers.ReadOnlyField(source="carrier.email")

    class Meta:
        model = DigitalShipmentDocument
        fields = [
            "id",
            "shipment_number",
            "load",
            "listing",
            "shipper",
            "shipper_email",
            "carrier",
            "carrier_email",
            "vehicle",
            "vehicle_registration",
            "driver",
            "driver_name",
            "origin_name",
            "destination_name",
            "cargo_summary",
            "weight_kg",
            "route_version",
            "secure_qr_token",
            "document_status",
            "generated_at",
            "valid_until",
            "tracking_events",
            "cold_chain_sensors",
        ]
        read_only_fields = fields
