"""
SIH26002 — Data Freshness & Quality Monitoring Service.

Provides real-time inspection of data pipelines:
- Observation age tracking & decay
- Provider reliability scoring
- Stale data alerts for control tower and dashboards
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.db.models import Count
from django.utils import timezone

from apps.ingestion.models import (
    DataProvider,
    FreshnessState,
    NormalizedTerrainRecord,
    NormalizedWeatherRecord,
)


class DataFreshnessService:
    """
    Evaluates freshness status across all providers and stored observations.
    """

    # Maximum allowed latency thresholds
    FRESH_THRESHOLD_HOURS = 3.0
    AGING_THRESHOLD_HOURS = 12.0

    @classmethod
    def get_freshness_confidence_factor(cls, freshness_state: str) -> float:
        """
        Returns confidence weighting multiplier based on data freshness:
        - FRESH: 1.0 (full fidelity)
        - AGING: 0.80 (modest decay)
        - STALE: 0.50 (heavy decay, triggers fallback flag)
        - INVALID/UNAVAILABLE: 0.0
        """
        if freshness_state == FreshnessState.FRESH:
            return 1.0
        elif freshness_state == FreshnessState.AGING:
            return 0.80
        elif freshness_state == FreshnessState.STALE:
            return 0.50
        return 0.0

    @classmethod
    def get_system_freshness_summary(cls) -> Dict[str, Any]:
        """
        Aggregates health and freshness across all ingestion pipelines for the dashboard.
        """
        providers = DataProvider.objects.all()
        provider_summaries = []

        total_fresh = 0
        total_aging = 0
        total_stale = 0

        now = timezone.now()

        for prov in providers:
            last_sync = prov.last_successful_sync
            if not last_sync:
                p_state = FreshnessState.UNAVAILABLE
            else:
                age = now - last_sync
                if age < timedelta(hours=cls.FRESH_THRESHOLD_HOURS):
                    p_state = FreshnessState.FRESH
                    total_fresh += 1
                elif age < timedelta(hours=cls.AGING_THRESHOLD_HOURS):
                    p_state = FreshnessState.AGING
                    total_aging += 1
                else:
                    p_state = FreshnessState.STALE
                    total_stale += 1

            provider_summaries.append({
                "source_code": prov.source_code,
                "name": prov.name,
                "source_type": prov.source_type,
                "is_active": prov.is_active,
                "is_mock_fallback": prov.is_mock_fallback,
                "last_successful_sync": last_sync.isoformat() if last_sync else None,
                "freshness_state": p_state,
                "last_error": prov.last_error or None,
            })

        # Weather observations breakdown
        weather_counts = dict(
            NormalizedWeatherRecord.objects.values("freshness_state")
            .annotate(count=Count("id"))
            .values_list("freshness_state", "count")
        )

        return {
            "evaluated_at": now.isoformat(),
            "total_providers": len(providers),
            "fresh_providers_count": total_fresh,
            "aging_providers_count": total_aging,
            "stale_providers_count": total_stale,
            "weather_records_by_state": weather_counts,
            "providers": provider_summaries,
        }
