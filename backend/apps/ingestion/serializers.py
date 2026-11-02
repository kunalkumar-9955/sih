"""
SIH26002 — Ingestion & Scenario Serializers.
"""
from rest_framework import serializers

from apps.ingestion.models import (
    DataProvider,
    DemoScenarioRecord,
    IngestionLog,
    NormalizedWeatherRecord,
)


class DataProviderSerializer(serializers.ModelSerializer):
    """Data provider registry serializer."""

    class Meta:
        model = DataProvider
        fields = [
            "id",
            "source_code",
            "name",
            "source_type",
            "version",
            "base_url",
            "is_active",
            "is_mock_fallback",
            "last_successful_sync",
            "last_error",
            "sync_interval_min",
            "provenance_metadata",
            "created_at",
        ]


class DemoScenarioSerializer(serializers.ModelSerializer):
    """Demo scenario registry and activation serializer."""

    class Meta:
        model = DemoScenarioRecord
        fields = [
            "id",
            "name",
            "is_active",
            "activated_at",
            "activated_by",
            "affected_edges_count",
            "affected_edge_ids",
            "description",
            "parameters",
        ]


class ActivateScenarioRequestSerializer(serializers.Serializer):
    """Request payload for activating a demo scenario."""

    scenario_name = serializers.CharField(max_length=64)
    activated_by = serializers.CharField(max_length=128, required=False, default="DEMO_OPERATOR")


class NormalizedWeatherRecordSerializer(serializers.ModelSerializer):
    """Weather observation serializer."""

    class Meta:
        model = NormalizedWeatherRecord
        fields = [
            "id",
            "edge",
            "rainfall_1h_mm",
            "rainfall_6h_mm",
            "rainfall_24h_mm",
            "precipitation_probability",
            "temperature_c",
            "humidity_pct",
            "wind_speed_mps",
            "weather_severity",
            "observation_time",
            "freshness_state",
            "provider_source",
            "created_at",
        ]
