"""
SIH26002 — Command Center Operational Intelligence & Explainable AI Views.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import DecisionRecommendation, NetworkHealthSnapshot
from apps.fleet.models import CargoStatus, FreightLoad, OptimizationRun
from apps.hazards.models import HazardScore
from apps.incidents.models import DisruptionSimulationRun
from apps.routing.models import ETAPredictionRecord, Route
from apps.routing.services.eta_intelligence import PredictiveETAService
from apps.transport_graph.models import EdgeStatus, TransportEdge, TransportNode
from apps.transport_graph.services.accessibility import AccessibilityIntelligenceService
from apps.trips.models import Trip, TripStatus
from apps.vehicles.models import Vehicle, VehicleStatus


class NetworkOperationalSummaryView(APIView):
    """
    GET /api/v1/intelligence/network/
    Command-center operational summary with overall network health, severity state,
    active trips, hazards, and infrastructure availability.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        state_filter = request.query_params.get("state")
        corridor_filter = request.query_params.get("corridor")

        # 1. Operational Counts
        active_trips_count = Trip.objects.filter(status__in=[TripStatus.PLANNED, TripStatus.ACTIVE]).count()
        total_vehicles = Vehicle.objects.filter(is_active=True).count()
        busy_vehicles = Vehicle.objects.filter(is_active=True, status__in=[VehicleStatus.ASSIGNED, VehicleStatus.ON_TRIP]).count()
        fleet_utilization = round((busy_vehicles / max(1, total_vehicles)) * 100.0, 1)

        unassigned_loads = FreightLoad.objects.filter(status__in=[CargoStatus.CREATED, CargoStatus.AVAILABLE]).count()
        delayed_shipments = FreightLoad.objects.filter(status="IN_TRANSIT").count()  # proxy

        # 2. Hazards & Infrastructure
        active_hazards = (
            HazardScore.objects.filter(hazard_index__gte=0.35).count()
            or TransportEdge.objects.filter(hazard_score__gte=0.35).count()
        )
        blocked_edges = TransportEdge.objects.filter(status__in=[EdgeStatus.BLOCKED, EdgeStatus.CRITICAL]).count()
        critical_corridors = 1 if blocked_edges > 0 else (1 if active_hazards >= 3 else 0)

        # 3. Overall Severity State
        if blocked_edges >= 3 or active_hazards >= 8:
            severity = NetworkHealthSnapshot.SeverityState.CRITICAL
        elif blocked_edges > 0 or active_hazards >= 3:
            severity = NetworkHealthSnapshot.SeverityState.WARNING
        elif active_hazards > 0:
            severity = NetworkHealthSnapshot.SeverityState.WATCH
        else:
            severity = NetworkHealthSnapshot.SeverityState.NORMAL

        # 4. Accessibility Score
        access_res = AccessibilityIntelligenceService.evaluate_corridor_accessibility()
        accessibility_score = access_res.get("accessibility_score", 82.5)

        # 5. Multimodal Terminal Status
        terminal_nodes = TransportNode.objects.filter(is_active=True, node_type__in=["MULTIMODAL_HUB", "PORT", "RAIL_YARD"])[:5]
        terminal_status = [
            {
                "id": str(t.id),
                "name": t.name,
                "type": t.node_type,
                "status": "OPERATIONAL",
                "mode": "MULTIMODAL",
            }
            for t in terminal_nodes
        ]

        # Critical Alerts Feed
        alerts = []
        if blocked_edges > 0:
            alerts.append({
                "severity": "CRITICAL",
                "message": f"{blocked_edges} network segment(s) blocked or critical due to monsoon slope failure.",
                "source": "MONITORING_TELEMETRY",
            })
        if unassigned_loads >= 5:
            alerts.append({
                "severity": "WATCH",
                "message": f"{unassigned_loads} freight demands awaiting vehicle dispatch.",
                "source": "FLEET_DISPATCH",
            })

        # Persist periodic snapshot if normal
        snapshot = NetworkHealthSnapshot.objects.create(
            severity_state=severity,
            active_trips_count=active_trips_count,
            delayed_shipments_count=delayed_shipments,
            active_hazards_count=active_hazards,
            critical_corridors_count=critical_corridors,
            fleet_utilization_pct=fleet_utilization,
            unassigned_freight_count=unassigned_loads,
            overall_accessibility_index=accessibility_score,
            multimodal_terminal_status={"terminals": terminal_status},
            critical_alerts=alerts,
        )

        return Response({
            "success": True,
            "severity_state": severity,
            "timestamp": snapshot.created_at,
            "metrics": {
                "active_trips": active_trips_count,
                "delayed_shipments": delayed_shipments,
                "active_hazards_count": active_hazards,
                "critical_corridors_count": critical_corridors,
                "fleet_utilization_pct": fleet_utilization,
                "unassigned_freight_count": unassigned_loads,
                "overall_accessibility_score": accessibility_score,
            },
            "multimodal_terminals": terminal_status,
            "critical_alerts": alerts,
            "recent_simulations_count": DisruptionSimulationRun.objects.count(),
            "recent_optimizations_count": OptimizationRun.objects.count(),
            "data_source": "CONFIGURED",
        }, status=status.HTTP_200_OK)


class CorridorHealthView(APIView):
    """
    GET /api/v1/intelligence/corridors/
    Lists major freight corridors with operational status, bottleneck risk, and mode redundancy.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        intel = AccessibilityIntelligenceService.get_network_accessibility_intelligence()
        return Response({
            "success": True,
            "corridors": intel.get("corridors", []),
            "most_vulnerable_nodes": intel.get("most_vulnerable_nodes", []),
            "recovery_priorities": intel.get("recovery_priorities", []),
        }, status=status.HTTP_200_OK)


class ExplainableRecommendationsView(APIView):
    """
    GET /api/v1/intelligence/recommendations/
    List recent explainable AI decisions with confidence and trade-off factors.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        dec_type = request.query_params.get("decision_type")
        qs = DecisionRecommendation.objects.all()
        if dec_type:
            qs = qs.filter(decision_type=dec_type)

        records = qs[:25]
        data = [
            {
                "id": str(r.id),
                "decision_type": r.decision_type,
                "title": r.title,
                "target_entity": f"{r.target_entity_type} #{r.target_entity_id[:8]}",
                "confidence": r.confidence,
                "confidence_pct": round(r.confidence * 100.0, 1),
                "primary_factors": r.primary_factors,
                "tradeoffs": r.tradeoffs,
                "algorithm_version": r.algorithm_version,
                "status": r.status,
                "created_at": r.created_at,
                "is_simulation": r.is_simulation,
            }
            for r in records
        ]
        return Response({"success": True, "count": len(data), "recommendations": data}, status=status.HTTP_200_OK)


class ETAIntelligenceView(APIView):
    """
    GET  /api/v1/intelligence/eta/ — List recent ETA prediction audit records.
    POST /api/v1/intelligence/eta/predict/ — Ad-hoc or route-based predictive ETA.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        records = ETAPredictionRecord.objects.select_related("origin_node", "destination_node").all()[:20]
        data = [
            {
                "id": str(r.id),
                "route_id": str(r.route_id) if r.route_id else None,
                "origin": r.origin_node.name if r.origin_node else "Origin",
                "destination": r.destination_node.name if r.destination_node else "Destination",
                "departure_time": r.departure_time,
                "predicted_eta": r.predicted_eta,
                "base_transit_time_min": r.base_transit_time_min,
                "predicted_transit_time_min": r.predicted_transit_time_min,
                "expected_delay_min": r.expected_delay_min,
                "delay_probability": r.delay_probability,
                "confidence_score": r.confidence_score,
                "contributing_factors": r.contributing_factors,
                "model_version": r.model_version,
                "data_source_mode": r.data_source_mode,
            }
            for r in records
        ]
        return Response({"success": True, "count": len(data), "data": data}, status=status.HTTP_200_OK)

    def post(self, request):
        route_id = request.data.get("route_id")
        origin_node_id = request.data.get("origin_node_id")
        destination_node_id = request.data.get("destination_node_id")
        rainfall_mm = float(request.data.get("weather_rainfall_mm", 0.0))

        if route_id:
            res = PredictiveETAService.predict_for_route(
                route_id=route_id,
                weather_rainfall_mm=rainfall_mm,
                trip_id=request.data.get("trip_id", ""),
                vehicle_id=request.data.get("vehicle_id", ""),
            )
        elif origin_node_id and destination_node_id:
            res = PredictiveETAService.predict_adhoc(
                origin_node_id=origin_node_id,
                destination_node_id=destination_node_id,
                weather_rainfall_mm=rainfall_mm,
                trip_id=request.data.get("trip_id", ""),
                vehicle_id=request.data.get("vehicle_id", ""),
            )
        else:
            return Response(
                {"success": False, "error": "Either route_id OR (origin_node_id and destination_node_id) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        http_status = status.HTTP_200_OK if res.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(res, status=http_status)


class AccessibilityIntelligenceAPIView(APIView):
    """
    GET /api/v1/intelligence/accessibility/
    Detailed network accessibility index with state, corridor, and vulnerable node breakdown.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        target_state = request.query_params.get("state")
        data = AccessibilityIntelligenceService.get_network_accessibility_intelligence(target_state=target_state)
        return Response(data, status=status.HTTP_200_OK)


class DemoScenarioOrchestrationView(APIView):
    """
    POST /api/v1/intelligence/demo-scenario/
    Executes the deterministic 20-step Phase 9 demo scenario and returns the audit trail.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.core.management.commands.phase9_demo import run_deterministic_phase9_demo
        steps_log = run_deterministic_phase9_demo()
        return Response({
            "success": True,
            "scenario": "PHASE_9_DETERMINISTIC_VERIFICATION",
            "steps_count": len(steps_log),
            "log": steps_log,
        }, status=status.HTTP_200_OK)
