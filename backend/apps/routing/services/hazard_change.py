"""
SIH26002 — Hazard Change Detector.

Monitors an active route for meaningful hazard degradation, status changes
(e.g., road closures, landslides, washouts), and threshold crossings that
warrant a reroute evaluation.
"""
import logging
from typing import Any, Dict, List, Optional
from django.conf import settings

from apps.hazards.models import HazardSeverity
from apps.routing.models import Route
from apps.transport_graph.models import EdgeStatus, TransportEdge
from .route_risk import RouteRiskEvaluator

logger = logging.getLogger("sih.routing.hazard_change")


class HazardChangeDetector:
    """
    Detects whether real-time hazard conditions along a route have degraded
    materially enough to justify recalculating the route.
    """

    def __init__(
        self,
        delta_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
    ):
        sih_settings = getattr(settings, "SIH_SETTINGS", {})
        self.delta_threshold = (
            delta_threshold
            if delta_threshold is not None
            else sih_settings.get("REROUTE_HAZARD_DELTA_THRESHOLD", 0.15)
        )
        self.critical_threshold = (
            critical_threshold
            if critical_threshold is not None
            else sih_settings.get("REROUTE_CRITICAL_THRESHOLD", 0.85)
        )

    def detect_route_change(
        self,
        route: Route,
        baseline_hazard: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compares route's current real-time state with its baseline.

        Parameters
        ----------
        route: Route
            The route currently assigned to the trip.
        baseline_hazard: Optional[float]
            Baseline hazard score when the route was assigned/started.
            If None, defaults to route.max_hazard_score or route.hazard_penalty_score.
        """
        current_eval = RouteRiskEvaluator.evaluate_route(route)
        current_max = current_eval["max_hazard_score"]
        blocked_edges = current_eval["blocked_edges"]

        if baseline_hazard is None:
            baseline_hazard = getattr(route, "max_hazard_score", 0.0) or 0.0

        hazard_delta = current_max - baseline_hazard
        triggering_edge_ids: List[str] = []
        reasons: List[str] = []
        is_blocked = len(blocked_edges) > 0
        is_critical = current_max >= self.critical_threshold

        # 1. Check for blocked / unavailable edges
        if is_blocked:
            for b in blocked_edges:
                triggering_edge_ids.append(b["edge_id"])
                reasons.append(f"Edge {b['source']} → {b['target']} is {b['reason']} ({b['status']})")

        # 2. Check for critical hazard threshold
        if is_critical and not is_blocked:
            reasons.append(
                f"Route peak hazard ({current_max:.2f}) exceeds CRITICAL threshold ({self.critical_threshold:.2f})"
            )
            # Find which edges are critical
            for e in current_eval["edge_evaluations"]:
                if e["hazard_score"] >= self.critical_threshold:
                    triggering_edge_ids.append(e["edge_id"])

        # 3. Check for significant delta increase
        elif hazard_delta >= self.delta_threshold:
            reasons.append(
                f"Hazard increased by +{hazard_delta:.2f} (baseline {baseline_hazard:.2f} → now {current_max:.2f})"
            )
            for e in current_eval["edge_evaluations"]:
                if e["hazard_score"] >= (baseline_hazard + self.delta_threshold):
                    triggering_edge_ids.append(e["edge_id"])

        should_reroute = is_blocked or is_critical or (hazard_delta >= self.delta_threshold)

        return {
            "should_reroute": should_reroute,
            "is_blocked": is_blocked,
            "is_critical": is_critical,
            "hazard_delta": round(hazard_delta, 4),
            "baseline_hazard": round(baseline_hazard, 4),
            "current_max_hazard": round(current_max, 4),
            "current_mean_hazard": current_eval["mean_hazard_score"],
            "trigger_reason": "; ".join(reasons) if reasons else "Hazard conditions within acceptable tolerance",
            "triggering_edge_ids": list(set(triggering_edge_ids)),
            "blocked_edges": blocked_edges,
            "risk_evaluation": current_eval,
        }
