"""
SIH26002 — Offline A* Routing Engine.

Provides standalone, in-memory graph search matching mobile edge routing requirements.
Operates on deserialized offline graph bundle structures without database access.
Implements A* search with Haversine distance heuristic, policy weighting, and physical constraint filtering.
"""
import heapq
import math
from typing import Any, Dict, List, Optional, Set, Tuple


def haversine_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Computes great-circle distance between two WGS84 coordinates in metres.
    """
    r = 6371000.0  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class OfflineAStarRouter:
    """
    In-memory A* graph search engine for offline routing.
    Accepts graph bundle JSON dictionary (nodes + edges).
    """

    DEFAULT_MAX_SPEED_MPS = 25.0  # ~90 km/h for heuristic denominator

    def __init__(self, graph_bundle: Dict[str, Any]):
        self.nodes: Dict[int, Dict[str, Any]] = {}
        self.adjacency: Dict[int, List[Dict[str, Any]]] = {}
        self.edges_by_id: Dict[int, Dict[str, Any]] = {}
        self._load_bundle(graph_bundle)

    def _load_bundle(self, bundle: Dict[str, Any]) -> None:
        """Parses graph bundle into fast lookup tables."""
        for n in bundle.get("nodes", []):
            nid = n["id"]
            self.nodes[nid] = n
            self.adjacency[nid] = []

        for e in bundle.get("edges", []):
            eid = e["id"]
            src = e["source_node_id"]
            self.edges_by_id[eid] = e
            if src in self.adjacency:
                self.adjacency[src].append(e)

    def _calculate_heuristic(
        self,
        current_node_id: int,
        target_node_id: int,
        policy: str,
    ) -> float:
        """
        Admissible Haversine heuristic estimating remaining cost to target.
        """
        curr = self.nodes.get(current_node_id)
        target = self.nodes.get(target_node_id)
        if not curr or not target:
            return 0.0

        c_coords = curr.get("coordinates", [0.0, 0.0])
        t_coords = target.get("coordinates", [0.0, 0.0])

        dist_m = haversine_distance_m(c_coords[0], c_coords[1], t_coords[0], t_coords[1])

        # Convert distance to minimal conceivable minutes
        min_transit_time_min = (dist_m / self.DEFAULT_MAX_SPEED_MPS) / 60.0

        if policy == "CHEAPEST":
            # Heuristic in approximate INR
            return min_transit_time_min * 20.0
        return min_transit_time_min

    def _evaluate_edge(
        self,
        edge: Dict[str, Any],
        policy: str,
        vehicle_weight_kg: Optional[float] = None,
        max_allowed_hazard: float = 1.0,
        allowed_modes: Optional[Set[str]] = None,
    ) -> Tuple[float, bool]:
        """
        Computes traversal weight and traversability based on policy & constraints.
        Returns: (cost, is_traversable)
        """
        if not edge.get("is_available", True):
            return float("inf"), False

        status = edge.get("status", "OPEN")
        if status in ("BLOCKED", "SEASONAL", "UNDER_REPAIR"):
            return float("inf"), False

        mode = edge.get("mode", "ROAD")
        if allowed_modes and mode not in allowed_modes:
            return float("inf"), False

        # Physical constraints
        cap = edge.get("capacity_kg")
        if cap is not None and vehicle_weight_kg is not None:
            if vehicle_weight_kg > cap:
                return float("inf"), False

        hazard_score = float(edge.get("hazard_score", 0.0))
        if hazard_score > max_allowed_hazard:
            return float("inf"), False

        # Status multiplier
        status_mult = 1.0
        if status == "RESTRICTED":
            status_mult = 1.35
        elif status == "CRITICAL":
            status_mult = 8.0 if policy == "SAFEST" else 3.5

        base_time = float(edge.get("base_transit_time_min", 0.0)) * status_mult
        transfer_time = float(edge.get("transfer_time_min", 0.0))
        cost_inr = float(edge.get("cost_inr") or (base_time * 25.0))
        transfer_cost = float(edge.get("transfer_cost_inr", 0.0))

        if policy == "FASTEST":
            weight = base_time + (transfer_time * 1.5) + (hazard_score * 5.0)
        elif policy == "SAFEST":
            hazard_factor = 1.0 + (1.5 * (hazard_score ** 2) * 6.0)
            weight = (base_time * hazard_factor) + transfer_time + (hazard_score * 250.0)
        elif policy == "CHEAPEST":
            weight = (cost_inr * status_mult) + transfer_cost + (base_time * 0.05)
        elif policy == "MULTIMODAL":
            mode_factor = 1.0
            if mode == "RAIL":
                mode_factor = 0.80
            elif mode in ("WATER", "WATERWAY"):
                mode_factor = 0.70
            hazard_factor = 1.0 + (1.5 * hazard_score)
            weight = (base_time * hazard_factor * mode_factor) + (transfer_time * 0.9)
        else:
            weight = base_time + (hazard_score * 10.0)

        return weight, True

    def find_path(
        self,
        origin_id: int,
        destination_id: int,
        policy: str = "SAFEST",
        vehicle_weight_kg: Optional[float] = None,
        max_allowed_hazard: float = 1.0,
        allowed_modes: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes A* search from origin to destination node.
        """
        if origin_id not in self.nodes or destination_id not in self.nodes:
            return {
                "found": False,
                "reason": "Origin or destination node not found in offline graph.",
                "node_ids": [],
                "edge_ids": [],
            }

        if origin_id == destination_id:
            return {
                "found": True,
                "node_ids": [origin_id],
                "edge_ids": [],
                "total_cost": 0.0,
                "total_distance_m": 0.0,
                "total_duration_min": 0.0,
                "total_cost_inr": 0.0,
                "avg_hazard_score": 0.0,
                "max_hazard_score": 0.0,
            }

        # Priority queue stores tuples: (f_score, current_g_cost, current_node_id)
        start_h = self._calculate_heuristic(origin_id, destination_id, policy)
        frontier = [(start_h, 0.0, origin_id)]

        g_scores: Dict[int, float] = {origin_id: 0.0}
        came_from: Dict[int, Tuple[int, int]] = {}  # node_id -> (prev_node_id, edge_id)
        visited: Set[int] = set()

        while frontier:
            _, current_g, current_node = heapq.heappop(frontier)

            if current_node in visited:
                continue
            visited.add(current_node)

            if current_node == destination_id:
                break

            for edge in self.adjacency.get(current_node, []):
                neighbor = edge["target_node_id"]
                if neighbor in visited:
                    continue

                edge_cost, traversable = self._evaluate_edge(
                    edge,
                    policy=policy,
                    vehicle_weight_kg=vehicle_weight_kg,
                    max_allowed_hazard=max_allowed_hazard,
                    allowed_modes=allowed_modes,
                )

                if not traversable:
                    continue

                tentative_g = current_g + edge_cost
                if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                    g_scores[neighbor] = tentative_g
                    came_from[neighbor] = (current_node, edge["id"])
                    h = self._calculate_heuristic(neighbor, destination_id, policy)
                    heapq.heappush(frontier, (tentative_g + h, tentative_g, neighbor))

        if destination_id not in came_from and origin_id != destination_id:
            return {
                "found": False,
                "reason": "No traversable path found under current policy and constraints.",
                "node_ids": [],
                "edge_ids": [],
            }

        # Reconstruct path
        path_nodes = [destination_id]
        path_edges = []
        curr = destination_id

        while curr in came_from:
            prev_node, edge_id = came_from[curr]
            path_edges.append(edge_id)
            path_nodes.append(prev_node)
            curr = prev_node

        path_nodes.reverse()
        path_edges.reverse()

        # Compute summary metrics
        total_dist_m = 0.0
        total_dur_min = 0.0
        total_cost_inr = 0.0
        hazard_scores = []

        for eid in path_edges:
            e = self.edges_by_id[eid]
            total_dist_m += float(e.get("distance_m", 0.0))
            total_dur_min += float(e.get("base_transit_time_min", 0.0)) + float(e.get("transfer_time_min", 0.0))
            cost = float(e.get("cost_inr", 0.0)) + float(e.get("transfer_cost_inr", 0.0))
            total_cost_inr += cost
            hazard_scores.append(float(e.get("hazard_score", 0.0)))

        avg_hazard = sum(hazard_scores) / len(hazard_scores) if hazard_scores else 0.0
        max_hazard = max(hazard_scores) if hazard_scores else 0.0

        return {
            "found": True,
            "policy": policy,
            "node_ids": path_nodes,
            "edge_ids": path_edges,
            "total_cost": round(g_scores.get(destination_id, 0.0), 2),
            "total_distance_m": round(total_dist_m, 2),
            "total_duration_min": round(total_dur_min, 2),
            "total_cost_inr": round(total_cost_inr, 2),
            "avg_hazard_score": round(avg_hazard, 4),
            "max_hazard_score": round(max_hazard, 4),
        }
