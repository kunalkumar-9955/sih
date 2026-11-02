"""
SIH26002 — Route Risk Evaluator Service.

Evaluates an existing Route or segment edge list against current real-time
edge hazard scores and operational statuses.
"""
import logging
from typing import Any, Dict, List, Optional
from django.utils import timezone

from apps.hazards.models import HazardSeverity
from apps.routing.models import Route
from apps.transport_graph.models import EdgeStatus, TransportEdge

logger = logging.getLogger("sih.routing.route_risk")


class RouteRiskEvaluator:
    """
    Evaluates real-time risk of a given route or route segments.
    """

    @classmethod
    def evaluate_route(cls, route: Route) -> Dict[str, Any]:
        """
        Evaluate live risk for a persisted Route instance using its segment edges.
        """
        edge_ids: List[str] = []
        if route.segments:
            for seg in route.segments:
                e_id = seg.get("edge_id")
                if e_id:
                    edge_ids.append(str(e_id))

        return cls.evaluate_edge_ids(edge_ids=edge_ids, route_id=str(route.id))

    @classmethod
    def evaluate_edge_ids(
        cls,
        edge_ids: List[str],
        route_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates risk for an ordered sequence of edge IDs.
        """
        now = timezone.now()
        if not edge_ids:
            return {
                "route_id": route_id,
                "evaluated_at": now.isoformat(),
                "edge_count": 0,
                "max_hazard_score": 0.0,
                "mean_hazard_score": 0.0,
                "risky_edge_count": 0,
                "critical_edge_count": 0,
                "blocked_edges": [],
                "safety_level": HazardSeverity.LOW,
                "has_critical_or_blocked": False,
                "edge_evaluations": [],
            }

        # Query current edge state
        edges = TransportEdge.objects.filter(id__in=edge_ids).select_related(
            "source_node", "target_node"
        )
        edge_map = {str(e.id): e for e in edges}

        scores: List[float] = []
        risky_count = 0
        critical_count = 0
        blocked_edges: List[Dict[str, Any]] = []
        edge_evaluations: List[Dict[str, Any]] = []

        thresholds = HazardSeverity.get_thresholds()

        for eid in edge_ids:
            edge = edge_map.get(str(eid))
            if not edge:
                continue

            h_score = float(edge.hazard_score or 0.0)
            scores.append(h_score)
            status = edge.status

            is_blocked = (
                not edge.is_available
                or status in [EdgeStatus.BLOCKED, EdgeStatus.UNDER_REPAIR, EdgeStatus.SEASONAL]
            )
            is_critical = h_score >= thresholds["CRITICAL"]
            is_risky = h_score >= thresholds["MODERATE"]

            if is_risky:
                risky_count += 1
            if is_critical:
                critical_count += 1

            if is_blocked or is_critical:
                blocked_edges.append({
                    "edge_id": str(edge.id),
                    "source": edge.source_node.name,
                    "target": edge.target_node.name,
                    "status": status,
                    "hazard_score": h_score,
                    "reason": "BLOCKED" if is_blocked else "CRITICAL_HAZARD",
                })

            edge_evaluations.append({
                "edge_id": str(edge.id),
                "source": edge.source_node.name,
                "target": edge.target_node.name,
                "status": status,
                "hazard_score": h_score,
                "severity": HazardSeverity.classify(h_score),
                "is_blocked": is_blocked,
            })

        max_h = max(scores) if scores else 0.0
        mean_h = sum(scores) / len(scores) if scores else 0.0
        safety_level = HazardSeverity.classify(max_h)

        return {
            "route_id": route_id,
            "evaluated_at": now.isoformat(),
            "edge_count": len(edge_evaluations),
            "max_hazard_score": round(max_h, 4),
            "mean_hazard_score": round(mean_h, 4),
            "risky_edge_count": risky_count,
            "critical_edge_count": critical_count,
            "blocked_edges": blocked_edges,
            "safety_level": safety_level,
            "has_critical_or_blocked": len(blocked_edges) > 0,
            "edge_evaluations": edge_evaluations,
        }
