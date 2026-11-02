"""
SIH26002 — Centralized Routing Policies.

Defines the mathematical cost formulations and operational constraint evaluations
for FASTEST, SAFEST, CHEAPEST, and MULTIMODAL route optimization strategies.

All edge status penalties (OPEN, RESTRICTED, CRITICAL, BLOCKED) are centralized here.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from django.conf import settings

from apps.transport_graph.models import EdgeStatus, TransportEdge, TransportMode
from .models import RouteType


class BaseRoutingPolicy(ABC):
    """
    Abstract Base Class for all routing policies.
    """

    def __init__(self, name: str, alpha: Optional[float] = None):
        self.name = name
        self.route_type = name
        self.alpha = alpha if alpha is not None else getattr(settings, "ROUTING_HAZARD_ALPHA", 1.5)

    def evaluate_status_penalty(self, edge: TransportEdge) -> Tuple[float, bool]:
        """
        Evaluates edge status and returns (multiplier, is_allowed).
        - OPEN: normal traversal (1.0)
        - RESTRICTED: +30% transit time penalty (1.3)
        - CRITICAL: +250% transit time penalty (3.5)
        - BLOCKED / SEASONAL / UNDER_REPAIR: not allowed
        """
        if not edge.is_available:
            return 0.0, False

        if edge.status == EdgeStatus.BLOCKED:
            return 0.0, False

        if edge.status in (EdgeStatus.SEASONAL, EdgeStatus.UNDER_REPAIR):
            return 0.0, False

        if edge.status == EdgeStatus.RESTRICTED:
            return 1.35, True

        if edge.status == EdgeStatus.CRITICAL:
            # High penalty for critical status
            return 3.5, True

        return 1.0, True

    def calculate_edge_cost(
        self,
        edge: TransportEdge,
        vehicle_context: Optional[Any] = None,
        hazard_provider: Optional[Any] = None,
        hazard_score: Optional[float] = None,
    ) -> float:
        """Convenience method to calculate edge cost scalar."""
        if hazard_score is None:
            if hazard_provider is not None:
                hazard_score = hazard_provider.get_hazard(edge).hazard_score
            else:
                hazard_score = getattr(edge, "hazard_score", 0.0) or 0.0
        weight, _, _ = self.calculate_weight(edge, hazard_score, vehicle_context)
        return weight

    @abstractmethod
    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        """
        Calculates the edge traversal cost weight.
        Returns:
          (weight: float, is_traversable: bool, rejection_reason: str)
        """
        pass


class FastestPolicy(BaseRoutingPolicy):
    """
    FASTEST Policy: Prioritizes minimal transit time.
    Modest safety caution while seeking highest throughput corridor.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.FASTEST, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        status_mult, is_allowed = self.evaluate_status_penalty(edge)
        if not is_allowed:
            return float("inf"), False, f"Edge status '{edge.status}' is not traversable."

        transit_time = float(edge.base_transit_time_min) * status_mult
        transfer_time = float(edge.transfer_time_min or 0.0)

        # Minor hazard caution in fastest mode
        hazard_penalty = hazard_score * 5.0

        weight = transit_time + (transfer_time * 1.5) + hazard_penalty
        return weight, True, ""


class SafestPolicy(BaseRoutingPolicy):
    """
    SAFEST Policy: Strongly penalizes hazard score and bottleneck risks.
    Applies quadratic escalation on geohazard scores to avoid landslide zones.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.SAFEST, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        status_mult, is_allowed = self.evaluate_status_penalty(edge)
        if not is_allowed:
            return float("inf"), False, f"Edge status '{edge.status}' is not traversable."

        # In SAFEST policy, CRITICAL edges are strictly disfavored / excluded
        if edge.status == EdgeStatus.CRITICAL:
            status_mult = 8.0

        transit_time = float(edge.base_transit_time_min) * status_mult
        transfer_time = float(edge.transfer_time_min or 0.0)

        # Quadratic penalty factor for hazard: H in [0, 1]
        hazard_factor = 1.0 + (self.alpha * (hazard_score ** 2) * 6.0)
        risk_time_penalty = hazard_score * 250.0

        weight = (transit_time * hazard_factor) + transfer_time + risk_time_penalty
        return weight, True, ""


class CheapestPolicy(BaseRoutingPolicy):
    """
    CHEAPEST Policy: Prioritizes lowest financial freight cost.
    Optimizes segment INR freight rates and intermodal transfer fees.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.CHEAPEST, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        status_mult, is_allowed = self.evaluate_status_penalty(edge)
        if not is_allowed:
            return float("inf"), False, f"Edge status '{edge.status}' is not traversable."

        transit_time = float(edge.base_transit_time_min) * status_mult
        # Default cost model: cost_inr if present, else ~25 INR/min
        cost_inr = float(edge.cost_inr or (transit_time * 25.0))
        transfer_cost = float(edge.transfer_cost_inr or 0.0)

        # Cost weighted with small time tie-breaker
        weight = (cost_inr * status_mult) + transfer_cost + (transit_time * 0.05)
        return weight, True, ""


class MultimodalPolicy(BaseRoutingPolicy):
    """
    MULTIMODAL Policy: Optimizes combined time, risk, and multi-modal transfer efficiency.
    Gives efficiency discounts to stable rail and green inland waterway corridors.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.MULTIMODAL, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        status_mult, is_allowed = self.evaluate_status_penalty(edge)
        if not is_allowed:
            return float("inf"), False, f"Edge status '{edge.status}' is not traversable."

        transit_time = float(edge.base_transit_time_min) * status_mult
        transfer_time = float(edge.transfer_time_min or 0.0)
        norm_mode = edge.normalized_mode

        # Mode efficiency discount:
        # Rail: 20% discount on transit time for bulk reliability
        # Waterway: 30% discount for low emissions & river freight efficiency
        mode_factor = 1.0
        if norm_mode == TransportMode.RAIL:
            mode_factor = 0.80
        elif norm_mode == TransportMode.WATER:
            mode_factor = 0.70

        hazard_factor = 1.0 + (self.alpha * hazard_score)
        weight = (transit_time * hazard_factor * mode_factor) + (transfer_time * 0.9)
        return weight, True, ""


class LowestRiskPolicy(BaseRoutingPolicy):
    """
    LOWEST_RISK Policy: Extreme hazard avoidance.
    Strictly avoids any road with hazard score > 0.40 if any alternative exists.
    Favors waterways, rail sidings, and low-gradient bypass corridors.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.LOWEST_RISK, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        status_mult, is_allowed = self.evaluate_status_penalty(edge)
        if not is_allowed:
            return float("inf"), False, f"Edge status '{edge.status}' is not traversable."

        if edge.status == EdgeStatus.CRITICAL or hazard_score > 0.85:
            return float("inf"), False, f"Hazard score {hazard_score:.2f} exceeds lowest-risk threshold."

        transit_time = float(edge.base_transit_time_min) * status_mult
        transfer_time = float(edge.transfer_time_min or 0.0)

        hazard_penalty = (hazard_score ** 3) * 1000.0 + (hazard_score * 300.0)
        weight = transit_time + transfer_time + hazard_penalty
        return weight, True, ""


class BalancedPolicy(BaseRoutingPolicy):
    """
    BALANCED Policy: Pareto composite balance across time, financial cost, and geohazard risk.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.BALANCED, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        status_mult, is_allowed = self.evaluate_status_penalty(edge)
        if not is_allowed:
            return float("inf"), False, f"Edge status '{edge.status}' is not traversable."

        transit_time = float(edge.base_transit_time_min) * status_mult
        transfer_time = float(edge.transfer_time_min or 0.0)
        cost_inr = float(edge.cost_inr or (transit_time * 25.0))
        transfer_cost = float(edge.transfer_cost_inr or 0.0)

        time_component = (transit_time + transfer_time * 1.2) * 0.40
        cost_component = ((cost_inr + transfer_cost) / 40.0) * 0.30
        safety_component = (hazard_score * 200.0) * 0.30

        weight = time_component + cost_component + safety_component
        return weight, True, ""


class EmergencyDisasterPolicy(BaseRoutingPolicy):
    """
    EMERGENCY_CORRIDOR Policy: Disaster relief response prioritization.
    Expedited transfer processing and high-priority passage.
    """

    def __init__(self, alpha: Optional[float] = None):
        super().__init__(RouteType.EMERGENCY_CORRIDOR, alpha)

    def calculate_weight(
        self,
        edge: TransportEdge,
        hazard_score: float,
        vehicle_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, bool, str]:
        if not edge.is_available or edge.status == EdgeStatus.BLOCKED:
            return float("inf"), False, f"Edge status '{edge.status}' is physically blocked."

        status_mult = 1.1 if edge.status == EdgeStatus.RESTRICTED else 1.0
        if edge.status == EdgeStatus.CRITICAL:
            status_mult = 2.0

        transit_time = float(edge.base_transit_time_min) * status_mult
        transfer_time = float(edge.transfer_time_min or 0.0) * 0.3
        hazard_penalty = hazard_score * 40.0

        weight = transit_time + transfer_time + hazard_penalty
        return weight, True, ""


def get_routing_policy(policy_type: str, alpha: Optional[float] = None) -> BaseRoutingPolicy:
    """
    Factory function returning the corresponding RoutingPolicy instance.
    """
    normalized = policy_type.upper().strip()
    if normalized == RouteType.FASTEST:
        return FastestPolicy(alpha=alpha)
    elif normalized == RouteType.SAFEST:
        return SafestPolicy(alpha=alpha)
    elif normalized == RouteType.CHEAPEST:
        return CheapestPolicy(alpha=alpha)
    elif normalized == RouteType.MULTIMODAL:
        return MultimodalPolicy(alpha=alpha)
    elif normalized == RouteType.LOWEST_RISK:
        return LowestRiskPolicy(alpha=alpha)
    elif normalized == RouteType.BALANCED:
        return BalancedPolicy(alpha=alpha)
    elif normalized == RouteType.EMERGENCY_CORRIDOR:
        return EmergencyDisasterPolicy(alpha=alpha)
    # Default fallback
    return SafestPolicy(alpha=alpha)


class RoutingPolicyFactory:
    @staticmethod
    def get_policy(policy_type: str, alpha: Optional[float] = None) -> BaseRoutingPolicy:
        return get_routing_policy(policy_type, alpha=alpha)


