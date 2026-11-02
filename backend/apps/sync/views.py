"""
SIH26002 — Sync Views.

Provides REST endpoints for:
1. Checking offline graph version and SHA-256 checksum (lightweight)
2. Downloading full offline graph bundle
3. Submitting batches of offline-queued sync events with idempotency & conflict detection
4. Querying sync diagnostics and health status
5. Triggering and tracking emergency SOS distress beacons
"""
import logging

from django.contrib.gis.geos import Point
from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import Driver
from apps.sync.models import (
    EmergencySOS,
    EmergencySOSStatus,
    OfflineGraphBundle,
    SyncEventStatus,
    SyncQueueRecord,
)
from apps.sync.serializers import (
    EmergencySOSSerializer,
    OfflineGraphDownloadSerializer,
    OfflineGraphVersionSerializer,
    SyncBatchRequestSerializer,
    SyncBatchResponseSerializer,
)
from apps.sync.services.offline_graph_exporter import OfflineGraphExporterService
from apps.sync.services.sync_processor import BatchSyncProcessor

logger = logging.getLogger(__name__)


def _get_driver_for_user(user) -> Driver | None:
    """Helper to safely extract driver from request.user."""
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "driver_profile", None)


class OfflineGraphVersionView(APIView):
    """
    GET /api/v1/sync/graph/version/
    Returns the latest version tag and SHA-256 checksum for the specified region.
    Clients use this to determine if a full bundle download is needed.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        region = request.query_params.get("region", "NER_CORRIDOR")
        bundle = (
            OfflineGraphBundle.objects.filter(corridor_name=region, is_active=True)
            .order_by("-created_at")
            .first()
        )

        if not bundle:
            # Auto-export if none exists yet
            exporter = OfflineGraphExporterService(region=region)
            bundle = exporter.export_and_save()

        serializer = OfflineGraphVersionSerializer(bundle)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OfflineGraphDownloadView(APIView):
    """
    GET /api/v1/sync/graph/download/
    Downloads the full offline graph bundle for local SQLite / in-memory edge caching.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        region = request.query_params.get("region", "NER_CORRIDOR")
        bundle = (
            OfflineGraphBundle.objects.filter(corridor_name=region, is_active=True)
            .order_by("-created_at")
            .first()
        )

        if not bundle:
            exporter = OfflineGraphExporterService(region=region)
            bundle = exporter.export_and_save()

        serializer = OfflineGraphDownloadSerializer(bundle)
        resp = Response(serializer.data, status=status.HTTP_200_OK)
        resp["ETag"] = f'"{bundle.checksum_sha256}"'
        resp["X-Graph-Version"] = bundle.version_tag
        resp["X-Graph-Checksum-SHA256"] = bundle.checksum_sha256
        return resp


class SyncBatchEventView(APIView):
    """
    POST /api/v1/sync/events/batch/
    Processes an array of offline queued events with idempotency and conflict resolution.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SyncBatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        events = serializer.validated_data["events"]
        driver = _get_driver_for_user(request.user)

        processor = BatchSyncProcessor(driver=driver)
        batch_summary = processor.process_batch(events)

        response_serializer = SyncBatchResponseSerializer(batch_summary)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class SyncStatusView(APIView):
    """
    GET /api/v1/sync/status/
    Provides diagnostic statistics on synchronized events, conflicts, and SOS beacons.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Breakdown by status
        status_counts = dict(
            SyncQueueRecord.objects.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        # Active SOS count
        active_sos = EmergencySOS.objects.filter(
            status__in=[EmergencySOSStatus.TRIGGERED, EmergencySOSStatus.ACKNOWLEDGED]
        ).count()

        # Latest graph bundle
        latest_bundle = OfflineGraphBundle.objects.filter(is_active=True).first()

        diagnostics = {
            "total_records": sum(status_counts.values()),
            "applied_count": status_counts.get(SyncEventStatus.APPLIED, 0),
            "conflict_count": status_counts.get(SyncEventStatus.CONFLICT, 0),
            "duplicate_count": status_counts.get(SyncEventStatus.DUPLICATE, 0),
            "rejected_count": status_counts.get(SyncEventStatus.REJECTED, 0),
            "active_sos_count": active_sos,
            "active_graph_bundle": (
                {
                    "version_tag": latest_bundle.version_tag,
                    "region": latest_bundle.region,
                    "node_count": latest_bundle.node_count,
                    "edge_count": latest_bundle.edge_count,
                    "checksum_sha256": latest_bundle.checksum_sha256[:12] + "...",
                }
                if latest_bundle
                else None
            ),
            "server_time": timezone.now().isoformat(),
        }

        return Response(diagnostics, status=status.HTTP_200_OK)


class EmergencySOSView(APIView):
    """
    GET, POST /api/v1/sync/sos/
    POST: Driver triggers an immediate SOS distress signal.
    GET: List active emergency SOS signals.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        signals = EmergencySOS.objects.select_related("driver", "trip").order_by("-triggered_at")[:50]
        serializer = EmergencySOSSerializer(signals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        driver = _get_driver_for_user(request.user)
        if not driver:
            # Check if user is staff/admin or if driver_id was passed
            driver_id = request.data.get("driver_id")
            if driver_id:
                driver = Driver.objects.filter(id=driver_id).first()

        if not driver:
            return Response(
                {"error": "Authenticated driver profile is required to trigger SOS."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EmergencySOSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lat = serializer.validated_data.get("latitude")
        lon = serializer.validated_data.get("longitude")
        pt = None
        if lat is not None and lon is not None:
            pt = Point(float(lon), float(lat), srid=4326)

        sos = EmergencySOS.objects.create(
            driver=driver,
            trip=serializer.validated_data.get("trip"),
            location=pt,
            status=EmergencySOSStatus.TRIGGERED,
            message=serializer.validated_data.get(
                "message", "Emergency SOS beacon triggered by driver."
            ),
            triggered_at=timezone.now(),
            metadata=serializer.validated_data.get("metadata", {}),
        )

        return Response(EmergencySOSSerializer(sos).data, status=status.HTTP_201_CREATED)
