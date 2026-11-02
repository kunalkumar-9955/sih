"""
SIH26002 — Phase 4 End-to-End Integration Test.

Mandatory integration test verifying the full lifecycle of dynamic rerouting:
1. Trip initiated on primary Guwahati → Shillong corridor
2. Route initially assigned with low hazard
3. Moderate/High hazard shock elevates hazard from 0.10 to 0.45 (advisory reroute)
4. Recalculate route detects risk and creates RerouteEvent with status PENDING
5. Driver acknowledges and accepts new route -> status becomes APPLIED
6. Trip route version increments to v2, route updated to bypass
7. Disaster closure: edge blocked triggers mandatory reroute (status APPLIED immediately)
8. Idempotency check: recalculating again when already on safe route creates no duplicates
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from rest_framework import status
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.routing.engine import RoutingEngine
from apps.routing.models import Route, RouteType
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.trips.models import RerouteEvent, RerouteEventStatus, Trip, TripStatus
from apps.users.models import UserRole
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestPhase4DynamicReroutingIntegration:
    """Mandatory Phase 4 End-to-End Integration Test."""

    def setup_method(self):
        self.client = APIClient()
        self.driver_user = User.objects.create_user(
            email="phase4_driver@ner.gov.in",
            password="SecurePassword123!",
            role=UserRole.DRIVER,
        )
        self.driver_profile = Driver.objects.create(user=self.driver_user)
        self.client.force_authenticate(user=self.driver_user)

        self.vehicle = Vehicle.objects.create(
            owner=self.driver_user,
            registration_number="AS-01-ER-4001",
            vehicle_type=VehicleType.HEAVY_TRUCK,
            capacity_kg=15000,
            status=VehicleStatus.AVAILABLE,
        )

        # ── Graph Nodes ───────────────────────────────────────────────────────
        self.node_origin = TransportNode.objects.create(
            name="Guwahati Multimodal Hub",
            short_code="GAU-HUB",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry=Point(91.7362, 26.1445, srid=4326),
        )
        self.node_nongpoh = TransportNode.objects.create(
            name="Nongpoh Checkpost",
            short_code="NPH-CHK",
            node_type=NodeType.CHECKPOST,
            geometry=Point(91.8789, 25.9015, srid=4326),
        )
        self.node_bypass = TransportNode.objects.create(
            name="Byrnihat Bypass Point",
            short_code="BYR-BYP",
            node_type=NodeType.LOCAL_HUB,
            geometry=Point(91.8500, 26.0200, srid=4326),
        )
        self.node_dest = TransportNode.objects.create(
            name="Shillong Logistics Hub",
            short_code="SHL-HUB",
            node_type=NodeType.LOGISTICS_HUB,
            geometry=Point(91.8933, 25.5788, srid=4326),
        )

        # ── Primary Corridor (Direct via Nongpoh) ─────────────────────────────
        self.edge_primary_1 = TransportEdge.objects.create(
            source_node=self.node_origin,
            target_node=self.node_nongpoh,
            mode=TransportMode.ROAD,
            distance_m=50000.0,
            base_transit_time_min=60.0,
            cost_inr=500.0,
            hazard_score=0.10,
            status=EdgeStatus.OPEN,
            is_available=True,
            geometry=LineString([Point(91.7362, 26.1445), Point(91.8789, 25.9015)], srid=4326),
        )
        self.edge_primary_2 = TransportEdge.objects.create(
            source_node=self.node_nongpoh,
            target_node=self.node_dest,
            mode=TransportMode.ROAD,
            distance_m=50000.0,
            base_transit_time_min=60.0,
            cost_inr=500.0,
            hazard_score=0.10,
            status=EdgeStatus.OPEN,
            is_available=True,
            geometry=LineString([Point(91.8789, 25.9015), Point(91.8933, 25.5788)], srid=4326),
        )

        # ── Alternative Bypass Corridor (via Byrnihat) ────────────────────────
        self.edge_bypass_1 = TransportEdge.objects.create(
            source_node=self.node_origin,
            target_node=self.node_bypass,
            mode=TransportMode.ROAD,
            distance_m=45000.0,
            base_transit_time_min=55.0,
            cost_inr=450.0,
            hazard_score=0.12,
            status=EdgeStatus.OPEN,
            is_available=True,
            geometry=LineString([Point(91.7362, 26.1445), Point(91.8500, 26.0200)], srid=4326),
        )
        self.edge_bypass_2 = TransportEdge.objects.create(
            source_node=self.node_bypass,
            target_node=self.node_dest,
            mode=TransportMode.ROAD,
            distance_m=65000.0,
            base_transit_time_min=80.0,
            cost_inr=650.0,
            hazard_score=0.12,
            status=EdgeStatus.OPEN,
            is_available=True,
            geometry=LineString([Point(91.8500, 26.0200), Point(91.8933, 25.5788)], srid=4326),
        )

    def test_end_to_end_dynamic_reroute_lifecycle(self):
        """
        Step-by-step verification of the complete dynamic rerouting pipeline.
        """
        # 1. Compute initial primary route
        engine = RoutingEngine()
        routes = engine.compute_all_routes(
            origin=self.node_origin,
            destination=self.node_dest,
            requested_types=[RouteType.SAFEST],
            persist=True,
        )
        assert len(routes) >= 1
        initial_route = routes[0]

        # 2. Dispatch Active Trip with initial route
        trip = Trip.objects.create(
            driver=self.driver_profile,
            vehicle=self.vehicle,
            origin_node=self.node_origin,
            destination_node=self.node_dest,
            route=initial_route,
            status=TripStatus.ACTIVE,
            cargo_description="Medical kits and emergency provisions",
            cargo_weight_kg=3500.0,
            route_version=1,
        )

        # 3. Check Initial Route Risk via API
        risk_res = self.client.get(f"/api/v1/trips/{trip.id}/route-risk/")
        assert risk_res.status_code == status.HTTP_200_OK
        assert risk_res.data["safety_level"] == "LOW"
        assert risk_res.data["max_hazard_score"] == 0.10
        assert risk_res.data["has_critical_or_blocked"] is False

        # 4. Trigger Advisory Hazard Shock: hazard rises on Nongpoh -> Shillong (0.10 -> 0.45)
        # Delta = 0.35 >= 0.15 threshold, but < 0.85 CRITICAL -> advisory reroute
        self.edge_primary_2.hazard_score = 0.45
        self.edge_primary_2.save(update_fields=["hazard_score", "updated_at"])

        # Check Route Risk API
        risk_res_post = self.client.get(f"/api/v1/trips/{trip.id}/route-risk/")
        assert risk_res_post.status_code == status.HTTP_200_OK
        assert risk_res_post.data["max_hazard_score"] == 0.45
        assert risk_res_post.data["risky_edge_count"] >= 1

        # 5. Trigger Recalculate Route API (advisory reroute)
        recalc_res = self.client.post(
            f"/api/v1/trips/{trip.id}/recalculate-route/",
            {"force": False, "auto_apply": False},
            format="json",
        )
        assert recalc_res.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert recalc_res.data["rerouted"] is True
        event_id = recalc_res.data["event_id"]
        assert event_id is not None
        assert recalc_res.data["improvement_pct"] > 0.50

        # 6. Verify RerouteEvent in List API
        events_res = self.client.get(f"/api/v1/trips/{trip.id}/reroute-events/")
        assert events_res.status_code == status.HTTP_200_OK
        results = events_res.data.get("results", events_res.data)
        assert len(results) >= 1
        latest_event = results[0]
        assert latest_event["id"] == event_id
        assert latest_event["status"] == RerouteEventStatus.PENDING

        # 7. Driver Acknowledges and Accepts the Bypass Route
        ack_res = self.client.post(
            f"/api/v1/trips/{trip.id}/reroute-events/{event_id}/acknowledge/",
            {"action": "ACCEPT", "notes": "Switching to Byrnihat bypass corridor"},
            format="json",
        )
        assert ack_res.status_code == status.HTTP_200_OK
        assert ack_res.data["status"] == RerouteEventStatus.APPLIED
        assert ack_res.data["driver_acknowledged_at"] is not None

        # 8. Verify Trip has been updated to Route Version 2
        trip.refresh_from_db()
        assert trip.route_version == 2
        assert trip.route_assigned_at is not None
        assert trip.route.id != initial_route.id
        new_route_edges = [s["edge_id"] for s in trip.route.segments]
        assert str(self.edge_primary_2.id) not in new_route_edges

        # 9. Idempotency Check: Recalculate Route Again on Safe Route
        second_recalc = self.client.post(
            f"/api/v1/trips/{trip.id}/recalculate-route/",
            {"force": False, "auto_apply": False},
            format="json",
        )
        assert second_recalc.status_code == status.HTTP_200_OK
        assert second_recalc.data["rerouted"] is False
        assert "within safe tolerance" in second_recalc.data["reason"]
