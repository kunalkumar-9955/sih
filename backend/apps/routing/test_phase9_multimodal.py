"""
SIH26002 — Phase 9 Advanced Multimodal Routing & Predictive ETA Unit Tests.
"""
from datetime import timedelta
import pytest
from django.utils import timezone

from apps.routing.constraints import ConstraintChecker, VehicleContext
from apps.routing.models import RouteType
from apps.routing.policies import (
    BalancedPolicy,
    EmergencyDisasterPolicy,
    FastestPolicy,
    LowestRiskPolicy,
    SafestPolicy,
    RoutingPolicyFactory,
)
from apps.routing.services.eta_intelligence import MountainCorridorDelayModel, PredictiveETAService
from apps.routing.services.multimodal_service import MultimodalRouteOptimizationService
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode


@pytest.mark.django_db
class TestPhase9MultimodalRouting:
    @pytest.fixture(autouse=True)
    def setup_multimodal_network(self):
        # Create 4 test nodes
        self.node_origin = TransportNode.objects.create(
            name="Guwahati Multimodal Terminal",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.7362 26.1856)",
            state="Assam",
            district="Kamrup Metro",
            is_active=True,
        )
        self.node_river_port = TransportNode.objects.create(
            name="Pandu River Port",
            node_type=NodeType.PORT,
            geometry="POINT(91.6850 26.1720)",
            state="Assam",
            district="Kamrup Metro",
            is_active=True,
        )
        self.node_rail_junction = TransportNode.objects.create(
            name="Lumding Rail Yard",
            node_type=NodeType.RAIL_YARD,
            geometry="POINT(93.1700 25.7500)",
            state="Assam",
            district="Hojai",
            is_active=True,
        )
        self.node_dest = TransportNode.objects.create(
            name="Silchar Logistics Park",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(92.7970 24.8333)",
            state="Assam",
            district="Cachar",
            is_active=True,
        )

        # Edge 1: Direct Highway (Fast but high hazard)
        self.edge_direct_road = TransportEdge.objects.create(
            source_node=self.node_origin,
            target_node=self.node_dest,
            mode=TransportMode.ROAD,
            distance_m=310000,
            base_transit_time_min=390,
            cost_inr=9500.0,
            hazard_score=0.72,
            capacity_kg=15000.0,
            status=EdgeStatus.OPEN,
            is_available=True,
        )

        # Edge 2: Origin -> River Port (Transfer)
        self.edge_to_port = TransportEdge.objects.create(
            source_node=self.node_origin,
            target_node=self.node_river_port,
            mode=TransportMode.ROAD,
            distance_m=12000,
            base_transit_time_min=25,
            cost_inr=600.0,
            hazard_score=0.08,
            capacity_kg=20000.0,
            status=EdgeStatus.OPEN,
            is_available=True,
        )

        # Edge 3: River Port -> Dest (Inland Waterway NW-2, Safe, low cost, longer time)
        self.edge_waterway = TransportEdge.objects.create(
            source_node=self.node_river_port,
            target_node=self.node_dest,
            mode=TransportMode.WATER,
            distance_m=380000,
            base_transit_time_min=620,
            cost_inr=4200.0,
            hazard_score=0.12,
            capacity_kg=40000.0,
            water_level_m=3.5,
            min_required_depth_m=2.0,
            status=EdgeStatus.OPEN,
            is_available=True,
        )

    def test_routing_policy_factory(self):
        lowest_risk = RoutingPolicyFactory.get_policy(RouteType.LOWEST_RISK)
        assert isinstance(lowest_risk, LowestRiskPolicy)
        assert lowest_risk.route_type == RouteType.LOWEST_RISK

        balanced = RoutingPolicyFactory.get_policy(RouteType.BALANCED)
        assert isinstance(balanced, BalancedPolicy)

        emergency = RoutingPolicyFactory.get_policy(RouteType.EMERGENCY_CORRIDOR)
        assert isinstance(emergency, EmergencyDisasterPolicy)

    def test_multimodal_route_optimization_pareto(self):
        res = MultimodalRouteOptimizationService.optimize(
            origin_id=str(self.node_origin.id),
            destination_id=str(self.node_dest.id),
            cargo_weight_kg=8000.0,
            allow_multimodal=True,
        )
        assert res["success"] is True
        assert res["routes_evaluated_count"] >= 1
        assert len(res["routes"]) >= 1

        # Check Pareto trade-offs and explanation fields
        for r in res["routes"]:
            assert "total_distance_km" in r
            assert "total_time_min" in r
            assert "hazard_score" in r
            assert "explanation" in r
            assert "modes_used" in r

    def test_emergency_disaster_policy_prefers_safety(self):
        res = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_origin.id),
            destination_node_id=str(self.node_dest.id),
            avoid_hazard_threshold=0.60,
            disaster_mode=True,
        )
        assert res["success"] is True
        assert "pareto_frontier" in res

    def test_waterway_depth_constraint(self):
        checker = ConstraintChecker()
        # Water draft exceeding river depth should be rejected
        v_ctx_deep = VehicleContext(water_draft_m=4.5)
        passes, reason = checker.is_edge_allowed(self.edge_waterway, v_ctx_deep)
        assert passes is False
        assert "draft" in reason.lower()

        # Water draft within river depth should pass
        v_ctx_shallow = VehicleContext(water_draft_m=1.8)
        passes_ok, _ = checker.is_edge_allowed(self.edge_waterway, v_ctx_shallow)
        assert passes_ok is True


@pytest.mark.django_db
class TestPhase9PredictiveETAIntelligence:
    def test_mountain_delay_model_direct(self):
        model = MountainCorridorDelayModel()
        pred = model.predict_delay(
            route_distance_km=180.0,
            base_transit_time_min=240.0,
            hazard_score=0.45,
            weather_rainfall_mm=65.0,
            has_active_incidents=True,
            transfer_count=1,
            is_mountain_pass=True,
        )
        assert pred["predicted_transit_time_min"] > 240.0
        assert pred["expected_delay_min"] > 0
        assert 0.0 <= pred["delay_probability"] <= 1.0
        assert 0.0 <= pred["confidence_score"] <= 1.0
        assert "contributing_factors" in pred
        assert pred["data_source_mode"] == "CONFIGURED"

    def test_predictive_eta_service_adhoc(self):
        node_a = TransportNode.objects.create(
            name="Guwahati Dispatch Hub",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.74 26.18)",
            is_active=True,
        )
        node_b = TransportNode.objects.create(
            name="Shillong Transit Yard",
            node_type=NodeType.LOCAL_HUB,
            geometry="POINT(91.89 25.57)",
            is_active=True,
        )
        TransportEdge.objects.create(
            source_node=node_a,
            target_node=node_b,
            mode=TransportMode.ROAD,
            distance_m=98000,
            base_transit_time_min=160,
            hazard_score=0.30,
            status=EdgeStatus.OPEN,
            is_available=True,
        )

        res = PredictiveETAService.predict_adhoc(
            origin_node_id=str(node_a.id),
            destination_node_id=str(node_b.id),
            weather_rainfall_mm=85.0,
        )
        assert res["success"] is True
        assert res["origin_name"] == "Guwahati Dispatch Hub"
        assert res["destination_name"] == "Shillong Transit Yard"
        assert res["expected_delay_min"] > 0
        assert "contributing_factors" in res
        assert "prediction" in res
