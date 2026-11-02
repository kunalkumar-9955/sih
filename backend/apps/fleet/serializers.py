"""
SIH26002 — DRF Serializers for Fleet Intelligence, Load Management & Emergencies.
"""
from rest_framework import serializers
from apps.fleet.models import (
    CargoPriority,
    CargoStatus,
    CargoType,
    DisasterFleetModeState,
    FreightLoad,
    LoadAssignment,
    MatchingRecommendation,
)
from apps.sync.models import EmergencySOS, EmergencySOSStatus
from apps.vehicles.models import Vehicle


class FreightLoadSerializer(serializers.ModelSerializer):
    origin_node_name = serializers.CharField(source="origin_node.name", read_only=True)
    destination_node_name = serializers.CharField(source="destination_node.name", read_only=True)
    assigned_vehicle_reg = serializers.CharField(source="assigned_vehicle.registration_number", read_only=True)

    class Meta:
        model = FreightLoad
        fields = [
            "id",
            "shipper",
            "title",
            "origin_node",
            "origin_node_name",
            "destination_node",
            "destination_node_name",
            "cargo_type",
            "weight_kg",
            "volume_cbm",
            "priority",
            "is_perishable",
            "pickup_window_start",
            "pickup_window_end",
            "delivery_window_start",
            "delivery_window_end",
            "required_delivery_time",
            "special_handling_requirements",
            "preferred_modes",
            "status",
            "assigned_vehicle",
            "assigned_vehicle_reg",
            "assigned_trip",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "assigned_vehicle", "assigned_trip", "created_at", "updated_at"]


class CreateFreightLoadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreightLoad
        fields = [
            "title",
            "origin_node",
            "destination_node",
            "cargo_type",
            "weight_kg",
            "volume_cbm",
            "priority",
            "is_perishable",
            "pickup_window_start",
            "pickup_window_end",
            "delivery_window_start",
            "delivery_window_end",
            "required_delivery_time",
            "special_handling_requirements",
            "preferred_modes",
        ]


class LoadAssignmentSerializer(serializers.ModelSerializer):
    vehicle_reg = serializers.CharField(source="vehicle.registration_number", read_only=True)
    load_title = serializers.CharField(source="load.title", read_only=True)
    driver_name = serializers.CharField(source="driver.user.email", read_only=True)

    class Meta:
        model = LoadAssignment
        fields = [
            "id",
            "load",
            "load_title",
            "vehicle",
            "vehicle_reg",
            "driver",
            "driver_name",
            "trip",
            "matched_score",
            "matching_factors",
            "is_manual_override",
            "override_reason",
            "assigned_by",
            "assigned_at",
            "is_active",
        ]
        read_only_fields = ["id", "assigned_at", "is_active"]


class ExecuteMatchRequestSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField(required=True)
    is_manual_override = serializers.BooleanField(default=False)
    override_reason = serializers.CharField(required=False, allow_blank=True, default="")


class MatchingRecommendationSerializer(serializers.ModelSerializer):
    vehicle_reg = serializers.CharField(source="vehicle.registration_number", read_only=True)
    vehicle_type = serializers.CharField(source="vehicle.vehicle_type", read_only=True)
    capacity_kg = serializers.DecimalField(source="vehicle.capacity_kg", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = MatchingRecommendation
        fields = [
            "id",
            "load",
            "vehicle",
            "vehicle_reg",
            "vehicle_type",
            "capacity_kg",
            "rank",
            "final_score",
            "capacity_score",
            "distance_score",
            "availability_score",
            "safety_score",
            "cost_score",
            "deadline_score",
            "compatibility_score",
            "estimated_cost_inr",
            "estimated_travel_time_min",
            "explanation",
            "recommended_at",
        ]


class EmergencySOSDetailSerializer(serializers.ModelSerializer):
    driver_email = serializers.CharField(source="driver.user.email", read_only=True)
    nearest_hub_name = serializers.CharField(source="nearest_hub.name", read_only=True)
    location_lat = serializers.SerializerMethodField()
    location_lon = serializers.SerializerMethodField()

    class Meta:
        model = EmergencySOS
        fields = [
            "id",
            "driver",
            "driver_email",
            "trip",
            "location_lat",
            "location_lon",
            "status",
            "message",
            "triggered_at",
            "resolved_at",
            "acknowledged_at",
            "dispatched_at",
            "nearest_hub",
            "nearest_hub_name",
            "nearest_hub_distance_km",
            "audit_log",
        ]

    def get_location_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_location_lon(self, obj):
        return obj.location.x if obj.location else None


class EmergencyActionRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["ACKNOWLEDGE", "DISPATCH", "RESOLVE", "FALSE_ALARM"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DisasterModeActivateSerializer(serializers.Serializer):
    affected_corridors = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["NH-6_SHILLONG_CORRIDOR", "BARAK_VALLEY_PASS"],
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="Severe weather emergency escalation")
