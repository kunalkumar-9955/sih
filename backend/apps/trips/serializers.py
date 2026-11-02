"""
SIH26002 — Trip serializers.
"""
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import serializers

from apps.drivers.models import Driver
from apps.routing.models import Route
from apps.routing.serializers import RouteSerializer
from apps.transport_graph.models import TransportNode
from apps.vehicles.models import Vehicle
from .models import RerouteEvent, Trip, TripStatus


class TripSerializer(serializers.ModelSerializer):
    """Full trip read serializer."""

    driver_name = serializers.SerializerMethodField()
    vehicle_registration = serializers.CharField(source="vehicle.registration_number", read_only=True)
    origin_name = serializers.CharField(source="origin_node.name", read_only=True)
    destination_name = serializers.CharField(source="destination_node.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_location_coords = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "driver",
            "driver_name",
            "vehicle",
            "vehicle_registration",
            "origin_node",
            "origin_name",
            "destination_node",
            "destination_name",
            "route",
            "status",
            "status_display",
            "planned_departure",
            "actual_departure",
            "actual_arrival",
            "route_snapshot",
            "route_version",
            "route_assigned_at",
            "route_hazard_snapshot_at",
            "cargo_description",
            "cargo_weight_kg",
            "current_location_coords",
            "last_location_update",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "route_version",
            "route_assigned_at",
            "route_hazard_snapshot_at",
            "actual_departure",
            "actual_arrival",
            "created_at",
            "updated_at",
        ]

    def get_driver_name(self, obj):
        if obj.driver and obj.driver.user:
            user = obj.driver.user
            if hasattr(user, "full_name") and user.full_name:
                return user.full_name
            if callable(getattr(user, "get_full_name", None)):
                fn = user.get_full_name()
                if fn:
                    return fn
            return user.email
        return None

    def get_current_location_coords(self, obj):
        if obj.current_location:
            return {
                "longitude": obj.current_location.x,
                "latitude": obj.current_location.y,
            }
        return None


class TripCreateSerializer(serializers.ModelSerializer):
    """Trip creation serializer."""

    class Meta:
        model = Trip
        fields = [
            "id",
            "driver",
            "vehicle",
            "origin_node",
            "destination_node",
            "route",
            "planned_departure",
            "cargo_description",
            "cargo_weight_kg",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        origin = attrs.get("origin_node")
        dest = attrs.get("destination_node")
        if origin == dest:
            raise serializers.ValidationError("Origin and destination cannot be identical.")

        route = attrs.get("route")
        if route:
            if route.origin_node != origin or route.destination_node != dest:
                raise serializers.ValidationError("Assigned route does not match trip origin and destination.")
        return attrs

    def create(self, validated_data):
        route = validated_data.get("route")
        # Save route snapshot
        if route:
            validated_data["route_snapshot"] = {
                "route_id": str(route.id),
                "route_type": route.route_type,
                "distance_m": route.total_distance_m,
                "time_min": route.total_time_min,
                "cost_inr": float(route.total_cost_inr or 0.0),
                "hazard_score": route.hazard_penalty_score,
                "coordinates": list(route.geometry.coords) if route.geometry else [],
                "segments": route.segments,
            }
        return super().create(validated_data)


class TripStatusUpdateSerializer(serializers.Serializer):
    """Serializer to transition trip status."""

    status = serializers.ChoiceField(choices=TripStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class TripLocationUpdateSerializer(serializers.Serializer):
    """Serializer for real-time driver GPS tracking."""

    latitude = serializers.FloatField(min_value=-90.0, max_value=90.0)
    longitude = serializers.FloatField(min_value=-180.0, max_value=180.0)


class RerouteEventSerializer(serializers.ModelSerializer):
    """Serializer for audit and UI display of dynamic reroute events."""

    old_route_summary = serializers.SerializerMethodField()
    new_route_summary = serializers.SerializerMethodField()

    class Meta:
        model = RerouteEvent
        fields = [
            "id",
            "trip",
            "old_route",
            "old_route_summary",
            "new_route",
            "new_route_summary",
            "trigger_reason",
            "triggering_edge_ids",
            "old_hazard_exposure",
            "new_hazard_exposure",
            "improvement_pct",
            "trip_route_version",
            "status",
            "driver_acknowledged_at",
            "notification_payload",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_old_route_summary(self, obj):
        if obj.old_route:
            return {
                "id": str(obj.old_route.id),
                "route_type": obj.old_route.route_type,
                "total_time_min": obj.old_route.total_time_min,
                "total_distance_km": round(obj.old_route.total_distance_m / 1000.0, 1),
                "max_hazard_score": getattr(obj.old_route, "max_hazard_score", 0.0),
                "safety_level": getattr(obj.old_route, "safety_level", "LOW"),
            }
        return None

    def get_new_route_summary(self, obj):
        if obj.new_route:
            return {
                "id": str(obj.new_route.id),
                "route_type": obj.new_route.route_type,
                "total_time_min": obj.new_route.total_time_min,
                "total_distance_km": round(obj.new_route.total_distance_m / 1000.0, 1),
                "max_hazard_score": getattr(obj.new_route, "max_hazard_score", 0.0),
                "safety_level": getattr(obj.new_route, "safety_level", "LOW"),
            }
        return None


class RerouteAcknowledgeSerializer(serializers.Serializer):
    """Serializer for driver acknowledgement of a reroute event."""

    action = serializers.ChoiceField(choices=["ACCEPT", "DECLINE"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")
