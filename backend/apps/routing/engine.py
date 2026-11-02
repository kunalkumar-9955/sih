"""
SIH26002 — Hardened GIS Multimodal Routing Engine.

Core orchestration layer for risk-aware, multi-modal routing across the North Eastern Region.

Features:
- Dijkstra optimization with pluggable policies (FASTEST, SAFEST, CHEAPEST, MULTIMODAL)
- Explicit multimodal transfers (ROAD <-> RAIL <-> WATER) with transfer time & cost accounting
- Decoupled HazardProvider interface consuming real-time or static geohazard scores
- Vehicle payload, mode compatibility, and waterway depth constraint enforcement
- Dynamic, contextual route explanations generated from actual route traversal data
- Geometrically deduplicated alternative generation
- PostGIS LineString geometry synthesis
- Phase 4: Route safety summary (max hazard, risky/critical edge counts, safety classification)
"""
import heapq
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from django.conf import settings
from django.contrib.gis.geos import LineString, Point

from apps.hazards.models import HazardSeverity
from apps.transport_graph.models import EdgeStatus, TransportEdge, TransportMode, TransportNode
from .constraints import ConstraintChecker, VehicleContext
from .hazard_provider import HazardProvider, StaticHazardProvider
from .models import Route, RouteType
from .policies import BaseRoutingPolicy, get_routing_policy

logger = logging.getLogger("sih.routing.engine")


class RoutingEngine:
    """
    Hardened Multimodal Routing Engine.
    """

    def __init__(
        self,
        alpha: Optional[float] = None,
        hazard_provider: Optional[HazardProvider] = None,
        constraint_checker: Optional[ConstraintChecker] = None,
        vehicle_context: Optional[VehicleContext] = None,
    ):
        self.alpha = alpha if alpha is not None else getattr(settings, "ROUTING_HAZARD_ALPHA", 1.5)
        self.hazard_provider = hazard_provider or StaticHazardProvider()
        self.constraint_checker = constraint_checker or ConstraintChecker()
        self.vehicle_context = vehicle_context
        self.policy_map = {
            RouteType.FASTEST: get_routing_policy(RouteType.FASTEST, alpha=self.alpha),
            RouteType.SAFEST: get_routing_policy(RouteType.SAFEST, alpha=self.alpha),
            RouteType.CHEAPEST: get_routing_policy(RouteType.CHEAPEST, alpha=self.alpha),
            RouteType.MULTIMODAL: get_routing_policy(RouteType.MULTIMODAL, alpha=self.alpha),
            RouteType.LOWEST_RISK: get_routing_policy(RouteType.LOWEST_RISK, alpha=self.alpha),
            RouteType.BALANCED: get_routing_policy(RouteType.BALANCED, alpha=self.alpha),
            RouteType.EMERGENCY_CORRIDOR: get_routing_policy(RouteType.EMERGENCY_CORRIDOR, alpha=self.alpha),
        }

    def generate_route_explanation(
        self,
        policy: BaseRoutingPolicy,
        segments: List[Dict[str, Any]],
        total_time_min: float,
        total_cost_inr: float,
        hazard_score: float,
        modes_used: List[str],
        transfer_count: int,
    ) -> str:
        """
        Generates contextual explanation from actual computed route data.
        """
        has_rail = TransportMode.RAIL in modes_used
        has_water = TransportMode.WATER in modes_used or TransportMode.WATERWAY in modes_used
        has_landslide_avoidance = hazard_score < 0.25

        if policy.name == RouteType.SAFEST:
            if has_rail and transfer_count > 0:
                return (
                    f"Recommended SAFEST path: Bypasses hazardous hill road corridors "
                    f"(overall risk index {hazard_score:.2f}) by transferring to the heavy rail network "
                    f"at an intermodal freight terminal."
                )
            elif has_landslide_avoidance:
                return (
                    f"Recommended SAFEST path: Maximizes travel along low-risk, monitored highway segments "
                    f"with minimal geohazard exposure (risk index {hazard_score:.2f})."
                )
            return f"SAFEST route: Minimized cumulative landslide and terrain risk index ({hazard_score:.2f})."

        elif policy.name == RouteType.FASTEST:
            return (
                f"Recommended FASTEST path: Prioritizes direct high-throughput road corridors with estimated "
                f"transit time of {int(total_time_min // 60)}h {int(total_time_min % 60)}m."
            )

        elif policy.name == RouteType.CHEAPEST:
            if has_water:
                return (
                    f"Recommended CHEAPEST path: Leverages cost-efficient inland waterway river transit "
                    f"(estimated freight ₹{int(total_cost_inr):,})."
                )
            return f"CHEAPEST route: Lowest direct transport tariff at ₹{int(total_cost_inr):,}."

        elif policy.name == RouteType.MULTIMODAL:
            if transfer_count > 0:
                modes_str = " + ".join(m for m in modes_used if m != TransportMode.TRANSFER)
                return (
                    f"MULTIMODAL optimization: Integrates {modes_str} across {transfer_count} intermodal "
                    f"transfer point(s) to balance freight capacity, speed, and safety."
                )
            return "MULTIMODAL route: Direct modal transit with high operational reliability."

        elif policy.name == RouteType.LOWEST_RISK:
            return (
                f"LOWEST_RISK optimization: Strictly avoids high geohazard segments "
                f"(risk index {hazard_score:.2f}), maximizing infrastructure resilience."
            )

        elif policy.name == RouteType.BALANCED:
            return (
                f"BALANCED Pareto optimization: Balances transit time ({int(total_time_min // 60)}h {int(total_time_min % 60)}m), "
                f"freight cost (₹{int(total_cost_inr):,}), and risk exposure ({hazard_score:.2f})."
            )

        elif policy.name == RouteType.EMERGENCY_CORRIDOR:
            return (
                f"EMERGENCY CORRIDOR: Expedited humanitarian and disaster relief route authorized "
                f"for rapid regional deployment across priority networks."
            )

        return f"Calculated {policy.name} route across {len(segments)} network segments."


    def compute_single_route(
        self,
        origin: TransportNode,
        destination: TransportNode,
        policy: Optional[Any] = None,
        vehicle_context: Optional[VehicleContext] = None,
        max_hazard_threshold: Optional[float] = None,
        edges_pool: Optional[List[TransportEdge]] = None,
        route_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Executes Dijkstra on the transport graph with policy weighting and constraint checks.
        """
        start_id = origin.id
        target_id = destination.id

        if start_id == target_id:
            return None

        if policy is None:
            pol_name = route_type or RouteType.SAFEST
            policy = get_routing_policy(pol_name, alpha=self.alpha)
        elif isinstance(policy, str):
            policy = get_routing_policy(policy, alpha=self.alpha)

        if vehicle_context is None and self.vehicle_context is not None:
            vehicle_context = self.vehicle_context

        # 1. Fetch traversable edges
        if edges_pool is not None:
            edge_qs = edges_pool
        else:
            edge_qs = list(
                TransportEdge.objects.filter(is_available=True)
                .exclude(status__in=[EdgeStatus.BLOCKED, EdgeStatus.SEASONAL, EdgeStatus.UNDER_REPAIR])
                .select_related("source_node", "target_node")
            )

        # 2. Build adjacency list applying vehicle & mode constraints
        adj: Dict[Any, List[TransportEdge]] = {}
        for edge in edge_qs:
            # Check vehicle constraints
            allowed, _ = self.constraint_checker.is_edge_allowed(edge, vehicle_context)
            if not allowed:
                continue

            # Check hazard threshold
            hazard_data = self.hazard_provider.get_hazard(edge)
            if max_hazard_threshold is not None and hazard_data.hazard_score > max_hazard_threshold:
                continue

            adj.setdefault(edge.source_node_id, []).append(edge)

        # 3. Dijkstra Priority Queue
        pq: List[Tuple[float, Any]] = [(0.0, start_id)]
        distances: Dict[Any, float] = {start_id: 0.0}
        predecessors: Dict[Any, Tuple[Any, TransportEdge]] = {}
        visited: Set[Any] = set()

        while pq:
            current_dist, current_node_id = heapq.heappop(pq)

            if current_node_id in visited:
                continue
            visited.add(current_node_id)

            if current_node_id == target_id:
                break

            for edge in adj.get(current_node_id, []):
                next_node_id = edge.target_node_id
                if next_node_id in visited:
                    continue

                hazard_data = self.hazard_provider.get_hazard(edge)
                weight, traversable, _ = policy.calculate_weight(
                    edge=edge,
                    hazard_score=hazard_data.hazard_score,
                    vehicle_context=vehicle_context.__dict__ if vehicle_context else None,
                )

                if not traversable or weight == float("inf"):
                    continue

                new_dist = current_dist + weight

                if next_node_id not in distances or new_dist < distances[next_node_id]:
                    distances[next_node_id] = new_dist
                    predecessors[next_node_id] = (current_node_id, edge)
                    heapq.heappush(pq, (new_dist, next_node_id))

        if target_id not in predecessors and start_id != target_id:
            logger.info(
                f"No route available from {origin.name} to {destination.name} under policy {policy.name}"
            )
            return None

        # 4. Reconstruct path
        path_edges: List[TransportEdge] = []
        curr = target_id
        while curr != start_id:
            prev_id, edge = predecessors[curr]
            path_edges.append(edge)
            curr = prev_id
        path_edges.reverse()

        # 5. Aggregate metrics & format segments
        total_distance = 0.0
        total_time = 0.0
        total_cost = 0.0
        transfer_count = 0
        hazard_scores: List[float] = []
        modes_used_set: Set[str] = set()
        segments_data: List[Dict[str, Any]] = []
        coord_points = [Point(origin.geometry.x, origin.geometry.y, srid=4326)]

        for seq, e in enumerate(path_edges, start=1):
            norm_mode = e.normalized_mode
            modes_used_set.add(norm_mode)

            t_time = float(e.transfer_time_min or 0.0)
            t_cost = float(e.transfer_cost_inr or 0.0)
            if e.is_transfer:
                transfer_count += 1

            total_distance += float(e.distance_m)
            total_time += float(e.base_transit_time_min) + t_time
            total_cost += float(e.cost_inr or (e.base_transit_time_min * 25.0)) + t_cost

            h_data = self.hazard_provider.get_hazard(e)
            hazard_scores.append(h_data.hazard_score)

            tgt_geom = e.target_node.geometry
            if tgt_geom:
                coord_points.append(Point(tgt_geom.x, tgt_geom.y, srid=4326))

            segments_data.append({
                "sequence": seq,
                "edge_id": str(e.id),
                "source_node": e.source_node.name,
                "source_name": e.source_node.name,
                "source_node_id": str(e.source_node_id),
                "target_node": e.target_node.name,
                "target_name": e.target_node.name,
                "target_node_id": str(e.target_node_id),
                "mode": norm_mode,
                "distance_m": e.distance_m,
                "transit_time_min": e.base_transit_time_min,
                "cost_inr": float(e.cost_inr or (e.base_transit_time_min * 25.0)),
                "hazard_score": round(h_data.hazard_score, 3),
                "status": e.status,
                "transfer_time_min": e.transfer_time_min,
                "transfer_cost_inr": float(e.transfer_cost_inr) if e.transfer_cost_inr else None,
                "road_name": e.road_name,
            })

        avg_hazard = (sum(hazard_scores) / len(hazard_scores)) if hazard_scores else 0.0
        max_hazard = max(hazard_scores) if hazard_scores else 0.0
        risk_score = round((avg_hazard * 0.6) + (max_hazard * 0.4), 3)

        # Phase 4: Route safety summary
        thresholds = HazardSeverity.get_thresholds()
        moderate_threshold = thresholds["MODERATE"]
        critical_threshold = thresholds["CRITICAL"]
        risky_edge_count = sum(1 for h in hazard_scores if h >= moderate_threshold)
        critical_edge_count = sum(1 for h in hazard_scores if h >= critical_threshold)
        safety_level = HazardSeverity.classify(max_hazard)

        route_geom = LineString(coord_points, srid=4326) if len(coord_points) >= 2 else None
        modes_used_list = sorted(list(modes_used_set))

        explanation = self.generate_route_explanation(
            policy=policy,
            segments=segments_data,
            total_time_min=total_time,
            total_cost_inr=total_cost,
            hazard_score=risk_score,
            modes_used=modes_used_list,
            transfer_count=transfer_count,
        )

        return {
            "origin_node": origin,
            "destination_node": destination,
            "route_type": policy.name,
            "routing_policy": policy.name,
            "total_distance_m": round(total_distance, 1),
            "total_time_min": round(total_time, 1),
            "total_cost_inr": round(total_cost, 2),
            "hazard_penalty_score": risk_score,
            "risk_score": risk_score,
            "modes_used": modes_used_list,
            "transfer_count": transfer_count,
            "explanation": explanation,
            "geometry": route_geom,
            "segments": segments_data,
            "alpha_used": policy.alpha,
            # Phase 4 safety summary
            "max_hazard_score": round(max_hazard, 4),
            "risky_edge_count": risky_edge_count,
            "critical_edge_count": critical_edge_count,
            "safety_level": safety_level,
        }

    def compute_all_routes(
        self,
        origin: TransportNode,
        destination: TransportNode,
        requested_types: Optional[List[str]] = None,
        vehicle_context: Optional[VehicleContext] = None,
        alpha: Optional[float] = None,
        persist: bool = True,
        deduplicate: bool = True,
    ) -> List[Route]:
        """
        Computes all requested policy route alternatives, deduplicates redundant geometries,
        persists to DB if requested, and returns Route model instances.
        """
        types_to_compute = requested_types or [
            RouteType.SAFEST,
            RouteType.FASTEST,
            RouteType.CHEAPEST,
            RouteType.MULTIMODAL,
        ]

        # Pre-fetch active edges pool once for efficiency
        edges_pool = list(
            TransportEdge.objects.filter(is_available=True)
            .exclude(status__in=[EdgeStatus.BLOCKED, EdgeStatus.SEASONAL, EdgeStatus.UNDER_REPAIR])
            .select_related("source_node", "target_node")
        )

        computed_results: List[Dict[str, Any]] = []
        seen_geometries: Set[str] = set()

        for policy_name in types_to_compute:
            pol = get_routing_policy(policy_name, alpha=alpha or self.alpha)
            res = self.compute_single_route(
                origin=origin,
                destination=destination,
                policy=pol,
                vehicle_context=vehicle_context,
                edges_pool=edges_pool,
            )
            if not res:
                continue

            # Deduplication check: compare segment edge sequences
            seg_signature = ",".join(s["edge_id"] for s in res["segments"])
            if deduplicate and seg_signature in seen_geometries and len(computed_results) > 0:
                # Still include if it has unique policy insights, or skip exact identical duplicates
                continue

            seen_geometries.add(seg_signature)
            computed_results.append(res)

        routes: List[Route] = []
        for r_data in computed_results:
            if persist:
                # Mark older routes for this OD pair & policy as superseded
                Route.objects.filter(
                    origin_node=origin,
                    destination_node=destination,
                    route_type=r_data["route_type"],
                    is_current=True,
                ).update(is_current=False)

                route_obj = Route.objects.create(
                    origin_node=r_data["origin_node"],
                    destination_node=r_data["destination_node"],
                    route_type=r_data["route_type"],
                    total_distance_m=r_data["total_distance_m"],
                    total_time_min=r_data["total_time_min"],
                    total_cost_inr=r_data["total_cost_inr"],
                    hazard_penalty_score=r_data["hazard_penalty_score"],
                    modes_used=r_data["modes_used"],
                    transfer_count=r_data["transfer_count"],
                    explanation=r_data["explanation"],
                    geometry=r_data["geometry"],
                    segments=r_data["segments"],
                    alpha_used=r_data["alpha_used"],
                    # Phase 4 safety summary
                    max_hazard_score=r_data.get("max_hazard_score", 0.0),
                    risky_edge_count=r_data.get("risky_edge_count", 0),
                    critical_edge_count=r_data.get("critical_edge_count", 0),
                    safety_level=r_data.get("safety_level", "LOW"),
                    is_current=True,
                )
                routes.append(route_obj)
            else:
                route_obj = Route(
                    origin_node=r_data["origin_node"],
                    destination_node=r_data["destination_node"],
                    route_type=r_data["route_type"],
                    total_distance_m=r_data["total_distance_m"],
                    total_time_min=r_data["total_time_min"],
                    total_cost_inr=r_data["total_cost_inr"],
                    hazard_penalty_score=r_data["hazard_penalty_score"],
                    modes_used=r_data["modes_used"],
                    transfer_count=r_data["transfer_count"],
                    explanation=r_data["explanation"],
                    geometry=r_data["geometry"],
                    segments=r_data["segments"],
                    alpha_used=r_data["alpha_used"],
                    # Phase 4 safety summary
                    max_hazard_score=r_data.get("max_hazard_score", 0.0),
                    risky_edge_count=r_data.get("risky_edge_count", 0),
                    critical_edge_count=r_data.get("critical_edge_count", 0),
                    safety_level=r_data.get("safety_level", "LOW"),
                    is_current=True,
                )
                routes.append(route_obj)

        return routes

    def compute_pareto_multimodal_routes(
        self,
        origin: TransportNode,
        destination: TransportNode,
        vehicle_context: Optional[VehicleContext] = None,
        alpha: Optional[float] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Computes multi-objective Pareto-frontier multimodal routes.
        Evaluates FASTEST, SAFEST, CHEAPEST, MULTIMODAL, LOWEST_RISK, BALANCED.
        Identifies non-dominated alternatives across (Time, Cost, Hazard).
        Provides clear trade-off explanations between alternatives.
        """
        all_policies = [
            RouteType.FASTEST,
            RouteType.SAFEST,
            RouteType.CHEAPEST,
            RouteType.MULTIMODAL,
            RouteType.LOWEST_RISK,
            RouteType.BALANCED,
        ]
        routes = self.compute_all_routes(
            origin=origin,
            destination=destination,
            requested_types=all_policies,
            vehicle_context=vehicle_context,
            alpha=alpha,
            persist=persist,
            deduplicate=True,
        )

        # Build Pareto frontier
        pareto_routes = []
        tradeoffs = []

        for i, r_i in enumerate(routes):
            is_dominated = False
            t_i = r_i.total_time_min
            c_i = float(r_i.total_cost_inr or 0.0)
            h_i = r_i.hazard_penalty_score

            for j, r_j in enumerate(routes):
                if i == j:
                    continue
                t_j = r_j.total_time_min
                c_j = float(r_j.total_cost_inr or 0.0)
                h_j = r_j.hazard_penalty_score

                if t_j <= t_i and c_j <= c_i and h_j <= h_i and (t_j < t_i or c_j < c_i or h_j < h_i):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_routes.append(r_i)

        fastest = min(routes, key=lambda r: r.total_time_min, default=None)
        safest = min(routes, key=lambda r: r.hazard_penalty_score, default=None)
        cheapest = min(routes, key=lambda r: float(r.total_cost_inr or 0.0), default=None)

        if fastest and safest and fastest.id != safest.id:
            time_saved = safest.total_time_min - fastest.total_time_min
            hazard_delta = fastest.hazard_penalty_score - safest.hazard_penalty_score
            tradeoffs.append({
                "comparison": "FASTEST vs SAFEST",
                "time_delta_min": round(time_saved, 1),
                "hazard_reduction_pct": round((hazard_delta / max(0.01, fastest.hazard_penalty_score)) * 100.0, 1),
                "summary": f"FASTEST saves {time_saved:.0f}m transit time but has {hazard_delta:+.2f} higher geohazard risk compared to SAFEST.",
            })

        if cheapest and fastest and cheapest.id != fastest.id:
            cost_saved = float(fastest.total_cost_inr or 0.0) - float(cheapest.total_cost_inr or 0.0)
            tradeoffs.append({
                "comparison": "CHEAPEST vs FASTEST",
                "cost_saved_inr": round(cost_saved, 2),
                "summary": f"CHEAPEST reduces freight expense by ₹{cost_saved:,.0f}.",
            })

        return {
            "origin": {"id": str(origin.id), "name": origin.name},
            "destination": {"id": str(destination.id), "name": destination.name},
            "routes_evaluated": len(routes),
            "pareto_optimal_count": len(pareto_routes),
            "routes": routes,
            "pareto_routes": pareto_routes,
            "tradeoffs": tradeoffs,
            "recommended_route": pareto_routes[0] if pareto_routes else (routes[0] if routes else None),
        }

