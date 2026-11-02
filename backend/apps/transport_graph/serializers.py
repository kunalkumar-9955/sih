"""
SIH26002 — Transport graph serializers.
"""
from rest_framework import serializers

from .models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode


class TransportNodeSerializer(serializers.ModelSerializer):
    """Serializer for transport graph nodes."""

    node_type_display = serializers.CharField(source="get_node_type_display", read_only=True)
    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = TransportNode
        fields = [
            "id",
            "name",
            "short_code",
            "node_type",
            "node_type_display",
            "coordinates",
            "elevation_m",
            "state",
            "district",
            "is_active",
            "data_source",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_coordinates(self, obj):
        if obj.geometry:
            return {
                "longitude": obj.geometry.x,
                "latitude": obj.geometry.y,
            }
        return None


class TransportEdgeSerializer(serializers.ModelSerializer):
    """Serializer for transport graph edges."""

    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_node_name = serializers.CharField(source="source_node.name", read_only=True)
    target_node_name = serializers.CharField(source="target_node.name", read_only=True)
    is_traversable = serializers.BooleanField(read_only=True)
    geometry_coordinates = serializers.SerializerMethodField()

    class Meta:
        model = TransportEdge
        fields = [
            "id",
            "source_node",
            "source_node_name",
            "target_node",
            "target_node_name",
            "mode",
            "mode_display",
            "status",
            "status_display",
            "distance_m",
            "base_transit_time_min",
            "cost_inr",
            "capacity_kg",
            "hazard_score",
            "is_available",
            "is_traversable",
            "transfer_time_min",
            "transfer_cost_inr",
            "road_name",
            "geometry_coordinates",
            "data_source",
            "last_updated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_traversable", "created_at", "updated_at", "last_updated"]

    def get_geometry_coordinates(self, obj):
        if obj.geometry:
            return list(obj.geometry.coords)
        return []


class TransportGraphDumpSerializer(serializers.Serializer):
    """
    Compact serialization of the full transport graph for offline synchronization
    and local client routing (Mobile / Web).
    """

    nodes = TransportNodeSerializer(many=True)
    edges = TransportEdgeSerializer(many=True)
    timestamp = serializers.DateTimeField()
