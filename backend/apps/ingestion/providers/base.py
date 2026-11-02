"""
SIH26002 — Base Data Provider Abstraction.

Defines the contract for real-world and federated data providers:
- Strict schema validation
- Geospatial normalization (WGS84 EPSG:4326)
- Freshness evaluation
- Fault tolerance, retries, and fallback logging
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from apps.ingestion.models import FreshnessState, ProviderSourceType


@dataclass
class QualityReport:
    """Outcome of provider schema & value validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    record_count: int = 0
    clean_count: int = 0


class BaseDataProvider(ABC):
    """
    Abstract base class for all external and simulated data providers.
    """

    def __init__(
        self,
        source_code: str,
        source_name: str,
        source_type: ProviderSourceType,
        source_version: str = "v1.0",
        base_url: str = "",
        is_mock_fallback: bool = False,
    ):
        self.source_code = source_code
        self.source_name = source_name
        self.source_type = source_type
        self.source_version = source_version
        self.base_url = base_url
        self.is_mock_fallback = is_mock_fallback
        self.last_successful_sync: Optional[datetime] = None
        self.last_error: Optional[str] = None

    @abstractmethod
    def fetch_raw_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Retrieves raw data records from external API or local source."""
        pass

    @abstractmethod
    def validate_schema(self, raw_record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verifies presence and types of mandatory fields."""
        pass

    @abstractmethod
    def normalize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Maps provider schema to internal SIH26002 normalized representation."""
        pass

    def evaluate_freshness(self, observation_time: datetime) -> FreshnessState:
        """
        Classifies freshness based on observation age:
        - FRESH: < 3 hours old
        - AGING: 3 to 12 hours old
        - STALE: > 12 hours old
        """
        if timezone.is_naive(observation_time):
            observation_time = timezone.make_aware(observation_time)

        now = timezone.now()
        age = now - observation_time

        if age < timedelta(hours=3):
            return FreshnessState.FRESH
        elif age < timedelta(hours=12):
            return FreshnessState.AGING
        return FreshnessState.STALE

    def ingest_and_normalize(self, **kwargs) -> Tuple[List[Dict[str, Any]], QualityReport]:
        """
        Full pipeline: Fetch -> Validate -> Normalize -> Freshness Tagging.
        Returns: (normalized_records, quality_report)
        """
        raw_records = []
        errors = []
        warnings = []
        normalized_records = []

        try:
            raw_records = self.fetch_raw_data(**kwargs)
        except Exception as exc:
            self.last_error = str(exc)
            errors.append(f"Fetch failed: {str(exc)}")
            return [], QualityReport(is_valid=False, errors=errors, record_count=0, clean_count=0)

        for i, raw in enumerate(raw_records):
            valid, record_errors = self.validate_schema(raw)
            if not valid:
                errors.extend([f"Record #{i}: {err}" for err in record_errors])
                continue

            try:
                norm = self.normalize_record(raw)
                # Compute freshness if observation_time is present
                obs_time = norm.get("observation_time")
                if obs_time and isinstance(obs_time, datetime):
                    norm["freshness_state"] = self.evaluate_freshness(obs_time)

                norm["provider_source"] = self.source_code
                norm["is_mock_fallback"] = self.is_mock_fallback
                normalized_records.append(norm)
            except Exception as exc:
                warnings.append(f"Record #{i} normalization error: {str(exc)}")

        self.last_successful_sync = timezone.now()
        report = QualityReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            record_count=len(raw_records),
            clean_count=len(normalized_records),
        )
        return normalized_records, report
