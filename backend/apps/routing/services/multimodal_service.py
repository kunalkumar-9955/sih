"""
SIH26002 — Advanced Multimodal Route Optimization Service.

Coordinates network-level multi-modal routing across road, rail, and inland waterway (NW-2),
evaluating vehicle capacities, draft/depth limits, operating hours, geohazard risk,
delivery deadlines, and Pareto trade-offs.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.routing.constraints import ConstraintChecker, VehicleContext
from apps.routing.engine import RoutingEngine
from apps.routing.models import Route, RouteType
from apps.transport_graph.models import TransportEdge, TransportMode, TransportNode

logger = logging.getLogger("sih.routing.multimodal")


class MultimodalRouteOptimizationService:
    """
    Advanced Multimodal Optimization Engine.
    Exposes Pareto-aware multi-objective route generation.
    """

    @classmethod
    def optimize(
        cls,
        origin_id: str,
        destination_id: str,
        cargo_weight_kg: Optional[float] = None,
        cargo_type: Optional[str] = None,
        water_draft_m: Optional[float] = None,
        departure_time: Optional[datetime] = None,
        deadline_time: Optional[datetime] = None,
        avoid_modes: Optional[List[str]] = None,
        preferred_modes: Optional[List[str]] = None,
        allow_multimodal: bool = True,
        max_hazard_threshold: Optional[float] = None,
        priority: str = "NORMAL",
        is_disaster_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates Pareto-optimal multimodal route alternatives between origin and destination.
        """
        try:
            origin = TransportNode.objects.get(id=origin_id, is_active=True)
            destination = TransportNode.objects.get(id=destination_id, is_active=True)
        except TransportNode.DoesNotExist as e:
            return {
                "success": False,
                "error": f"Transport node not found: {str(e)}",
            }

        effective_departure = departure_time or timezone.now()

        # Build vehicle context
        v_context = VehicleContext(
            cargo_weight_kg=cargo_weight_kg,
            cargo_type=cargo_type,
            water_draft_m=water_draft_m,
            departure_time=effective_departure,
            avoid_modes=avoid_modes or [],
            preferred_modes=preferred_modes or [],
            allow_multimodal=allow_multimodal,
            max_hazard_threshold=max_hazard_threshold,
        )

        engine = RoutingEngine(vehicle_context=v_context)

        # Run Pareto multi-objective search
        pareto_result = engine.compute_pareto_multimodal_routes(
            origin=origin,
            destination=destination,
            vehicle_context=v_context,
            persist=True,
        )

        routes_data = []
        for r in pareto_result.get("routes", []):
            is_deadline_feasible = True
            slack_min = None
            if deadline_time:
                arrival_time = effective_departure + timezone.timedelta(minutes=r.total_time_min)
                slack_min = round((deadline_time - arrival_time).total_seconds() / 60.0, 1)
                is_deadline_feasible = slack_min >= 0

            routes_data.append({
                "id": str(r.id),
                "policy": r.route_type,
                "policy_display": r.get_route_type_display(),
                "total_distance_km": round(r.total_distance_m / 1000.0, 1),
                "total_time_min": r.total_time_min,
                "formatted_time": f"{int(r.total_time_min // 60)}h {int(r.total_time_min % 60)}m",
                "total_cost_inr": float(r.total_cost_inr or 0.0),
                "hazard_score": r.hazard_penalty_score,
                "safety_level": r.safety_level,
                "transfer_count": r.transfer_count,
                "modes_used": r.modes_used,
                "explanation": r.explanation,
                "is_deadline_feasible": is_deadline_feasible,
                "deadline_slack_min": slack_min,
                "segments_count": len(r.segments),
            })

        # Check multimodal redundancy
        multimodal_routes = [r for r in routes_data if r["transfer_count"] > 0 or any(m in (TransportMode.RAIL, TransportMode.WATER) for m in r["modes_used"])]
        has_redundancy = len(multimodal_routes) > 0

        pareto_map = {r["policy"].lower(): r for r in routes_data}
        best_route = routes_data[0] if routes_data else {}

        return {
            "success": True,
            "origin": {"id": str(origin.id), "name": origin.name, "node_type": origin.node_type},
            "destination": {"id": str(destination.id), "name": destination.name, "node_type": destination.node_type},
            "routes_evaluated_count": pareto_result.get("routes_evaluated", 0),
            "pareto_optimal_count": pareto_result.get("pareto_optimal_count", 0),
            "recommended_policy": pareto_result["recommended_route"].route_type if pareto_result.get("recommended_route") else "SAFEST",
            "best_composite_route": best_route,
            "pareto_frontier": pareto_map,
            "routes": routes_data,
            "tradeoffs": pareto_result.get("tradeoffs", []),
            "multimodal_redundancy": {
                "has_alternative_modes": has_redundancy,
                "modal_shift_options": [r["policy"] for r in multimodal_routes],
            },
            "constraints_applied": {
                "cargo_weight_kg": cargo_weight_kg,
                "cargo_type": cargo_type,
                "allow_multimodal": allow_multimodal,
                "departure_time": effective_departure.isoformat(),
                "deadline_time": deadline_time.isoformat() if deadline_time else None,
                "is_disaster_mode": is_disaster_mode,
            },
            "optimization_metadata": {
                "engine": "Dijkstra-Pareto-MultiModal-v2",
                "status": "COMPLETED",
                "data_mode": "CONFIGURED",
            },
        }

    @classmethod
    def optimize_multimodal_route(
        cls,
        origin_node_id: Optional[str] = None,
        destination_node_id: Optional[str] = None,
        origin_id: Optional[str] = None,
        destination_id: Optional[str] = None,
        weight_kg: Optional[float] = None,
        cargo_weight_kg: Optional[float] = None,
        preferred_mode: Optional[str] = None,
        preferred_modes: Optional[List[str]] = None,
        avoid_hazard_threshold: Optional[float] = None,
        max_hazard_threshold: Optional[float] = None,
        disaster_mode: bool = False,
        is_disaster_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        return cls.optimize(
            origin_id=origin_id or origin_node_id,
            destination_id=destination_id or destination_node_id,
            cargo_weight_kg=cargo_weight_kg or weight_kg,
            cargo_type=kwargs.get("cargo_type"),
            water_draft_m=kwargs.get("water_draft_m"),
            departure_time=kwargs.get("departure_time"),
            deadline_time=kwargs.get("deadline_time"),
            avoid_modes=kwargs.get("avoid_modes"),
            preferred_modes=preferred_modes or ([preferred_mode] if preferred_mode else None),
            allow_multimodal=kwargs.get("allow_multimodal", True),
            max_hazard_threshold=max_hazard_threshold or avoid_hazard_threshold,
            priority=kwargs.get("priority", "NORMAL"),
            is_disaster_mode=is_disaster_mode or disaster_mode,
        )
