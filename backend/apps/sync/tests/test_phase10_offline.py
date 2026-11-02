"""
SIH26002 — Phase 10 Offline-First Navigation & Sync Verification Tests.
"""
import uuid
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.sync.models import (
    EmergencySOS,
    OfflineGraphBundle,
    SyncEventStatus,
    SyncEventType,
    SyncQueueRecord,
)
from apps.sync.services.offline_routing import OfflineAStarRouter
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.trips.models import Trip, TripStatus
from apps.users.models import UserRole
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestPhase10OfflineLifecycle:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="offline_driver_p10@ner.gov.in",
            password="SecureDriverPass123!",
            role=UserRole.DRIVER,
        )
        self.driver = Driver.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

        self.node_origin = TransportNode.objects.create(
            name="Guwahati Offline Origin",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(91.73 26.18)",
            state="Assam",
            is_active=True,
        )
        self.node_dest = TransportNode.objects.create(
            name="Shillong Offline Dest",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.89 25.57)",
            state="Meghalaya",
            is_active=True,
        )
        self.edge = TransportEdge.objects.create(
            source_node=self.node_origin,
            target_node=self.node_dest,
            mode=TransportMode.ROAD,
            distance_m=98000.0,
            base_transit_time_min=140.0,
            status=EdgeStatus.OPEN,
            hazard_score=0.10,
            is_available=True,
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number="ML-01-OFF-1010",
            vehicle_type=VehicleType.MEDIUM_TRUCK,
            capacity_kg=5000.0,
            status=VehicleStatus.AVAILABLE,
        )
        self.trip = Trip.objects.create(
            driver=self.driver,
            vehicle=self.vehicle,
            origin_node=self.node_origin,
            destination_node=self.node_dest,
            status=TripStatus.PLANNED,
        )

    def test_offline_bundle_export_and_version(self):
        """Step 1: Download/cache graph bundle metadata."""
        bundle, _ = OfflineGraphBundle.objects.update_or_create(
            version="v1.0-ner-demo",
            defaults={
                "corridor_name": "NER_GLOBAL",
                "checksum_sha256": "abcdef1234567890",
                "node_count": 2,
                "edge_count": 1,
                "payload": {"nodes": [], "edges": []},
                "is_active": True,
            }
        )
        res = self.client.get("/api/v1/sync/graph/version/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "version" in data
        assert "checksum_sha256" in data

    def test_offline_local_routing_with_astar(self):
        """Step 4-5: Client generates offline local route using local cache without server."""
        graph_data = {
            "nodes": [
                {"id": 1, "name": "Guwahati", "coordinates": [91.73, 26.18]},
                {"id": 2, "name": "Shillong", "coordinates": [91.89, 25.57]},
            ],
            "edges": [
                {
                    "id": 101,
                    "source_node_id": 1,
                    "target_node_id": 2,
                    "mode": "ROAD",
                    "distance_m": 98000.0,
                    "base_transit_time_min": 140.0,
                    "cost_inr": 2500.0,
                    "capacity_kg": 20000.0,
                    "status": "OPEN",
                    "is_available": True,
                    "hazard_score": 0.10,
                    "transfer_time_min": 0.0,
                    "transfer_cost_inr": 0.0,
                }
            ],
        }
        router = OfflineAStarRouter(graph_data)
        route_res = router.find_path(
            origin_id=1,
            destination_id=2,
            policy="FASTEST",
        )
        assert route_res["found"] is True
        assert route_res["node_ids"] == [1, 2]
        assert route_res["total_distance_m"] == 98000.0

    def test_batch_sync_event_submission_and_idempotency(self):
        """Step 6-10: Queue sync events, submit batch, verify duplicate idempotency."""
        event_id = str(uuid.uuid4())
        payload = {
            "events": [
                {
                    "idempotency_key": event_id,
                    "event_type": SyncEventType.TRIP_STATUS,
                    "client_timestamp": timezone.now().isoformat(),
                    "payload": {
                        "trip_id": str(self.trip.id),
                        "status": TripStatus.ACTIVE,
                    },
                }
            ]
        }

        # First sync
        res1 = self.client.post("/api/v1/sync/events/batch/", payload, format="json")
        assert res1.status_code == status.HTTP_200_OK
        data1 = res1.json()
        assert data1.get("total_events") == 1
        assert data1.get("applied_count") == 1
        assert data1.get("duplicate_count") == 0

        # Duplicate sync with same idempotency_key (idempotency verification)
        res2 = self.client.post("/api/v1/sync/events/batch/", payload, format="json")
        assert res2.status_code == status.HTTP_200_OK
        data2 = res2.json()
        assert data2.get("duplicate_count") == 1
        assert data2.get("applied_count") == 0

        # Verify final trip state updated cleanly to ACTIVE
        self.trip.refresh_from_db()
        assert self.trip.status == TripStatus.ACTIVE
