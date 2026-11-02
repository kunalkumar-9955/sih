"""
SIH26002 — Phase 10 Failure Injection & Graceful Degraded Mode Tests.
"""
from unittest.mock import patch
import pytest

from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.services.data_quality import DataQualityValidator
from apps.ingestion.services.normalization import GeospatialNormalizer


@pytest.mark.django_db
class TestPhase10FailureInjection:
    def test_missing_model_artifact_handled_safely(self):
        """When an artifact path does not exist on disk, ModelRegistry returns None without unhandled crash."""
        loaded = ModelRegistry.load_model_artifact("/non/existent/path/to/model.joblib")
        assert loaded is None

    def test_geospatial_out_of_bounds_gps_injection(self):
        """Invalid GPS coordinates far outside NER (e.g. London, Null Island) are rejected/flagged."""
        # Null Island
        assert not GeospatialNormalizer.is_within_ner_bounds(lon=0.0, lat=0.0)

        # London
        assert not GeospatialNormalizer.is_within_ner_bounds(lon=-0.1278, lat=51.5074)

        # Mumbai (India, but outside NER bounding box)
        assert not GeospatialNormalizer.is_within_ner_bounds(lon=72.8777, lat=19.0760)

        # Valid NER (Guwahati, Assam: lon 91.73, lat 26.18)
        assert GeospatialNormalizer.is_within_ner_bounds(lon=91.73, lat=26.18)

        # Valid NER (Shillong, Meghalaya: lon 91.89, lat 25.57)
        assert GeospatialNormalizer.is_within_ner_bounds(lon=91.89, lat=25.57)

    def test_data_quality_validator_catches_unphysical_inputs(self):
        """Negative rainfall and impossible slope gradients are flagged and audited safely."""
        corrupted_records = [
            {"edge_id": "EDGE-1", "rainfall_24h_mm": -15.0, "slope_deg": 12.0},
            {"edge_id": "EDGE-2", "rainfall_24h_mm": 50.0, "slope_deg": 105.0},  # slope > 90 deg impossible
        ]
        report = DataQualityValidator.audit_records(corrupted_records)
        assert not report.is_clean
        assert report.error_count >= 1
        assert len(report.errors) >= 1
