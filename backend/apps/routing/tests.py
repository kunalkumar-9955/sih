"""
SIH26002 — Routing engine unit and API tests: policies, constraints, engine, explanations, APIs.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from rest_framework import status
from rest_framework.test import APIClient

from apps.routing.constraints import ConstraintChecker, VehicleContext
from apps.routing.engine import RoutingEngine
from apps.routing.hazard_provider import MockHazardProvider
from apps.routing.models import RouteType
from apps.routing.policies import CheapestPolicy, FastestPolicy, MultimodalPolicy, SafestPolicy
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestRoutingEngine:

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="driver@test.com", password="Password123!", role=UserRole.DRIVER
        )
        self.client.force_authenticate(user=self.user)

        # Triangle network: Node A -> Node B (direct, high hazard, expensive)
        # Node A -> Node C -> Node B (longer, low hazard, cheap)
        self.nA = TransportNode.objects.create(name="A", geometry=Point(91.0, 26.0, srid=4326), node_type=NodeType.LOCAL_HUB)
        self.nB = TransportNode.objects.create(name="B", geometry=Point(92.0, 26.0, srid=4326), node_type=NodeType.LOCAL_HUB)
        self.nC = TransportNode.objects.create(name="C", geometry=Point(91.5, 26.5, srid=4326), node_type=NodeType.LOCAL_HUB)

        # Direct edge A->B: 60 min, hazard 0.9 (landslide zone), cost 2000, max payload 10 tons
        self.eAB = TransportEdge.objects.create(
            source_node=self.nA,
            target_node=self.nB,
            mode=TransportMode.ROAD,
            distance_m=50000.0,
            base_transit_time_min=60.0,
            cost_inr=2000.0,
            hazard_score=0.9,
            capacity_kg=10000.0,
            geometry=LineString([self.nA.geometry, self.nB.geometry], srid=4326),
        )

        # Detour edge A->C: 45 min, hazard 0.05, cost 500, max payload 25 tons
        self.eAC = TransportEdge.objects.create(
            source_node=self.nA,
            target_node=self.nC,
            mode=TransportMode.ROAD,
            distance_m=40000.0,
            base_transit_time_min=45.0,
            cost_inr=500.0,
            hazard_score=0.05,
            capacity_kg=25000.0,
            geometry=LineString([self.nA.geometry, self.nC.geometry], srid=4326),
        )

        # Detour edge C->B: 45 min, hazard 0.05, cost 500, max payload 25 tons
        self.eCB = TransportEdge.objects.create(
            source_node=self.nC,
            target_node=self.nB,
            mode=TransportMode.ROAD,
            distance_m=40000.0,
            base_transit_time_min=45.0,
            cost_inr=500.0,
            hazard_score=0.05,
            capacity_kg=25000.0,
            geometry=LineString([self.nC.geometry, self.nB.geometry], srid=4326),
        )

    def test_fastest_vs_safest_routing(self):
        engine = RoutingEngine(alpha=2.5)

        # FASTEST prefers A -> B (60 min vs 90 min)
        fastest = engine.compute_single_route(self.nA, self.nB, route_type=RouteType.FASTEST)
        assert fastest is not None
        assert len(fastest["segments"]) == 1
        assert fastest["segments"][0]["target_name"] == "B"

        # SAFEST penalizes hazard heavily and prefers A -> C -> B (avoiding 0.9 hazard)
        safest = engine.compute_single_route(self.nA, self.nB, route_type=RouteType.SAFEST)
        assert safest is not None
        assert len(safest["segments"]) == 2
        assert safest["segments"][0]["target_name"] == "C"
        assert safest["segments"][1]["target_name"] == "B"

    def test_cheapest_routing(self):
        # A->B costs 2000 INR. A->C + C->B costs 500 + 500 = 1000 INR.
        engine = RoutingEngine()
        cheapest = engine.compute_single_route(self.nA, self.nB, route_type=RouteType.CHEAPEST)
        assert cheapest is not None
        assert len(cheapest["segments"]) == 2
        assert cheapest["total_cost_inr"] == 1000.0

    def test_blocked_edge_exclusion(self):
        # Block A->B completely
        self.eAB.status = EdgeStatus.BLOCKED
        self.eAB.is_available = False
        self.eAB.save()

        engine = RoutingEngine()
        route = engine.compute_single_route(self.nA, self.nB, route_type=RouteType.FASTEST)
        # Must take detour since direct edge is blocked
        assert route is not None
        assert len(route["segments"]) == 2

    def test_vehicle_payload_constraint(self):
        checker = ConstraintChecker()
        # Heavy cargo (20 tons) cannot use eAB (max 10 tons)
        heavy_context = VehicleContext(cargo_weight_tons=20.0)
        assert checker.is_edge_traversable(self.eAB, heavy_context) is False
        assert checker.is_edge_traversable(self.eAC, heavy_context) is True

        # Routing engine with heavy cargo will avoid A->B even on FASTEST
        engine = RoutingEngine(vehicle_context=heavy_context)
        route = engine.compute_single_route(self.nA, self.nB, route_type=RouteType.FASTEST)
        assert route is not None
        assert len(route["segments"]) == 2

    def test_waterway_depth_constraint(self):
        # Create a water edge
        water_edge = TransportEdge.objects.create(
            source_node=self.nA,
            target_node=self.nC,
            mode=TransportMode.WATER,
            distance_m=35000.0,
            base_transit_time_min=120.0,
            cost_inr=300.0,
            water_level_m=1.8,
            min_required_depth_m=2.0,
            draft_requirement_m=2.5,
            geometry=LineString([self.nA.geometry, self.nC.geometry], srid=4326),
        )
        checker = ConstraintChecker()
        # Vessel requiring 2.2m draft cannot navigate 1.8m water level
        vessel_ctx = VehicleContext(draft_m=2.2)
        assert checker.is_edge_traversable(water_edge, vessel_ctx) is False

        # Vessel with shallow 1.2m draft can navigate if depth is sufficient
        water_edge.water_level_m = 2.5
        water_edge.save()
        shallow_ctx = VehicleContext(draft_m=1.2)
        assert checker.is_edge_traversable(water_edge, shallow_ctx) is True
        water_edge.delete()

    def test_mock_hazard_provider_override(self):
        mock_provider = MockHazardProvider(default_score=0.99)
        engine = RoutingEngine(hazard_provider=mock_provider)
        cost = engine.policy_map[RouteType.SAFEST].calculate_edge_cost(self.eAC, None, hazard_provider=mock_provider)
        assert cost > 500.0

    def test_route_plan_api(self):
        payload = {
            "origin_node_id": str(self.nA.id),
            "destination_node_id": str(self.nB.id),
            "routing_policy": "SAFEST",
            "cargo_weight_tons": 5.0,
            "allow_multimodal": True,
        }
        res = self.client.post("/api/v1/routes/plan/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert "routes" in res.data
        assert len(res.data["routes"]) >= 1
        first = res.data["routes"][0]
        assert "explanation" in first
        assert "modes_used" in first
        assert "transfer_count" in first
        assert "risk_score" in first

    def test_legacy_route_compute_api(self):
        payload = {
            "origin_node_id": str(self.nA.id),
            "destination_node_id": str(self.nB.id),
            "route_types": ["SAFEST", "FASTEST"],
        }
        res = self.client.post("/api/v1/routes/compute/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.data, list)
        assert len(res.data) >= 1

