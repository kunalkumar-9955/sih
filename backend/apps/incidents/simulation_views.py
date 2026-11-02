"""
SIH26002 — Disruption Scenario Simulator API Views.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.users.permissions import IsAdminLevel
from apps.incidents.models import DisruptionSimulationRun
from apps.incidents.services.simulation_engine import DisruptionSimulationEngine


class SimulationRunView(APIView):
    """
    POST /api/v1/simulations/ — Trigger an isolated disruption simulation.
    GET  /api/v1/simulations/ — List previous simulation runs.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminLevel]

    def get(self, request):
        runs = DisruptionSimulationRun.objects.all()[:25]
        data = [
            {
                "id": str(r.id),
                "scenario_name": r.scenario_name,
                "scenario_type": r.scenario_type,
                "severity_level": r.severity_level,
                "affected_edges_count": r.affected_edges_count,
                "impacted_shipments_count": r.impacted_shipments_count,
                "pre_accessibility": r.pre_disruption_accessibility_score,
                "post_accessibility": r.post_disruption_accessibility_score,
                "accessibility_delta_pct": r.accessibility_delta_pct,
                "estimated_network_delay_hours": r.estimated_network_delay_hours,
                "created_at": r.created_at,
                "is_simulation": True,
            }
            for r in runs
        ]
        return Response({"success": True, "count": len(data), "data": data}, status=status.HTTP_200_OK)

    def post(self, request):
        scenario_type = request.data.get("scenario_type", "HEAVY_RAINFALL")
        target_corridor = request.data.get("target_corridor", "")
        target_state = request.data.get("target_state", "")
        custom_params = request.data.get("parameters", {})

        result = DisruptionSimulationEngine.run_scenario(
            scenario_type=scenario_type,
            target_corridor=target_corridor,
            target_state=target_state,
            custom_parameters=custom_params,
            persist=True,
            operator_user=request.user,
        )
        return Response(result, status=status.HTTP_200_OK)


class SimulationDetailView(APIView):
    """
    GET /api/v1/simulations/{id}/ — Retrieve detailed simulation run with per-asset impacts.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminLevel]

    def get(self, request, pk):
        try:
            run = DisruptionSimulationRun.objects.prefetch_related("impacts").get(pk=pk)
        except DisruptionSimulationRun.DoesNotExist:
            return Response({"success": False, "error": "Simulation run not found."}, status=status.HTTP_404_NOT_FOUND)

        impacts = [
            {
                "entity_type": i.entity_type,
                "entity_id": i.entity_id,
                "entity_name": i.entity_name,
                "impact_type": i.impact_type,
                "delay_added_min": i.delay_added_min,
                "notes": i.notes,
            }
            for i in run.impacts.all()
        ]

        return Response({
            "success": True,
            "data": {
                "id": str(run.id),
                "scenario_name": run.scenario_name,
                "scenario_type": run.scenario_type,
                "severity_level": run.severity_level,
                "target_corridor": run.target_corridor,
                "affected_edges_count": run.affected_edges_count,
                "affected_nodes_count": run.affected_nodes_count,
                "impacted_shipments_count": run.impacted_shipments_count,
                "impacted_vehicles_count": run.impacted_vehicles_count,
                "pre_accessibility_score": run.pre_disruption_accessibility_score,
                "post_accessibility_score": run.post_disruption_accessibility_score,
                "accessibility_delta_pct": run.accessibility_delta_pct,
                "multimodal_redundancy_before": run.multimodal_redundancy_before,
                "multimodal_redundancy_after": run.multimodal_redundancy_after,
                "redundancy_delta_pct": run.redundancy_delta_pct,
                "estimated_delay_hours": run.estimated_network_delay_hours,
                "alternative_routes_available": run.alternative_routes_available,
                "recovery_recommendations": run.recovery_recommendations,
                "impact_summary": run.impact_summary,
                "impacts": impacts,
                "is_simulation": True,
                "data_source": "SIMULATION",
            }
        }, status=status.HTTP_200_OK)


class SimulationComparisonView(APIView):
    """
    GET /api/v1/simulations/{id}/comparison/
    Returns side-by-side comparison of simulation run vs normal baseline.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            run = DisruptionSimulationRun.objects.get(pk=pk)
        except DisruptionSimulationRun.DoesNotExist:
            return Response({"success": False, "error": "Simulation not found."}, status=status.HTTP_404_NOT_FOUND)

        baseline_scenario = DisruptionSimulationEngine.run_scenario("NORMAL", persist=False)

        comparison = {
            "simulation_id": str(run.id),
            "scenario": run.scenario_type,
            "metrics": {
                "baseline_accessibility": baseline_scenario["resilience_delta"]["post_disruption_accessibility"],
                "simulated_accessibility": run.post_disruption_accessibility_score,
                "accessibility_loss_pct": run.accessibility_delta_pct,
                "baseline_redundancy": 88.0,
                "simulated_redundancy": run.multimodal_redundancy_after,
                "network_delay_hours": run.estimated_network_delay_hours,
                "impacted_shipments": run.impacted_shipments_count,
                "alternative_routes_remaining": run.alternative_routes_available,
            },
            "critical_corridors_affected": run.impact_summary.get("critical_bottlenecks", []),
            "recovery_recommendations": run.recovery_recommendations,
            "is_simulation": True,
            "data_source": "SIMULATION",
        }
        return Response({"success": True, "data": comparison}, status=status.HTTP_200_OK)


class SimulationQuickEvaluateView(APIView):
    """
    POST /api/v1/simulations/quick-evaluate/
    Evaluates scenarios comparison without persistence (e.g. NORMAL vs HEAVY_RAIN vs LANDSLIDE).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        scenarios = request.data.get("scenarios", ["NORMAL", "HEAVY_RAINFALL", "LANDSLIDE", "CRITICAL_CORRIDOR"])
        result = DisruptionSimulationEngine.compare_scenarios(scenarios)
        return Response(result, status=status.HTTP_200_OK)
