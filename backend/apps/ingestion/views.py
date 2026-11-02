"""
SIH26002 — Ingestion & Scenario Views.

Provides REST APIs for:
1. Data provider registry & health metrics
2. Data freshness dashboard summary
3. Manual / triggered ingestion sync across external providers
4. Controlled Demo Scenario activation & reset for SIH demonstrations
"""
import logging
from typing import Any, Dict

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ingestion.models import DataProvider, IngestionLog, ProviderSourceType
from apps.ingestion.providers import (
    BhuvanTerrainProvider,
    FOISRailwayProvider,
    GatiShaktiRoadProvider,
    IMDWeatherProvider,
    IWAIWaterwayProvider,
    SentinelInSARProvider,
    StateDisasterIncidentProvider,
)
from apps.ingestion.serializers import (
    ActivateScenarioRequestSerializer,
    DataProviderSerializer,
)
from apps.ingestion.services.freshness_service import DataFreshnessService
from apps.ingestion.services.normalization import GeospatialNormalizer
from apps.ingestion.services.scenario_engine import DemoScenarioEngine

logger = logging.getLogger("sih.ingestion.views")


def _ensure_default_providers():
    """Seeds baseline data providers if empty."""
    default_defs = [
        ("IMD_WEATHER", "India Meteorological Department (NER Regional AWS)", ProviderSourceType.WEATHER, "v2.1", "https://mausam.imd.gov.in/api/"),
        ("BHUVAN_TERRAIN", "ISRO Bhuvan CartoDEM 30m Geospatial Portal", ProviderSourceType.TERRAIN, "v3.0", "https://bhuvan.nrsc.gov.in/data/api/"),
        ("SENTINEL_INSAR", "Sentinel-1 InSAR Interferometric Deformation", ProviderSourceType.TERRAIN, "v1.4", "https://sentinel.esa.int/api/insar/"),
        ("GATI_SHAKTI_ROAD", "PM Gati Shakti National Master Plan (MoRTH/PWD)", ProviderSourceType.ROAD, "v2.4", "https://gatishakti.gov.in/api/corridors/"),
        ("FOIS_RAIL", "Indian Railways Freight Operations Information System (FOIS)", ProviderSourceType.RAIL, "v4.2", "https://fois.indianrail.gov.in/api/freight/"),
        ("IWAI_WATERWAY", "Inland Waterways Authority of India (NW-2 Brahmaputra)", ProviderSourceType.WATERWAY, "v1.8", "https://iwai.nic.in/api/nw2/"),
        ("SDMA_INCIDENTS", "NER State Disaster Management Authorities (ASDMA / MSDMA)", ProviderSourceType.INCIDENT, "v1.2", "https://sdma.gov.in/api/bulletins/"),
    ]
    for code, name, ptype, ver, url in default_defs:
        DataProvider.objects.get_or_create(
            source_code=code,
            defaults={
                "name": name,
                "source_type": ptype,
                "version": ver,
                "base_url": url,
                "is_active": True,
                "is_mock_fallback": False,
                "last_successful_sync": timezone.now(),
            },
        )


class DataProviderListView(APIView):
    """
    GET /api/v1/ingestion/providers/
    Lists all registered external data providers and operational health metrics.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        _ensure_default_providers()
        providers = DataProvider.objects.all().order_by("source_type", "source_code")
        serializer = DataProviderSerializer(providers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FreshnessSummaryView(APIView):
    """
    GET /api/v1/ingestion/freshness/
    Returns real-time data freshness states across all observation sources.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        _ensure_default_providers()
        summary = DataFreshnessService.get_system_freshness_summary()
        return Response(summary, status=status.HTTP_200_OK)


class SyncAllProvidersView(APIView):
    """
    POST /api/v1/ingestion/sync-all/
    Triggers immediate ingestion cycle across all active data providers.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        _ensure_default_providers()
        providers_map = {
            "IMD_WEATHER": IMDWeatherProvider(),
            "BHUVAN_TERRAIN": BhuvanTerrainProvider(),
            "SENTINEL_INSAR": SentinelInSARProvider(),
            "GATI_SHAKTI_ROAD": GatiShaktiRoadProvider(),
            "FOIS_RAIL": FOISRailwayProvider(),
            "IWAI_WATERWAY": IWAIWaterwayProvider(),
            "SDMA_INCIDENTS": StateDisasterIncidentProvider(),
        }

        results = {}
        total_ingested = 0

        for code, provider_instance in providers_map.items():
            db_provider = DataProvider.objects.filter(source_code=code).first()
            if not db_provider or not db_provider.is_active:
                continue

            t0 = timezone.now()
            norm_records, quality_report = provider_instance.ingest_and_normalize()
            elapsed = (timezone.now() - t0).total_seconds()

            # Persist weather records specifically
            saved_count = 0
            if code == "IMD_WEATHER":
                for rec in norm_records:
                    saved_rec, _ = GeospatialNormalizer.persist_normalized_weather(rec)
                    if saved_rec:
                        saved_count += 1
            else:
                saved_count = len(norm_records)

            # Update provider metadata
            db_provider.last_successful_sync = timezone.now()
            db_provider.last_error = "" if quality_report.is_valid else "; ".join(quality_report.errors[:2])
            db_provider.save(update_fields=["last_successful_sync", "last_error"])

            # Create IngestionLog
            IngestionLog.objects.create(
                provider=db_provider,
                status=IngestionLog.IngestionStatus.SUCCESS if quality_report.is_valid else IngestionLog.IngestionStatus.PARTIAL,
                records_received=quality_report.record_count,
                records_normalized=saved_count,
                records_invalid=len(quality_report.errors),
                execution_duration_sec=round(elapsed, 3),
                error_summary="; ".join(quality_report.errors[:3]),
                metadata={"warnings": quality_report.warnings[:3]},
            )

            total_ingested += saved_count
            results[code] = {
                "status": "SUCCESS" if quality_report.is_valid else "PARTIAL",
                "records_normalized": saved_count,
                "duration_sec": round(elapsed, 3),
            }

        return Response({
            "message": f"Ingestion cycle completed. {total_ingested} records normalized.",
            "providers_executed": len(results),
            "results": results,
            "timestamp": timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)


class DemoScenarioListView(APIView):
    """
    GET /api/v1/ingestion/scenarios/
    Lists available controlled demonstration scenarios.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        scenarios = DemoScenarioEngine.list_available_scenarios()
        return Response(scenarios, status=status.HTTP_200_OK)


class DemoScenarioActivateView(APIView):
    """
    POST /api/v1/ingestion/scenarios/activate/
    Activates a specific scenario state across edges and hazard models.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ActivateScenarioRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scenario_name = serializer.validated_data["scenario_name"]
        activated_by = serializer.validated_data.get("activated_by", request.user.email)

        try:
            result = DemoScenarioEngine.activate_scenario(scenario_name, activated_by=activated_by)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class DemoScenarioResetView(APIView):
    """
    POST /api/v1/ingestion/scenarios/reset/
    Restores the canonical baseline graph conditions.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        result = DemoScenarioEngine.reset_to_baseline()
        return Response(result, status=status.HTTP_200_OK)
