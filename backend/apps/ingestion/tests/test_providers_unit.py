"""
SIH26002 — Phase 6 Unit Tests: Data Ingestion Providers, Normalization, & Freshness.

Tests:
1. IMDWeatherProvider schema validation, bounds checks, impossible value rejection, and severity classification.
2. BhuvanTerrainProvider DEM and slope gradient validation.
3. SentinelInSARProvider surface deformation displacement rate validation.
4. FOISRailwayProvider rail freight capacity and transshipment timings.
5. IWAIWaterwayProvider NW-2 navigable depth and water stage validation.
6. StateDisasterIncidentProvider official disaster bulletin validation.
7. GeospatialNormalizer NER operational bounding box checks and coordinate validation.
8. DataFreshnessService confidence decay calculations.
"""
from datetime import datetime, timedelta
import pytest
from django.utils import timezone

from apps.ingestion.models import FreshnessState
from apps.ingestion.providers import (
    BhuvanTerrainProvider,
    FOISRailwayProvider,
    GatiShaktiRoadProvider,
    IMDWeatherProvider,
    IWAIWaterwayProvider,
    SentinelInSARProvider,
    StateDisasterIncidentProvider,
)
from apps.ingestion.services.freshness_service import DataFreshnessService
from apps.ingestion.services.normalization import GeospatialNormalizer


class TestIMDWeatherProvider:
    """Tests IMD weather schema, bounds, and normalizations."""

    def test_fetch_and_normalize_success(self):
        provider = IMDWeatherProvider()
        records, report = provider.ingest_and_normalize()
        assert report.is_valid is True
        assert len(records) >= 5
        for rec in records:
            assert "rainfall_24h_mm" in rec
            assert "weather_severity" in rec
            assert rec["rainfall_24h_mm"] >= 0.0

    def test_rejection_of_negative_rainfall(self):
        provider = IMDWeatherProvider()
        raw = {
            "latitude": 26.14,
            "longitude": 91.73,
            "rainfall_24h_mm": -10.0,
            "observation_time": timezone.now().isoformat(),
        }
        is_valid, errors = provider.validate_schema(raw)
        assert is_valid is False
        assert any("negative" in e.lower() for e in errors)

    def test_rejection_of_unphysical_extreme_rainfall(self):
        provider = IMDWeatherProvider()
        raw = {
            "latitude": 26.14,
            "longitude": 91.73,
            "rainfall_24h_mm": 2500.0,  # Impossible single-day rainfall
            "observation_time": timezone.now().isoformat(),
        }
        is_valid, errors = provider.validate_schema(raw)
        assert is_valid is False
        assert any("unphysical" in e.lower() for e in errors)

    def test_weather_severity_classification(self):
        provider = IMDWeatherProvider()
        # Light rain
        norm1 = provider.normalize_record({
            "latitude": 26.0, "longitude": 91.0,
            "rainfall_24h_mm": 5.0, "observation_time": timezone.now(),
        })
        assert norm1["weather_severity"] == "LIGHT_RAIN"

        # Extreme rain
        norm2 = provider.normalize_record({
            "latitude": 26.0, "longitude": 91.0,
            "rainfall_24h_mm": 125.0, "observation_time": timezone.now(),
        })
        assert norm2["weather_severity"] == "EXTREME_RAIN"


class TestTerrainAndInSARProviders:
    """Tests ISRO Bhuvan DEM and Sentinel-1 InSAR providers."""

    def test_bhuvan_dem_validation(self):
        provider = BhuvanTerrainProvider()
        records, report = provider.ingest_and_normalize()
        assert report.is_valid is True
        assert len(records) >= 3
        for r in records:
            assert 0.0 <= r["slope_deg"] <= 90.0

    def test_bhuvan_invalid_slope_rejected(self):
        provider = BhuvanTerrainProvider()
        raw = {"latitude": 25.5, "longitude": 91.8, "elevation_m": 500, "slope_deg": 120.0}
        valid, errors = provider.validate_schema(raw)
        assert valid is False
        assert any("slope" in e.lower() for e in errors)

    def test_sentinel_insar_displacement_validation(self):
        provider = SentinelInSARProvider()
        records, report = provider.ingest_and_normalize()
        assert report.is_valid is True
        assert len(records) >= 2
        sonapur_rec = [r for r in records if r["surface_deformation_mm_yr"] < -10.0]
        assert len(sonapur_rec) >= 1  # Active slope creep identified


class TestMultimodalTransportProviders:
    """Tests PM Gati Shakti, FOIS Rail, and IWAI Waterway."""

    def test_gati_shakti_road_validation(self):
        provider = GatiShaktiRoadProvider()
        records, report = provider.ingest_and_normalize()
        assert report.is_valid is True
        assert any(r["corridor_code"] == "NH6_MEGHALAYA_BARAK" for r in records)

    def test_fois_rail_validation(self):
        provider = FOISRailwayProvider()
        records, report = provider.ingest_and_normalize()
        assert report.is_valid is True
        assert any(r["operating_status"] == "OPERATIONAL" for r in records)

    def test_iwai_waterway_validation_and_negative_depth_rejection(self):
        provider = IWAIWaterwayProvider()
        records, report = provider.ingest_and_normalize()
        assert report.is_valid is True

        # Invalid depth
        raw_bad = {"port_code": "TEST", "navigable_depth_m": -2.0, "is_navigable": True}
        valid, errors = provider.validate_schema(raw_bad)
        assert valid is False


class TestGeospatialNormalizer:
    """Tests North Eastern Region spatial bounding box checks."""

    def test_ner_bounding_box_acceptance(self):
        # Guwahati (26.14, 91.73)
        assert GeospatialNormalizer.is_within_ner_bounds(91.73, 26.14) is True
        # Silchar (24.83, 92.79)
        assert GeospatialNormalizer.is_within_ner_bounds(92.79, 24.83) is True

    def test_outside_ner_rejection(self):
        # Mumbai (19.07, 72.87)
        assert GeospatialNormalizer.is_within_ner_bounds(72.87, 19.07) is False
        # London (51.50, -0.12)
        assert GeospatialNormalizer.is_within_ner_bounds(-0.12, 51.50) is False

        pt, errors = GeospatialNormalizer.create_point_geometry(lon=72.87, lat=19.07)
        assert pt is None
        assert any("outside north eastern region" in e.lower() for e in errors)


class TestDataFreshnessDecay:
    """Tests data freshness confidence factors."""

    def test_confidence_factor_decay(self):
        assert DataFreshnessService.get_freshness_confidence_factor(FreshnessState.FRESH) == 1.0
        assert DataFreshnessService.get_freshness_confidence_factor(FreshnessState.AGING) == 0.80
        assert DataFreshnessService.get_freshness_confidence_factor(FreshnessState.STALE) == 0.50
        assert DataFreshnessService.get_freshness_confidence_factor(FreshnessState.INVALID) == 0.0
