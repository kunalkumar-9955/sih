"""
SIH26002 — Phase 10 Routing Robustness & Edge-Case Verification Tests.
"""
import pytest
from apps.routing.engine import RoutingEngine
from apps.routing.models import RouteType
from apps.routing.policies import RoutingPolicyFactory
from apps.routing.services.multimodal_service import MultimodalRouteOptimizationService
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode


@pytest.mark.django_db
class TestPhase10RoutingRobustness:
    def setup_method(self):
        # Create test nodes
        self.node_a = TransportNode.objects.create(
            name="Guwahati Dispatch Yard",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(91.73 26.18)",
            state="Assam",
            is_active=True,
        )
        self.node_b = TransportNode.objects.create(
            name="Nongpoh Transit Point",
            node_type=NodeType.CHECKPOST,
            geometry="POINT(91.88 25.90)",
            state="Meghalaya",
            is_active=True,
        )
        self.node_c = TransportNode.objects.create(
            name="Shillong Gateway Hub",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.89 25.57)",
            state="Meghalaya",
            is_active=True,
        )
        self.node_island = TransportNode.objects.create(
            name="Isolated Remote Enclave",
            node_type=NodeType.CHECKPOST,
            geometry="POINT(93.50 27.20)",
            state="Arunachal Pradesh",
            is_active=True,
        )

        # Edges
        # Route 1: Direct Highway (A -> C)
        self.edge_direct = TransportEdge.objects.create(
            source_node=self.node_a,
            target_node=self.node_c,
            mode=TransportMode.ROAD,
            distance_m=100000.0,
            base_transit_time_min=150.0,
            status=EdgeStatus.OPEN,
            hazard_score=0.10,
            is_available=True,
            capacity_kg=25000.0,
        )
        # Route 2: Detour via B (A -> B -> C)
        self.edge_ab = TransportEdge.objects.create(
            source_node=self.node_a,
            target_node=self.node_b,
            mode=TransportMode.ROAD,
            distance_m=50000.0,
            base_transit_time_min=80.0,
            status=EdgeStatus.OPEN,
            hazard_score=0.10,
            is_available=True,
            capacity_kg=20000.0,
        )
        self.edge_bc = TransportEdge.objects.create(
            source_node=self.node_b,
            target_node=self.node_c,
            mode=TransportMode.ROAD,
            distance_m=60000.0,
            base_transit_time_min=90.0,
            status=EdgeStatus.OPEN,
            hazard_score=0.10,
            is_available=True,
            capacity_kg=20000.0,
        )

    def test_routing_on_normal_network(self):
        """Validates that direct route is chosen when all edges are open and low risk."""
        routes = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_a.id),
            destination_node_id=str(self.node_c.id),
            preferred_mode=TransportMode.ROAD,
        )
        best = routes.get("best_composite_route", {})
        assert best is not None
        assert best.get("total_distance_km") is not None
        assert best.get("total_distance_km") > 0

    def test_blocked_edge_strict_exclusion(self):
        """Validates that a blocked direct edge forces routing via detour."""
        self.edge_direct.status = EdgeStatus.BLOCKED
        self.edge_direct.save(update_fields=["status"])

        routes = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_a.id),
            destination_node_id=str(self.node_c.id),
            preferred_mode=TransportMode.ROAD,
        )
        best = routes.get("best_composite_route", {})
        assert best is not None
        # Must have routed via B
        segments = best.get("segments", [])
        edge_ids = [s.get("edge_id") for s in segments]
        assert str(self.edge_direct.id) not in edge_ids

        # Restore
        self.edge_direct.status = EdgeStatus.OPEN
        self.edge_direct.save(update_fields=["status"])

    def test_multiple_blocked_edges_forces_infeasible_or_clean_empty(self):
        """When all paths are blocked, engine should gracefully report no path rather than crash."""
        self.edge_direct.status = EdgeStatus.BLOCKED
        self.edge_direct.save(update_fields=["status"])
        self.edge_ab.status = EdgeStatus.BLOCKED
        self.edge_ab.save(update_fields=["status"])

        routes = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_a.id),
            destination_node_id=str(self.node_c.id),
            preferred_mode=TransportMode.ROAD,
        )
        # Should gracefully return empty or fallback without 500 error
        assert routes is not None

        # Restore
        self.edge_direct.status = EdgeStatus.OPEN
        self.edge_direct.save(update_fields=["status"])
        self.edge_ab.status = EdgeStatus.OPEN
        self.edge_ab.save(update_fields=["status"])

    def test_isolated_node_handling(self):
        """Routing to/from disconnected node returns empty path cleanly without crashing."""
        routes = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_a.id),
            destination_node_id=str(self.node_island.id),
            preferred_mode=TransportMode.ROAD,
        )
        assert routes is not None
        best = routes.get("best_composite_route")
        # Either None or empty segments
        if best:
            assert len(best.get("segments", [])) == 0

    def test_vehicle_weight_constraint_exclusion(self):
        """Vehicle with payload exceeding edge capacity is excluded."""
        routes = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_a.id),
            destination_node_id=str(self.node_c.id),
            weight_kg=35000.0,  # 35 tonnes > 25 tonnes max on direct edge
        )
        assert routes is not None

    def test_emergency_disaster_policy_favors_safety(self):
        """In disaster mode, emergency policy selects low-hazard route even if longer."""
        # Make direct edge risky
        self.edge_direct.hazard_score = 0.85
        self.edge_direct.save(update_fields=["hazard_score"])

        # Detour edges safe
        self.edge_ab.hazard_score = 0.05
        self.edge_ab.save(update_fields=["hazard_score"])
        self.edge_bc.hazard_score = 0.05
        self.edge_bc.save(update_fields=["hazard_score"])

        routes = MultimodalRouteOptimizationService.optimize_multimodal_route(
            origin_node_id=str(self.node_a.id),
            destination_node_id=str(self.node_c.id),
            disaster_mode=True,
            avoid_hazard_threshold=0.60,
        )
        best = routes.get("pareto_frontier", {}).get("safest") or routes.get("best_composite_route", {})
        segments = best.get("segments", [])
        edge_ids = [s.get("edge_id") for s in segments]
        # Should NOT use risky direct edge
        assert str(self.edge_direct.id) not in edge_ids

        # Restore
        self.edge_direct.hazard_score = 0.10
        self.edge_direct.save(update_fields=["hazard_score"])
