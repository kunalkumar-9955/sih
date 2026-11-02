"""
SIH26002 — Vehicle serializers.
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Vehicle, VehicleStatus


class VehicleSerializer(serializers.ModelSerializer):
    """Standard vehicle serializer. Location as [lon, lat] array."""

    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    vehicle_type_display = serializers.CharField(source="get_vehicle_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_location_coords = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "owner",
            "owner_email",
            "registration_number",
            "vehicle_type",
            "vehicle_type_display",
            "make",
            "model_name",
            "year",
            "capacity_kg",
            "capacity_cbm",
            "fuel_type",
            "status",
            "status_display",
            "is_active",
            "current_location_coords",
            "location_updated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "owner_email", "created_at", "updated_at"]

    def get_current_location_coords(self, obj):
        if obj.current_location:
            return {
                "longitude": obj.current_location.x,
                "latitude": obj.current_location.y,
            }
        return None


class VehicleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new vehicle."""

    class Meta:
        model = Vehicle
        fields = [
            "registration_number",
            "vehicle_type",
            "make",
            "model_name",
            "year",
            "capacity_kg",
            "capacity_cbm",
            "fuel_type",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["owner"] = request.user
        return super().create(validated_data)


class VehicleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating vehicle details."""

    class Meta:
        model = Vehicle
        fields = [
            "make",
            "model_name",
            "year",
            "capacity_kg",
            "capacity_cbm",
            "fuel_type",
            "status",
            "is_active",
        ]

    def validate_status(self, value):
        # Cannot directly set ON_TRIP via update — that happens through trips
        if value == VehicleStatus.ON_TRIP:
            raise serializers.ValidationError(
                "Vehicle status ON_TRIP is set automatically by the trip system."
            )
        return value
