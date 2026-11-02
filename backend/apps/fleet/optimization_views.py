"""
SIH26002 — Fleet Optimization & Load Consolidation API Views.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.fleet.models import ConsolidationBundle, OptimizationRun
from apps.fleet.services.dynamic_consolidation_service import DynamicLoadConsolidationService
from apps.fleet.services.fleet_optimizer import MultiDepotFleetOptimizer
from apps.users.permissions import CanManageFleet


class FleetOptimizationView(APIView):
    """
    POST /api/v1/optimization/fleet/
    Runs multi-depot, multi-vehicle dispatch optimization.
    """
    permission_classes = [permissions.IsAuthenticated, CanManageFleet]

    def post(self, request):
        depot_ids = request.data.get("depot_ids")
        load_ids = request.data.get("load_ids")
        vehicle_ids = request.data.get("vehicle_ids")
        max_detour_km = float(request.data.get("max_detour_km", 40.0))
        enable_consolidation = bool(request.data.get("enable_consolidation", True))
        is_simulation = bool(request.data.get("is_simulation", False))

        result = MultiDepotFleetOptimizer.optimize(
            depot_ids=depot_ids,
            load_ids=load_ids,
            vehicle_ids=vehicle_ids,
            max_detour_km=max_detour_km,
            enable_consolidation=enable_consolidation,
            is_simulation=is_simulation,
            operator_user=request.user,
        )

        http_status = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)


class ConsolidationOptimizationView(APIView):
    """
    POST /api/v1/optimization/consolidation/
    Scans active loads and identifies multi-shipment consolidation opportunities.
    """
    permission_classes = [permissions.IsAuthenticated, CanManageFleet]

    def post(self, request):
        max_bundle_size = int(request.data.get("max_bundle_size", 4))
        max_cluster_radius_km = float(request.data.get("max_cluster_radius_km", 45.0))
        is_simulation = bool(request.data.get("is_simulation", False))

        result = DynamicLoadConsolidationService.generate_recommendations(
            max_bundle_size=max_bundle_size,
            max_cluster_radius_km=max_cluster_radius_km,
            persist=True,
            is_simulation=is_simulation,
        )
        return Response(result, status=status.HTTP_200_OK)


class OptimizationRunListView(APIView):
    """
    GET /api/v1/optimization/runs/
    List previous optimization runs.
    """
    permission_classes = [permissions.IsAuthenticated, CanManageFleet]

    def get(self, request):
        runs = OptimizationRun.objects.all()[:20]
        data = [
            {
                "id": str(r.id),
                "name": r.name,
                "mode": r.mode,
                "status": r.status,
                "improvement_pct": r.improvement_pct,
                "total_distance_saved_km": r.total_distance_saved_km,
                "estimated_cost_savings_inr": float(r.estimated_cost_savings_inr),
                "vehicle_utilization_avg_pct": r.vehicle_utilization_avg_pct,
                "assigned_loads_count": r.assigned_loads_count,
                "created_at": r.created_at,
                "is_simulation": r.is_simulation,
            }
            for r in runs
        ]
        return Response({"success": True, "count": len(data), "data": data}, status=status.HTTP_200_OK)


class OptimizationRunDetailView(APIView):
    """
    GET /api/v1/optimization/runs/{id}/
    Retrieve detailed assignments and metrics for a specific optimization run.
    """
    permission_classes = [permissions.IsAuthenticated, CanManageFleet]

    def get(self, request, pk):
        try:
            run = OptimizationRun.objects.prefetch_related("assignments__assigned_loads", "assignments__vehicle").get(pk=pk)
        except OptimizationRun.DoesNotExist:
            return Response({"success": False, "error": "Optimization run not found."}, status=status.HTTP_404_NOT_FOUND)

        assignments_data = []
        for a in run.assignments.all():
            assignments_data.append({
                "id": str(a.id),
                "vehicle_registration": a.vehicle.registration_number,
                "depot_name": a.depot.name if a.depot else None,
                "total_weight_kg": float(a.total_weight_kg),
                "capacity_utilization_pct": a.capacity_utilization_pct,
                "total_distance_km": a.total_distance_km,
                "estimated_cost_inr": float(a.estimated_cost_inr),
                "estimated_duration_min": a.estimated_duration_min,
                "stop_sequence": a.stop_sequence,
                "assigned_loads_count": a.assigned_loads.count(),
                "explanation": a.explanation,
            })

        return Response({
            "success": True,
            "data": {
                "id": str(run.id),
                "name": run.name,
                "mode": run.mode,
                "status": run.status,
                "baseline_metrics": run.baseline_metrics,
                "optimized_metrics": run.optimized_metrics,
                "improvement_pct": run.improvement_pct,
                "total_distance_saved_km": run.total_distance_saved_km,
                "estimated_cost_savings_inr": float(run.estimated_cost_savings_inr),
                "vehicle_utilization_avg_pct": run.vehicle_utilization_avg_pct,
                "unassigned_loads": run.unassigned_loads,
                "execution_time_ms": run.execution_time_ms,
                "assignments": assignments_data,
                "is_simulation": run.is_simulation,
            }
        }, status=status.HTTP_200_OK)


class ConsolidationBundleListView(APIView):
    """
    GET /api/v1/optimization/bundles/
    List recommended or active consolidation bundles.
    """
    permission_classes = [permissions.IsAuthenticated, CanManageFleet]

    def get(self, request):
        bundles = ConsolidationBundle.objects.prefetch_related("loads", "origin_hub", "destination_hub").all()[:20]
        data = [
            {
                "id": str(b.id),
                "bundle_code": b.bundle_code,
                "loads_count": b.loads.count(),
                "origin_hub_name": b.origin_hub.name if b.origin_hub else None,
                "destination_hub_name": b.destination_hub.name if b.destination_hub else None,
                "total_weight_kg": float(b.total_weight_kg),
                "expected_utilization_pct": b.expected_utilization_pct,
                "estimated_cost_savings_inr": float(b.estimated_cost_savings_inr),
                "estimated_delay_impact_min": b.estimated_delay_impact_min,
                "status": b.status,
                "reasons": b.consolidation_reasons,
                "is_estimate": b.is_estimate,
            }
            for b in bundles
        ]
        return Response({"success": True, "count": len(data), "data": data}, status=status.HTTP_200_OK)
