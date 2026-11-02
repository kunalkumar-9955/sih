"""
SIH26002 — Health check views.

Provides simple HTTP endpoints for Docker health checks and monitoring.
All health endpoints are unauthenticated (public).
"""
import logging

from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("sih.core")


class HealthView(APIView):
    """
    GET /api/v1/health/
    Basic liveness probe — returns 200 if the application is running.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "success": True,
                "status": "ok",
                "service": "sih26002-backend",
            },
            status=status.HTTP_200_OK,
        )


class DatabaseHealthView(APIView):
    """
    GET /api/v1/health/db/
    Database readiness probe — verifies PostGIS connection.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version();")
                postgis_version = cursor.fetchone()[0]
            return Response(
                {
                    "success": True,
                    "status": "ok",
                    "database": "connected",
                    "postgis_version": postgis_version,
                },
                status=status.HTTP_200_OK,
            )
        except OperationalError as e:
            logger.error("Database health check failed: %s", e)
            return Response(
                {
                    "success": False,
                    "status": "error",
                    "database": "disconnected",
                    "detail": str(e),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class RedisHealthView(APIView):
    """
    GET /api/v1/health/redis/
    Redis readiness probe.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            from django.core.cache import cache

            cache.set("_health_check", "ok", timeout=5)
            value = cache.get("_health_check")
            if value == "ok":
                return Response(
                    {"success": True, "status": "ok", "redis": "connected"},
                    status=status.HTTP_200_OK,
                )
            raise ValueError("Cache read/write mismatch")
        except Exception as e:
            logger.error("Redis health check failed: %s", e)
            return Response(
                {"success": False, "status": "error", "redis": "disconnected", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class DetailedHealthView(APIView):
    """
    GET /api/v1/health/detailed/
    Comprehensive multi-subsystem readiness and observability diagnostic.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        details = {
            "application": "ok",
            "database": "unknown",
            "postgis": "unknown",
            "ml_hazard_model": "unknown",
            "data_providers": "unknown",
            "sync_engine": "unknown",
        }
        is_healthy = True

        # 1. Database & PostGIS
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version();")
                postgis_ver = cursor.fetchone()[0]
                details["database"] = "connected"
                details["postgis"] = f"active ({postgis_ver})"
        except Exception as exc:
            details["database"] = f"error: {str(exc)}"
            is_healthy = False

        # 2. ML Hazard Model Registry
        try:
            from apps.hazards.ml.model_registry import ModelRegistry

            model_inst, record = ModelRegistry.get_active_model()
            details["ml_hazard_model"] = (
                f"loaded ({record.model_version if record else 'baseline-v1'})"
            )
        except Exception as exc:
            details["ml_hazard_model"] = f"warning: {str(exc)}"

        # 3. Data Ingestion Providers
        try:
            from apps.ingestion.models import DataProvider

            prov_count = DataProvider.objects.filter(is_active=True).count()
            details["data_providers"] = f"{prov_count} active providers"
        except Exception as exc:
            details["data_providers"] = f"warning: {str(exc)}"

        # 4. Sync Engine & Offline Graph Bundle
        try:
            from apps.sync.models import OfflineGraphBundle

            active_bundle = OfflineGraphBundle.objects.filter(is_active=True).first()
            bundle_tag = active_bundle.version if active_bundle else "none"
            details["sync_engine"] = f"active (bundle: {bundle_tag})"
        except Exception as exc:
            details["sync_engine"] = f"warning: {str(exc)}"

        # 5. Fleet Optimizer & Dynamic Consolidation
        try:
            from apps.fleet.services.fleet_optimizer import MultiDepotFleetOptimizer
            details["fleet_optimizer"] = "active (clarke-wright-savings-v2)"
        except Exception as exc:
            details["fleet_optimizer"] = f"warning: {str(exc)}"

        # 6. Disruption Simulation Engine
        try:
            from apps.incidents.services.simulation_engine import DisruptionSimulationEngine
            details["simulation_engine"] = "active (isolated-environment)"
        except Exception as exc:
            details["simulation_engine"] = f"warning: {str(exc)}"

        # 7. ETA Intelligence & Delay Predictor
        try:
            from apps.routing.services.eta_intelligence import PredictiveETAService
            details["eta_intelligence"] = "active (ner-mountain-eta-v2.1)"
        except Exception as exc:
            details["eta_intelligence"] = f"warning: {str(exc)}"

        response_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "success": is_healthy,
                "status": "HEALTHY" if is_healthy else "DEGRADED",
                "subsystems": details,
            },
            status=response_status,
        )


