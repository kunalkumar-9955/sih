"""
SIH26002 — Phase 5 End-to-End Integration Tests.

Validates:
1. Offline graph bundle export, checksum generation, and version/download REST endpoints
2. Batch sync event submission (telemetry, hazard incident creation, trip status transitions)
3. Strict idempotency preventing duplicate event processing
4. Conflict resolution rejecting illegal trip regressions from terminal states
5. Emergency SOS distress beacon registration and sync diagnostics monitoring
"""
import uuid
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.hazards.models import HazardIncident
from apps.sync.models import (
    EmergencySOS,
    EmergencySOSStatus,
    OfflineGraphBundle,
    SyncEventStatus,
    SyncEventType,
    SyncQueueRecord,
)
from apps.sync.services.offline_graph_exporter import OfflineGraphExporterService
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.trips.models import Trip, TripStatus
from apps.users.models import UserRole
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestPhase5OfflineSyncIntegration:
    """End-to-end integration test suite for Phase 5."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="phase5_tester@ner.gov.in",
            password="SecureTestPassword123!",
            role=UserRole.DRIVER,
        )
        self.driver = Driver.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number="AS-01-SYNC-5001",
            vehicle_type=VehicleType.HEAVY_TRUCK,
            capacity_kg=18000,
            status=VehicleStatus.AVAILABLE,
        )

        # Create nodes
        self.node_a = TransportNode.objects.create(
            name="Guwahati Dispatch Hub",
            short_code="GAU-SYNC",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry=Point(91.7362, 26.1445, srid=4326),
            is_active=True,
        )
        self.node_b = TransportNode.objects.create(
            name="Shillong Receiving Depot",
            short_code="SHL-SYNC",
            node_type=NodeType.LOCAL_HUB,
            geometry=Point(91.8831, 25.5788, srid=4326),
            is_active=True,
        )

        # Create edge
        self.edge = TransportEdge.objects.create(
            source_node=self.node_a,
            target_node=self.node_b,
            mode=TransportMode.ROAD,
            distance_m=95000.0,
            base_transit_time_min=110.0,
            cost_inr=2400.0,
            capacity_kg=22000.0,
            status=EdgeStatus.OPEN,
            is_available=True,
            hazard_score=0.15,
            geometry=LineString([Point(91.7362, 26.1445), Point(91.8831, 25.5788)], srid=4326),
        )

        # Create Trip
        self.trip = Trip.objects.create(
            driver=self.driver,
            vehicle=self.vehicle,
            origin_node=self.node_a,
            destination_node=self.node_b,
            status=TripStatus.PLANNED,
            route_version=1,
        )

    def test_offline_graph_export_and_download_api(self):
        # 1. Export bundle
        exporter = OfflineGraphExporterService(region="NER_CORRIDOR")
        bundle = exporter.export_and_save(version_tag="NER-V1-TEST")

        assert bundle.node_count >= 2
        assert bundle.edge_count >= 1
        assert len(bundle.checksum_sha256) == 64

        # 2. Test Version API
        v_res = self.client.get("/api/v1/sync/graph/version/?region=NER_CORRIDOR")
        assert v_res.status_code == status.HTTP_200_OK
        v_data = v_res.json()
        assert v_data["version_tag"] == "NER-V1-TEST"
        assert v_data["checksum_sha256"] == bundle.checksum_sha256

        # 3. Test Download API
        d_res = self.client.get("/api/v1/sync/graph/download/?region=NER_CORRIDOR")
        assert d_res.status_code == status.HTTP_200_OK
        assert d_res.headers["X-Graph-Version"] == "NER-V1-TEST"
        d_data = d_res.json()
        assert "bundle_data" in d_data
        assert d_data["bundle_data"]["nodes_count"] >= 2

    def test_batch_sync_events_execution(self):
        key_loc = str(uuid.uuid4())
        key_haz = str(uuid.uuid4())
        key_trip = str(uuid.uuid4())

        now_str = timezone.now().isoformat()

        batch_payload = {
            "events": [
                {
                    "idempotency_key": key_loc,
                    "event_type": SyncEventType.LOCATION_UPDATE,
                    "client_timestamp": now_str,
                    "payload": {
                        "latitude": 25.9032,
                        "longitude": 91.8814,
                        "speed_mps": 14.5,
                        "heading_deg": 180.0,
                        "trip_id": str(self.trip.id),
                    },
                },
                {
                    "idempotency_key": key_haz,
                    "event_type": SyncEventType.HAZARD_REPORT,
                    "client_timestamp": now_str,
                    "payload": {
                        "incident_type": "LANDSLIDE",
                        "severity": "HIGH",
                        "latitude": 25.7500,
                        "longitude": 91.8200,
                        "description": "Mudslide blocking northbound lane on NH6",
                        "edge_id": self.edge.id,
                    },
                },
                {
                    "idempotency_key": key_trip,
                    "event_type": SyncEventType.TRIP_STATUS,
                    "client_timestamp": now_str,
                    "payload": {
                        "trip_id": str(self.trip.id),
                        "status": "ACTIVE",
                        "route_version": 1,
                    },
                },
            ]
        }

        res = self.client.post("/api/v1/sync/events/batch/", batch_payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_events"] == 3
        assert data["applied_count"] == 3
        assert data["conflict_count"] == 0

        # Verify domain entities
        self.trip.refresh_from_db()
        assert self.trip.status == TripStatus.ACTIVE
        assert self.trip.actual_departure is not None

        incident = HazardIncident.objects.filter(edge=self.edge).first()
        assert incident is not None
        assert incident.incident_type == "LANDSLIDE"
        assert incident.source == "DRIVER"

    def test_idempotency_duplicate_submission(self):
        key = str(uuid.uuid4())
        now_str = timezone.now().isoformat()
        payload = {
            "events": [
                {
                    "idempotency_key": key,
                    "event_type": SyncEventType.LOCATION_UPDATE,
                    "client_timestamp": now_str,
                    "payload": {"latitude": 26.0, "longitude": 91.8},
                }
            ]
        }

        # First submission
        res1 = self.client.post("/api/v1/sync/events/batch/", payload, format="json")
        assert res1.status_code == status.HTTP_200_OK
        assert res1.json()["applied_count"] == 1

        # Second submission with same key
        res2 = self.client.post("/api/v1/sync/events/batch/", payload, format="json")
        assert res2.status_code == status.HTTP_200_OK
        assert res2.json()["duplicate_count"] == 1
        assert res2.json()["applied_count"] == 0

        # Verify exactly 1 record in database
        assert SyncQueueRecord.objects.filter(idempotency_key=key).count() == 1

    def test_monotonic_trip_conflict_rejection(self):
        # Move trip directly to COMPLETED
        self.trip.status = TripStatus.COMPLETED
        self.trip.save(update_fields=["status"])

        key = str(uuid.uuid4())
        payload = {
            "events": [
                {
                    "idempotency_key": key,
                    "event_type": SyncEventType.TRIP_STATUS,
                    "client_timestamp": timezone.now().isoformat(),
                    "payload": {
                        "trip_id": str(self.trip.id),
                        "status": "ACTIVE",
                    },
                }
            ]
        }

        res = self.client.post("/api/v1/sync/events/batch/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["conflict_count"] == 1
        assert data["applied_count"] == 0

        # Ensure trip stayed COMPLETED
        self.trip.refresh_from_db()
        assert self.trip.status == TripStatus.COMPLETED

    def test_emergency_sos_and_sync_status_diagnostics(self):
        sos_payload = {
            "latitude": 25.8000,
            "longitude": 91.8500,
            "trip": str(self.trip.id),
            "message": "Emergency: Flash flood washed road ahead.",
        }

        # Trigger SOS
        sos_res = self.client.post("/api/v1/sync/sos/", sos_payload, format="json")
        assert sos_res.status_code == status.HTTP_201_CREATED
        sos_data = sos_res.json()
        assert sos_data["status"] == EmergencySOSStatus.TRIGGERED

        # Query Diagnostics
        diag_res = self.client.get("/api/v1/sync/status/")
        assert diag_res.status_code == status.HTTP_200_OK
        diag_data = diag_res.json()
        assert diag_data["active_sos_count"] >= 1
