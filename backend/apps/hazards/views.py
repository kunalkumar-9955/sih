"""
SIH26002 — Hazard Intelligence Views & API Endpoints.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.models import (
    HazardIncident,
    HazardModelRecord,
    HazardScore,
    HazardSeverity,
    TerrainFeature,
    WeatherObservation,
)
from apps.hazards.serializers import (
    EdgeHazardDetailSerializer,
    HazardIncidentListSerializer,
    HazardIncidentReportSerializer,
    HazardModelRecordSerializer,
    HazardScoreSerializer,
)
from apps.hazards.services.data_quality import DataQualityValidator
from apps.transport_graph.models import TransportEdge


class HazardSummaryView(APIView):
    """
    GET /api/v1/hazards/summary/
    High-level platform hazard overview for dashboards and control towers.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        edges = TransportEdge.objects.filter(is_available=True)
        total_edges = edges.count()

        active_scores = HazardScore.objects.filter(is_current=True)
        severity_counts = {
            HazardSeverity.LOW: 0,
            HazardSeverity.MODERATE: 0,
            HazardSeverity.HIGH: 0,
            HazardSeverity.CRITICAL: 0,
        }

        stale_count = 0
        for s in active_scores:
            if s.severity in severity_counts:
                severity_counts[s.severity] += 1
            if s.is_stale:
                stale_count += 1

        # If no HazardScore objects yet, categorize from TransportEdge.hazard_score
        if active_scores.count() == 0:
            for e in edges:
                sev = HazardSeverity.classify(e.hazard_score or 0.1)
                severity_counts[sev] += 1

        active_model, _ = ModelRegistry.get_active_model()
        recent_incidents = HazardIncident.objects.filter(
            status__in=[HazardIncident.IncidentStatus.REPORTED, HazardIncident.IncidentStatus.VERIFIED]
        ).count()

        return Response({
            "total_monitored_segments": total_edges,
            "severity_breakdown": severity_counts,
            "critical_segments_count": severity_counts[HazardSeverity.CRITICAL],
            "high_risk_segments_count": severity_counts[HazardSeverity.HIGH],
            "stale_predictions_count": stale_count,
            "active_incidents_count": recent_incidents,
            "active_model": {
                "model_version": active_model.model_version if active_model else "baseline-heuristic",
                "algorithm": active_model.algorithm if active_model else "HEURISTIC",
                "trained_at": active_model.trained_at if active_model else None,
            },
            "thresholds": HazardSeverity.get_thresholds(),
        })


class HazardSegmentListView(APIView):
    """
    GET /api/v1/hazards/segments/
    Lists transport edges with their operational hazard scores and severity.
    Query param ?severity=CRITICAL,HIGH
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = TransportEdge.objects.select_related("source_node", "target_node").prefetch_related(
            "hazard_scores", "weather_observations", "incidents"
        ).filter(is_available=True)

        severity_filter = request.query_params.get("severity")
        if severity_filter:
            target_severities = [s.strip().upper() for s in severity_filter.split(",")]
            # Filter edges that have current hazard score matching severity
            qs = qs.filter(hazard_scores__is_current=True, hazard_scores__severity__in=target_severities)

        serializer = EdgeHazardDetailSerializer(qs, many=True)
        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        })


class HazardSegmentDetailView(APIView):
    """
    GET /api/v1/hazards/segments/{edge_id}/
    Returns granular risk intelligence, weather, terrain, and contributing factors for an edge.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, edge_id):
        try:
            edge = TransportEdge.objects.select_related("source_node", "target_node").get(id=edge_id)
        except TransportEdge.DoesNotExist:
            return Response({"detail": "Transport edge not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EdgeHazardDetailSerializer(edge)
        return Response(serializer.data)


class HazardIncidentReportView(APIView):
    """
    POST /api/v1/hazards/report/
    Crowd-sourced driver and official hazard incident reporting.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = HazardIncidentReportSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            incident = serializer.save()
            return Response(
                {
                    "message": "Hazard report submitted successfully. Operations team notified for verification.",
                    "report": HazardIncidentReportSerializer(incident).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HazardIncidentListView(APIView):
    """
    GET /api/v1/hazards/incidents/
    List active verified and reported disruptions.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        incidents = HazardIncident.objects.select_related("edge", "edge__source_node", "edge__target_node").order_by("-occurred_at")[:50]
        serializer = HazardIncidentListSerializer(incidents, many=True)
        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        })


class HazardModelRecordListView(APIView):
    """
    GET /api/v1/hazards/models/
    Admin / developer model registry inspection.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        models_qs = HazardModelRecord.objects.all().order_by("-trained_at")
        serializer = HazardModelRecordSerializer(models_qs, many=True)
        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        })


class DataQualityAuditView(APIView):
    """
    GET /api/v1/hazards/data-quality/
    Runs dynamic data quality check across meteorological and terrain records.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        weather_samples = list(
            WeatherObservation.objects.values(
                "rainfall_24h_mm", "rainfall_1h_mm", "temperature_c", "humidity_pct", "observation_time"
            )[:500]
        )
        terrain_samples = list(
            TerrainFeature.objects.values(
                "slope_deg", "elevation_m", "soil_saturation", "fault_line_distance_km"
            )[:500]
        )

        report = DataQualityValidator.audit_records(
            weather_records=weather_samples,
            terrain_records=terrain_samples,
        )
        return Response(report.to_dict())
