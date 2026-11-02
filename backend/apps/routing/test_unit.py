"""
SIH26002 — Routing Engine Pure Unit Tests.
Tests Policies, Constraints, Hazard Providers, and Explanations.
"""
import pytest
from apps.routing.constraints import ConstraintChecker, VehicleContext
from apps.routing.engine import RoutingEngine
from apps.routing.hazard_provider import HazardScoreData, MockHazardProvider, StaticHazardProvider
from apps.routing.models import RouteType
from apps.routing.policies import (
    BaseRoutingPolicy,
    CheapestPolicy,
    FastestPolicy,
    MultimodalPolicy,
    SafestPolicy,
    get_routing_policy,
)
from apps.transport_graph.models import EdgeStatus, NodeType, TransportMode


class DummyEdge:
    def __init__(
        self,
        edge_id="e1",
        base_transit_time_min=60.0,
        cost_inr=1000.0,
        hazard_score=0.2,
        mode=TransportMode.ROAD,
        status=EdgeStatus.OPEN,
        is_available=True,
        capacity_kg=15000.0,
        water_level_m=None,
        min_required_depth_m=None,
        draft_requirement_m=None,
        seasonal_open_month=None,
        seasonal_close_month=None,
        transfer_time_min=0.0,
        transfer_cost_inr=0.0,
        road_name="NH-6",
    ):
        self.id = edge_id
        self.base_transit_time_min = base_transit_time_min
        self.cost_inr = cost_inr
        self.hazard_score = hazard_score
        self.mode = mode
        self.status = status
        self.is_available = is_available
        self.capacity_kg = capacity_kg
        self.water_level_m = water_level_m
        self.min_required_depth_m = min_required_depth_m
        self.draft_requirement_m = draft_requirement_m
        self.seasonal_open_month = seasonal_open_month
        self.seasonal_close_month = seasonal_close_month
        self.transfer_time_min = transfer_time_min
        self.transfer_cost_inr = transfer_cost_inr
        self.road_name = road_name

    @property
    def normalized_mode(self):
        return TransportMode.normalize(self.mode)

    @property
    def is_transfer(self):
        return self.normalized_mode == TransportMode.TRANSFER

    @property
    def is_waterway(self):
        return self.normalized_mode == TransportMode.WATER


class TestRoutingPolicies:

    def test_fastest_policy_edge_cost(self):
        policy = FastestPolicy()
        edge = DummyEdge(base_transit_time_min=45.0, hazard_score=0.0, status=EdgeStatus.OPEN)
        weight, traversable, _ = policy.calculate_weight(edge, hazard_score=0.0)
        assert traversable is True
        assert weight == pytest.approx(45.0)

    def test_safest_policy_penalizes_hazard(self):
        policy = SafestPolicy(alpha=2.5)
        # Low hazard edge (0.05) vs High hazard edge (0.80) with same transit time
        low_hazard_edge = DummyEdge(base_transit_time_min=60.0)
        high_hazard_edge = DummyEdge(base_transit_time_min=60.0)

        weight_low, _, _ = policy.calculate_weight(low_hazard_edge, hazard_score=0.05)
        weight_high, _, _ = policy.calculate_weight(high_hazard_edge, hazard_score=0.80)

        assert weight_high > weight_low * 2.0

    def test_cheapest_policy_cost(self):
        policy = CheapestPolicy()
        edge = DummyEdge(cost_inr=750.0, base_transit_time_min=60.0, status=EdgeStatus.OPEN)
        weight, traversable, _ = policy.calculate_weight(edge, hazard_score=0.1)
        assert traversable is True
        # cost (750) + transfer_cost (0) + 60 * 0.05 (3.0) = 753.0
        assert weight == pytest.approx(753.0)

    def test_multimodal_policy_combines_factors(self):
        policy = MultimodalPolicy()
        edge = DummyEdge(base_transit_time_min=60.0, cost_inr=500.0, hazard_score=0.1)
        weight, traversable, _ = policy.calculate_weight(edge, hazard_score=0.1)
        assert traversable is True
        assert weight > 0.0

    def test_edge_status_penalties(self):
        policy = FastestPolicy()
        open_edge = DummyEdge(base_transit_time_min=50.0, status=EdgeStatus.OPEN)
        restricted_edge = DummyEdge(base_transit_time_min=50.0, status=EdgeStatus.RESTRICTED)
        critical_edge = DummyEdge(base_transit_time_min=50.0, status=EdgeStatus.CRITICAL)
        blocked_edge = DummyEdge(base_transit_time_min=50.0, status=EdgeStatus.BLOCKED)

        w_open, _, _ = policy.calculate_weight(open_edge, hazard_score=0.0)
        w_restricted, _, _ = policy.calculate_weight(restricted_edge, hazard_score=0.0)
        w_critical, _, _ = policy.calculate_weight(critical_edge, hazard_score=0.0)
        w_blocked, t_blocked, _ = policy.calculate_weight(blocked_edge, hazard_score=0.0)

        assert w_open == 50.0
        assert w_restricted == pytest.approx(50.0 * 1.35)
        assert w_critical == pytest.approx(50.0 * 3.5)
        assert t_blocked is False


class TestConstraintChecker:

    def test_payload_limit_enforced(self):
        checker = ConstraintChecker()
        edge = DummyEdge(capacity_kg=10000.0)

        light_truck = VehicleContext(cargo_weight_kg=8000.0)
        allowed, _ = checker.is_edge_allowed(edge, light_truck)
        assert allowed is True

        heavy_truck = VehicleContext(cargo_weight_kg=18000.0)
        allowed, _ = checker.is_edge_allowed(edge, heavy_truck)
        assert allowed is False

    def test_waterway_depth_enforced(self):
        checker = ConstraintChecker()
        water_edge = DummyEdge(
            mode=TransportMode.WATER,
            water_level_m=1.8,
            min_required_depth_m=2.0,
            draft_requirement_m=2.2,
        )

        # Deep draft vessel (2.2m) cannot navigate 1.8m channel
        deep_vessel = VehicleContext(water_draft_m=2.2)
        allowed, reason = checker.is_edge_allowed(water_edge, deep_vessel)
        assert allowed is False
        assert "exceeds" in reason or "below" in reason

        # Shallow vessel (1.5m) in sufficiently deep river (3.0m)
        deep_water_edge = DummyEdge(
            mode=TransportMode.WATER,
            water_level_m=3.0,
            min_required_depth_m=2.0,
            draft_requirement_m=2.5,
        )
        shallow_vessel = VehicleContext(water_draft_m=1.5)
        allowed, _ = checker.is_edge_allowed(deep_water_edge, shallow_vessel)
        assert allowed is True

    def test_mode_avoidance_enforced(self):
        checker = ConstraintChecker()
        rail_edge = DummyEdge(mode=TransportMode.RAIL)
        avoid_rail_context = VehicleContext(avoid_modes=["RAIL"])

        allowed, _ = checker.is_edge_allowed(rail_edge, avoid_rail_context)
        assert allowed is False


class TestHazardProvider:

    def test_mock_hazard_provider_returns_configured_score(self):
        provider = MockHazardProvider(default_score=0.75)
        edge = DummyEdge(hazard_score=0.1)
        res = provider.get_hazard(edge)
        assert res.hazard_score == 0.75
        assert res.confidence == 1.0

    def test_static_hazard_provider_reads_edge(self):
        provider = StaticHazardProvider()
        edge = DummyEdge(hazard_score=0.42)
        res = provider.get_hazard(edge)
        assert res.hazard_score == 0.42


class TestExplanationGenerator:

    def test_explanation_generation_contains_key_insights(self):
        segments = [
            {"mode": "ROAD", "hazard_score": 0.05, "status": "OPEN", "road_name": "NH-27"},
            {"mode": "TRANSFER", "hazard_score": 0.0, "status": "OPEN", "road_name": "Transfer Hub"},
            {"mode": "RAIL", "hazard_score": 0.02, "status": "OPEN", "road_name": "Lumding-Badarpur Line"},
        ]
        engine = RoutingEngine()
        policy = get_routing_policy(RouteType.MULTIMODAL)
        explanation = engine.generate_route_explanation(
            policy=policy,
            segments=segments,
            total_time_min=240.0,
            total_cost_inr=3200.0,
            hazard_score=0.04,
            modes_used=["ROAD", "RAIL", "TRANSFER"],
            transfer_count=1,
        )
        assert "multimodal" in explanation.lower()
        assert "transfer" in explanation.lower()


class MockNode:
    def __init__(self, node_id, name, lon=91.0, lat=26.0):
        self.id = node_id
        self.name = name
        self.geometry = type("Point", (), {"x": lon, "y": lat})()


class TestRoutingEngineDijkstraExecution:

    def setup_method(self):
        self.nA = MockNode("nA", "Guwahati")
        self.nB = MockNode("nB", "Silchar")
        self.nC = MockNode("nC", "Lumding")

        # Direct A -> B: 120 min, hazard 0.85, cost 3000 INR
        self.eAB = DummyEdge(
            edge_id="eAB",
            base_transit_time_min=120.0,
            cost_inr=3000.0,
            hazard_score=0.85,
            mode=TransportMode.ROAD,
        )
        self.eAB.source_node_id = self.nA.id
        self.eAB.source_node = self.nA
        self.eAB.target_node_id = self.nB.id
        self.eAB.target_node = self.nB
        self.eAB.distance_m = 180000.0

        # Detour A -> C: 60 min, hazard 0.05, cost 600 INR
        self.eAC = DummyEdge(
            edge_id="eAC",
            base_transit_time_min=60.0,
            cost_inr=600.0,
            hazard_score=0.05,
            mode=TransportMode.ROAD,
        )
        self.eAC.source_node_id = self.nA.id
        self.eAC.source_node = self.nA
        self.eAC.target_node_id = self.nC.id
        self.eAC.target_node = self.nC
        self.eAC.distance_m = 100000.0

        # Detour C -> B: 70 min, hazard 0.05, cost 700 INR
        self.eCB = DummyEdge(
            edge_id="eCB",
            base_transit_time_min=70.0,
            cost_inr=700.0,
            hazard_score=0.05,
            mode=TransportMode.ROAD,
        )
        self.eCB.source_node_id = self.nC.id
        self.eCB.source_node = self.nC
        self.eCB.target_node_id = self.nB.id
        self.eCB.target_node = self.nB
        self.eCB.distance_m = 110000.0

        self.edges_pool = [self.eAB, self.eAC, self.eCB]

    def test_fastest_policy_dijkstra(self):
        engine = RoutingEngine()
        policy = get_routing_policy(RouteType.FASTEST)
        route = engine.compute_single_route(
            origin=self.nA,
            destination=self.nB,
            policy=policy,
            edges_pool=self.edges_pool,
        )
        assert route is not None
        # FASTEST chooses direct A -> B (120 min vs 130 min detour)
        assert len(route["segments"]) == 1
        assert route["segments"][0]["edge_id"] == "eAB"

    def test_safest_policy_dijkstra(self):
        engine = RoutingEngine()
        policy = get_routing_policy(RouteType.SAFEST)
        route = engine.compute_single_route(
            origin=self.nA,
            destination=self.nB,
            policy=policy,
            edges_pool=self.edges_pool,
        )
        assert route is not None
        # SAFEST penalizes 0.85 hazard heavily and takes 2-segment low-hazard detour A -> C -> B
        assert len(route["segments"]) == 2
        assert route["segments"][0]["edge_id"] == "eAC"
        assert route["segments"][1]["edge_id"] == "eCB"

    def test_cheapest_policy_dijkstra(self):
        engine = RoutingEngine()
        policy = get_routing_policy(RouteType.CHEAPEST)
        route = engine.compute_single_route(
            origin=self.nA,
            destination=self.nB,
            policy=policy,
            edges_pool=self.edges_pool,
        )
        assert route is not None
        # A->B is 3000 INR vs A->C + C->B is 600 + 700 = 1300 INR
        assert len(route["segments"]) == 2
        assert route["total_cost_inr"] == 1300.0


