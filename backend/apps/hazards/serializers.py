"""
SIH26002 — Hazard Intelligence Serializers.
"""
from rest_framework import serializers

from apps.hazards.models import (
    HazardIncident,
    HazardModelRecord,
    HazardScore,
    HazardSeverity,
    TerrainFeature,
    WeatherObservation,
)
from apps.transport_graph.models import TransportEdge


class HazardScoreSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = HazardScore
        fields = [
            "id",
            "edge",
            "hazard_index",
            "confidence",
            "severity",
            "severity_display",
            "model_version",
            "feature_version",
            "predicted_at",
            "valid_until",
            "is_stale",
            "source",
            "contributing_factors",
            "features_snapshot",
            "is_current",
        ]


class WeatherObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherObservation
        fields = [
            "id",
            "edge",
            "rainfall_mm",
            "rainfall_1h_mm",
            "rainfall_6h_mm",
            "rainfall_24h_mm",
            "temperature_c",
            "humidity_pct",
            "precipitation_probability",
            "observation_time",
            "source",
            "is_forecast",
        ]


class TerrainFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerrainFeature
        fields = [
            "id",
            "edge",
            "slope_deg",
            "elevation_m",
            "elevation_change_m",
            "soil_type",
            "soil_saturation",
            "drainage_density",
            "fault_line_distance_km",
            "source",
        ]


class HazardIncidentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HazardIncident
        fields = [
            "id",
            "edge",
            "incident_type",
            "severity",
            "description",
            "occurred_at",
            "source",
            "status",
        ]
        read_only_fields = ["id", "status", "source", "occurred_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["reporter"] = user
        validated_data["source"] = HazardIncident.IncidentSource.DRIVER
        # Driver reports start in REPORTED status until verified
        validated_data["status"] = HazardIncident.IncidentStatus.REPORTED
        return super().create(validated_data)


class HazardIncidentListSerializer(serializers.ModelSerializer):
    edge_name = serializers.SerializerMethodField()

    class Meta:
        model = HazardIncident
        fields = [
            "id",
            "edge",
            "edge_name",
            "incident_type",
            "severity",
            "description",
            "occurred_at",
            "rainfall_context_mm",
            "source",
            "status",
        ]

    def get_edge_name(self, obj) -> str:
        if obj.edge:
            return f"{obj.edge.source_node.name} → {obj.edge.target_node.name}"
        return "Unspecified corridor sector"


class HazardModelRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = HazardModelRecord
        fields = [
            "id",
            "model_id",
            "model_version",
            "algorithm",
            "feature_version",
            "dataset_type",
            "training_samples",
            "metrics",
            "feature_importances",
            "is_active",
            "trained_at",
        ]


class EdgeHazardDetailSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source_node.name", read_only=True)
    target_name = serializers.CharField(source="target_node.name", read_only=True)
    current_hazard = serializers.SerializerMethodField()
    terrain = serializers.SerializerMethodField()
    latest_weather = serializers.SerializerMethodField()
    recent_incidents_count = serializers.SerializerMethodField()

    class Meta:
        model = TransportEdge
        fields = [
            "id",
            "source_name",
            "target_name",
            "mode",
            "road_name",
            "status",
            "distance_m",
            "current_hazard",
            "terrain",
            "latest_weather",
            "recent_incidents_count",
        ]

    def get_current_hazard(self, obj):
        score = obj.hazard_scores.filter(is_current=True).order_by("-predicted_at").first()
        if score:
            return HazardScoreSerializer(score).data
        # Fallback to edge static score
        return {
            "hazard_index": float(obj.hazard_score or 0.1),
            "severity": HazardSeverity.classify(obj.hazard_score or 0.1),
            "confidence": 0.50,
            "model_version": "static-fallback",
            "is_stale": False,
            "contributing_factors": {},
        }

    def get_terrain(self, obj):
        tf = getattr(obj, "terrain_feature", None)
        if tf:
            return TerrainFeatureSerializer(tf).data
        return None

    def get_latest_weather(self, obj):
        w = obj.weather_observations.order_by("-observation_time").first()
        if w:
            return WeatherObservationSerializer(w).data
        return None

    def get_recent_incidents_count(self, obj) -> int:
        return obj.incidents.count()
