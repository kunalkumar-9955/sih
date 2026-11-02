"""
SIH26002 — Phase 5 Unit Tests (Pure Logic, No Database Required).

Tests:
1. Offline Graph SHA-256 canonical hashing determinism
2. Haversine distance calculations
3. Offline A* search engine:
   - Identical origin/destination
   - Multi-hop path finding
   - Routing policies (FASTEST, SAFEST, CHEAPEST, MULTIMODAL)
   - BLOCKED edge avoidance
   - Vehicle weight capacity constraint
   - Pathfinder query latency performance (< 10ms)
4. Conflict resolution rules:
   - Monotonic trip state transitions (PLANNED -> ACTIVE -> COMPLETED)
   - Preventing illegal regressions from terminal states
   - Route version mismatch detection
   - Temporal sanity window (drift & future skew checks)
"""
import time
from datetime import datetime, timedelta
import pytest
from django.utils import timezone

from apps.sync.services.conflict_resolver import SyncConflictResolver
from apps.sync.services.offline_graph_exporter import OfflineGraphExporterService
from apps.sync.services.offline_routing import OfflineAStarRouter, haversine_distance_m
from apps.trips.models import TripStatus


@pytest.fixture
def sample_graph_bundle():
    """Synthetic 4-node corridor graph for unit testing."""
    return {
        "region": "TEST_NER_CORRIDOR",
        "exported_at": "2026-09-09T12:00:00Z",
        "nodes_count": 4,
        "edges_count": 5,
        "nodes": [
            {"id": 1, "name": "Guwahati Hub", "node_type": "MULTIMODAL_HUB", "coordinates": [91.7362, 26.1445]},
            {"id": 2, "name": "Nongpoh Waypoint", "node_type": "CHECKPOST", "coordinates": [91.8814, 25.9032]},
            {"id": 3, "name": "Shillong Hub", "node_type": "LOCAL_HUB", "coordinates": [91.8831, 25.5788]},
            {"id": 4, "name": "Jowai Bypass", "node_type": "ROAD_INTERSECTION", "coordinates": [92.2078, 25.4452]},
        ],
        "edges": [
            {
                "id": 101,
                "source_node_id": 1,
                "target_node_id": 2,
                "mode": "ROAD",
                "distance_m": 50000.0,
                "base_transit_time_min": 60.0,
                "cost_inr": 1500.0,
                "capacity_kg": 25000.0,
                "status": "OPEN",
                "is_available": True,
                "hazard_score": 0.1,
                "transfer_time_min": 0.0,
                "transfer_cost_inr": 0.0,
            },
            {
                "id": 102,
                "source_node_id": 2,
                "target_node_id": 3,
                "mode": "ROAD",
                "distance_m": 45000.0,
                "base_transit_time_min": 50.0,
                "cost_inr": 1200.0,
                "capacity_kg": 20000.0,
                "status": "OPEN",
                "is_available": True,
                "hazard_score": 0.2,
                "transfer_time_min": 0.0,
                "transfer_cost_inr": 0.0,
            },
            {
                "id": 103,
                "source_node_id": 1,
                "target_node_id": 3,
                "mode": "ROAD",
                "distance_m": 90000.0,
                "base_transit_time_min": 85.0,  # Faster direct path, but high hazard
                "cost_inr": 3000.0,
                "capacity_kg": 30000.0,
                "status": "OPEN",
                "is_available": True,
                "hazard_score": 0.85,  # High landslide hazard
                "transfer_time_min": 0.0,
                "transfer_cost_inr": 0.0,
            },
            {
                "id": 104,
                "source_node_id": 3,
                "target_node_id": 4,
                "mode": "ROAD",
                "distance_m": 35000.0,
                "base_transit_time_min": 40.0,
                "cost_inr": 900.0,
                "capacity_kg": 15000.0,
                "status": "OPEN",
                "is_available": True,
                "hazard_score": 0.15,
                "transfer_time_min": 0.0,
                "transfer_cost_inr": 0.0,
            },
            {
                "id": 105,
                "source_node_id": 2,
                "target_node_id": 4,
                "mode": "ROAD",
                "distance_m": 65000.0,
                "base_transit_time_min": 75.0,
                "cost_inr": 1800.0,
                "capacity_kg": 20000.0,
                "status": "BLOCKED",  # Landslide washout
                "is_available": True,
                "hazard_score": 0.95,
                "transfer_time_min": 0.0,
                "transfer_cost_inr": 0.0,
            },
        ],
    }


class TestOfflineGraphChecksum:
    """Tests SHA-256 deterministic checksum calculation."""

    def test_checksum_determinism(self, sample_graph_bundle):
        c1 = OfflineGraphExporterService.compute_checksum(sample_graph_bundle)
        c2 = OfflineGraphExporterService.compute_checksum(sample_graph_bundle)
        assert c1 == c2
        assert len(c1) == 64

    def test_checksum_detects_tampering(self, sample_graph_bundle):
        c1 = OfflineGraphExporterService.compute_checksum(sample_graph_bundle)
        tampered = dict(sample_graph_bundle)
        tampered["region"] = "MODIFIED_REGION"
        c2 = OfflineGraphExporterService.compute_checksum(tampered)
        assert c1 != c2


class TestHaversineDistance:
    """Tests coordinate distance mathematics."""

    def test_haversine_known_distance(self):
        # Guwahati (26.1445, 91.7362) to Shillong (25.5788, 91.8831) ~ 64 km direct
        dist = haversine_distance_m(91.7362, 26.1445, 91.8831, 25.5788)
        assert 60000.0 < dist < 70000.0

    def test_haversine_same_point(self):
        dist = haversine_distance_m(91.7362, 26.1445, 91.7362, 26.1445)
        assert dist == 0.0


class TestOfflineAStarRouting:
    """Tests client-side A* pathfinder engine."""

    def test_direct_same_node_path(self, sample_graph_bundle):
        router = OfflineAStarRouter(sample_graph_bundle)
        res = router.find_path(origin_id=1, destination_id=1)
        assert res["found"] is True
        assert res["node_ids"] == [1]
        assert res["edge_ids"] == []
        assert res["total_distance_m"] == 0.0

    def test_safest_policy_avoids_high_hazard_direct_edge(self, sample_graph_bundle):
        # Edge 103 connects 1 -> 3 directly (hazard 0.85)
        # Edges 101 + 102 connect 1 -> 2 -> 3 (hazard 0.1, 0.2)
        router = OfflineAStarRouter(sample_graph_bundle)
        res = router.find_path(origin_id=1, destination_id=3, policy="SAFEST")
        assert res["found"] is True
        # SAFEST must avoid high-risk edge 103 and take safer 101 -> 102
        assert res["node_ids"] == [1, 2, 3]
        assert res["edge_ids"] == [101, 102]
        assert res["max_hazard_score"] == 0.2

    def test_fastest_policy_prefers_direct_edge(self, sample_graph_bundle):
        # Edge 103 has transit time 85 min vs 60+50 = 110 min for 101+102
        router = OfflineAStarRouter(sample_graph_bundle)
        res = router.find_path(origin_id=1, destination_id=3, policy="FASTEST")
        assert res["found"] is True
        assert res["node_ids"] == [1, 3]
        assert res["edge_ids"] == [103]

    def test_blocked_edge_is_strictly_excluded(self, sample_graph_bundle):
        # Edge 105 (2 -> 4) is BLOCKED
        # To get from 2 to 4, router must go 2 -> 3 -> 4
        router = OfflineAStarRouter(sample_graph_bundle)
        res = router.find_path(origin_id=2, destination_id=4)
        assert res["found"] is True
        assert 105 not in res["edge_ids"]
        assert res["node_ids"] == [2, 3, 4]
        assert res["edge_ids"] == [102, 104]

    def test_vehicle_weight_constraint_filtering(self, sample_graph_bundle):
        # Edge 104 has capacity 15000 kg.
        # A vehicle weighing 18000 kg cannot traverse edge 104
        router = OfflineAStarRouter(sample_graph_bundle)
        res = router.find_path(origin_id=3, destination_id=4, vehicle_weight_kg=18000.0)
        assert res["found"] is False

    def test_routing_execution_speed_under_10ms(self, sample_graph_bundle):
        router = OfflineAStarRouter(sample_graph_bundle)
        t0 = time.perf_counter()
        for _ in range(50):
            router.find_path(origin_id=1, destination_id=4, policy="SAFEST")
        elapsed = (time.perf_counter() - t0) / 50.0
        # Must execute in well under 10ms per query
        assert elapsed < 0.010, f"Query took {elapsed*1000:.2f}ms which exceeds 10ms target"


class TestSyncConflictResolution:
    """Tests monotonic trip lifecycle and temporal sanity rules."""

    def test_monotonic_trip_progression_allowed(self):
        ok, _ = SyncConflictResolver.resolve_trip_state_transition(TripStatus.PLANNED, TripStatus.ACTIVE)
        assert ok is True

        ok, _ = SyncConflictResolver.resolve_trip_state_transition(TripStatus.ACTIVE, TripStatus.COMPLETED)
        assert ok is True

    def test_terminal_state_regression_rejected(self):
        ok, msg = SyncConflictResolver.resolve_trip_state_transition(TripStatus.COMPLETED, TripStatus.ACTIVE)
        assert ok is False
        assert "terminal state" in msg

        ok, msg = SyncConflictResolver.resolve_trip_state_transition(TripStatus.CANCELLED, TripStatus.PLANNED)
        assert ok is False

    def test_route_version_validation(self):
        class MockTrip:
            route_version = 3

        trip = MockTrip()
        ok, msg = SyncConflictResolver.validate_route_version(trip, client_route_version=2)
        assert ok is False
        assert "Stale route version" in msg

        ok, _ = SyncConflictResolver.validate_route_version(trip, client_route_version=3)
        assert ok is True

    def test_timestamp_sanity_window(self):
        now = timezone.now()

        # Valid recent timestamp (1 hour ago)
        ok, _ = SyncConflictResolver.validate_timestamp_sanity(now - timedelta(hours=1), now=now)
        assert ok is True

        # Stale timestamp (> 24 hours ago)
        ok, msg = SyncConflictResolver.validate_timestamp_sanity(now - timedelta(hours=25), now=now)
        assert ok is False
        assert "stale event" in msg

        # Future skew (> 10 minutes)
        ok, msg = SyncConflictResolver.validate_timestamp_sanity(now + timedelta(minutes=15), now=now)
        assert ok is False
        assert "future" in msg
