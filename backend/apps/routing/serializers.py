from django.db import models
from rest_framework import serializers

from apps.transport_graph.models import TransportMode, TransportNode
from apps.transport_graph.spatial import find_nearest_node
from .models import Route, RouteType


class RouteSegmentSerializer(serializers.Serializer):
    """Detailed segment serializer."""
    sequence = serializers.IntegerField(required=False, default=1)
    edge_id = serializers.CharField()
    source_node = serializers.CharField()
    source_node_id = serializers.CharField(required=False)
    target_node = serializers.CharField()
    target_node_id = serializers.CharField(required=False)
    mode = serializers.CharField()
    distance_m = serializers.FloatField()
    transit_time_min = serializers.FloatField()
    cost_inr = serializers.FloatField()
    hazard_score = serializers.FloatField()
    status = serializers.CharField()
    transfer_time_min = serializers.FloatField(allow_null=True, required=False)
    transfer_cost_inr = serializers.FloatField(allow_null=True, required=False)
    road_name = serializers.CharField(allow_blank=True, required=False)


class RouteSerializer(serializers.ModelSerializer):
    """
    Full Route Serializer exposing both standard and Section 8 specification keys.
    """

    route_id = serializers.UUIDField(source="id", read_only=True)
    routing_policy = serializers.CharField(source="route_type", read_only=True)
    route_type_display = serializers.CharField(source="get_route_type_display", read_only=True)

    origin = serializers.CharField(source="origin_node.name", read_only=True)
    origin_node_name = serializers.CharField(source="origin_node.name", read_only=True)
    destination = serializers.CharField(source="destination_node.name", read_only=True)
    destination_node_name = serializers.CharField(source="destination_node.name", read_only=True)

    total_distance = serializers.FloatField(source="total_distance_m", read_only=True)
    total_time = serializers.FloatField(source="total_time_min", read_only=True)
    total_cost = serializers.DecimalField(source="total_cost_inr", max_digits=12, decimal_places=2, read_only=True)
    risk_score = serializers.FloatField(source="hazard_penalty_score", read_only=True)

    geometry_coordinates = serializers.SerializerMethodField()
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            "id",
            "route_id",
            "route_type",
            "routing_policy",
            "route_type_display",
            "origin_node",
            "origin",
            "origin_node_name",
            "destination_node",
            "destination",
            "destination_node_name",
            "total_distance_m",
            "total_distance",
            "total_time_min",
            "total_time",
            "total_cost_inr",
            "total_cost",
            "hazard_penalty_score",
            "risk_score",
            "modes_used",
            "transfer_count",
            "explanation",
            "geometry",
            "geometry_coordinates",
            "segments",
            "alpha_used",
            "is_current",
            "computed_at",
        ]
        read_only_fields = fields

    def get_geometry_coordinates(self, obj):
        if obj.geometry:
            return list(obj.geometry.coords)
        return []

    def get_geometry(self, obj):
        if obj.geometry:
            return {
                "type": "LineString",
                "coordinates": list(obj.geometry.coords),
            }
        return None


class RoutePlanRequestSerializer(serializers.Serializer):
    """
    Serializer validating POST /api/v1/routes/plan/ and POST /api/v1/routes/compute/ requests.
    Supports node UUIDs, names, or spatial [lon, lat] coordinates.
    """

    # Identifiers (flexible input: origin or origin_node_id)
    origin = serializers.CharField(required=False, allow_blank=True)
    origin_node_id = serializers.UUIDField(required=False, allow_null=True)
    destination = serializers.CharField(required=False, allow_blank=True)
    destination_node_id = serializers.UUIDField(required=False, allow_null=True)

    # Coordinate fallback (optional)
    origin_coords = serializers.ListField(child=serializers.FloatField(), required=False, max_length=2, min_length=2)
    destination_coords = serializers.ListField(child=serializers.FloatField(), required=False, max_length=2, min_length=2)

    # Policy
    routing_policy = serializers.CharField(required=False, default="ALL")
    route_types = serializers.ListField(
        child=serializers.ChoiceField(choices=RouteType.choices),
        required=False,
        default=lambda: [RouteType.SAFEST, RouteType.FASTEST, RouteType.CHEAPEST, RouteType.MULTIMODAL],
    )

    # Vehicle & Cargo constraints
    vehicle_id = serializers.UUIDField(required=False, allow_null=True)
    vehicle_type = serializers.CharField(required=False, allow_blank=True)
    cargo_weight = serializers.FloatField(required=False, min_value=0.0, allow_null=True)
    departure_time = serializers.DateTimeField(required=False, allow_null=True)

    # Mode controls
    allow_multimodal = serializers.BooleanField(required=False, default=True)
    avoid_modes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    preferred_modes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    max_transfers = serializers.IntegerField(required=False, min_value=0, allow_null=True)

    # Engine tuning
    alpha = serializers.FloatField(required=False, min_value=0.0, max_value=10.0, allow_null=True)
    persist = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        # 1. Resolve Origin
        origin_node = None
        orig_id = attrs.get("origin_node_id") or attrs.get("origin")
        if orig_id:
            try:
                origin_node = TransportNode.objects.get(id=orig_id, is_active=True)
            except (TransportNode.DoesNotExist, ValueError):
                # Try search by name or short_code
                origin_node = TransportNode.objects.filter(is_active=True).filter(
                    models.Q(short_code=orig_id) | models.Q(name__iexact=str(orig_id))
                ).first()

        if not origin_node and attrs.get("origin_coords"):
            coords = attrs["origin_coords"]
            origin_node = find_nearest_node(longitude=coords[0], latitude=coords[1])

        if not origin_node:
            raise serializers.ValidationError({"origin": "Could not resolve an active origin transport node."})

        # 2. Resolve Destination
        dest_node = None
        dst_id = attrs.get("destination_node_id") or attrs.get("destination")
        if dst_id:
            try:
                dest_node = TransportNode.objects.get(id=dst_id, is_active=True)
            except (TransportNode.DoesNotExist, ValueError):
                dest_node = TransportNode.objects.filter(is_active=True).filter(
                    models.Q(short_code=dst_id) | models.Q(name__iexact=str(dst_id))
                ).first()

        if not dest_node and attrs.get("destination_coords"):
            coords = attrs["destination_coords"]
            dest_node = find_nearest_node(longitude=coords[0], latitude=coords[1])

        if not dest_node:
            raise serializers.ValidationError({"destination": "Could not resolve an active destination transport node."})

        if origin_node.id == dest_node.id:
            raise serializers.ValidationError("Origin and destination nodes cannot be identical.")

        attrs["resolved_origin"] = origin_node
        attrs["resolved_destination"] = dest_node

        # Normalize policy
        policy = attrs.get("routing_policy", "ALL").upper().strip()
        if policy in RouteType.values:
            attrs["requested_types"] = [policy]
        else:
            attrs["requested_types"] = attrs.get("route_types", [
                RouteType.SAFEST, RouteType.FASTEST, RouteType.CHEAPEST, RouteType.MULTIMODAL
            ])

        return attrs
