"""
SIH26002 — Explainable AI Decision Engine.

Provides an auditable, standardized explanation layer for all AI and optimization
recommendations (routes, reroutes, fleet dispatches, consolidations, ETA predictions,
and emergency escalation).
"""
import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.analytics.models import DecisionRecommendation

logger = logging.getLogger("sih.analytics.explainability")


class DecisionExplanationService:
    """
    Central explanation registry and contract generator for AI decisions.
    """

    @classmethod
    def record_decision(
        cls,
        decision_type: str,
        title: str,
        target_entity_type: str,
        target_entity_id: str,
        recommendation_payload: Dict[str, Any],
        confidence: float,
        primary_factors: List[Dict[str, Any]],
        tradeoffs: Optional[List[Dict[str, Any]]] = None,
        algorithm_version: str = "explainable-ai-v2.0",
        is_simulation: bool = False,
        operator_user: Optional[Any] = None,
    ) -> DecisionRecommendation:
        """
        Standardizes and records an explainable AI decision.
        """
        recommendation = DecisionRecommendation.objects.create(
            decision_type=decision_type,
            title=title,
            target_entity_type=target_entity_type,
            target_entity_id=str(target_entity_id),
            recommendation_payload=recommendation_payload,
            confidence=max(0.0, min(1.0, confidence)),
            primary_factors=primary_factors,
            tradeoffs=tradeoffs or [],
            algorithm_version=algorithm_version,
            is_simulation=is_simulation,
            status=DecisionRecommendation.RecommendationStatus.GENERATED,
            operator=operator_user,
        )
        return recommendation

    @classmethod
    def explain_route_selection(
        cls,
        route_obj: Any,
        alternative_routes: List[Any],
        tradeoffs: List[Dict[str, Any]],
        confidence: float = 0.90,
        operator_user: Optional[Any] = None,
    ) -> DecisionRecommendation:
        """Helper to create route decision explanation."""
        factors = [
            {
                "factor": "Geohazard Risk Index",
                "impact": f"Reduced to {route_obj.hazard_penalty_score:.2f}",
                "weight": 0.35,
                "description": "Evaluated landslide susceptibility, rainfall, and terrain steepness.",
            },
            {
                "factor": "Estimated Transit Time",
                "impact": f"{int(route_obj.total_time_min // 60)}h {int(route_obj.total_time_min % 60)}m",
                "weight": 0.35,
                "description": "Computed with actual road status penalties.",
            },
            {
                "factor": "Intermodal Transfers",
                "impact": f"{route_obj.transfer_count} modal transfer(s)",
                "weight": 0.15,
                "description": f"Modes utilized: {', '.join(route_obj.modes_used)}",
            },
            {
                "factor": "Estimated Cost",
                "impact": f"₹{int(route_obj.total_cost_inr or 0):,}",
                "weight": 0.15,
                "description": "Standard regional freight tariff model.",
            },
        ]

        return cls.record_decision(
            decision_type=DecisionRecommendation.DecisionType.ROUTE_RECOMMENDATION,
            title=f"Selected {route_obj.get_route_type_display()} route for {route_obj.origin_node.name} → {route_obj.destination_node.name}",
            target_entity_type="Route",
            target_entity_id=str(route_obj.id),
            recommendation_payload={
                "route_id": str(route_obj.id),
                "route_type": route_obj.route_type,
                "total_distance_km": round(route_obj.total_distance_m / 1000.0, 1),
                "total_time_min": route_obj.total_time_min,
                "explanation": route_obj.explanation,
            },
            confidence=confidence,
            primary_factors=factors,
            tradeoffs=tradeoffs,
            algorithm_version="dijkstra-pareto-explain-v2",
            operator_user=operator_user,
        )
