"""
SIH26002 — Trips Base Tests.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.transport_graph.models import NodeType, TransportNode
from apps.trips.models import Trip, TripStatus
from apps.users.models import UserRole
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestTrips:

    def setup_method(self):
        self.client = APIClient()
        self.driver_user = User.objects.create_user(
            email="driver@ner.in", password="Password123!", role=UserRole.DRIVER
        )
        self.driver_profile = Driver.objects.create(user=self.driver_user)
        self.client.force_authenticate(user=self.driver_user)

        self.node_orig = TransportNode.objects.create(name="Origin", geometry=Point(91.0, 26.0, srid=4326), node_type=NodeType.LOCAL_HUB)
        self.node_dest = TransportNode.objects.create(name="Dest", geometry=Point(92.0, 26.0, srid=4326), node_type=NodeType.LOCAL_HUB)

        self.vehicle = Vehicle.objects.create(
            owner=self.driver_user,
            registration_number="AS-01-XX-9999",
            vehicle_type=VehicleType.LIGHT_TRUCK,
            capacity_kg=2500,
            status=VehicleStatus.AVAILABLE,
        )

    def test_create_trip_and_transition_status(self):
        payload = {
            "origin_node": str(self.node_orig.id),
            "destination_node": str(self.node_dest.id),
            "vehicle": str(self.vehicle.id),
            "cargo_description": "Agricultural produce - Spices and Ginger",
            "cargo_weight_kg": 1200.0,
        }
        res = self.client.post("/api/v1/trips/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        trip_id = res.data["id"]

        # Transition status to ACTIVE
        status_res = self.client.post(
            f"/api/v1/trips/{trip_id}/status/",
            {"status": TripStatus.ACTIVE, "notes": "Departed warehouse on schedule"},
            format="json",
        )
        assert status_res.status_code == status.HTTP_200_OK
        assert status_res.data["status"] == TripStatus.ACTIVE
        assert status_res.data["actual_departure"] is not None

        # Verify vehicle status is updated to ON_TRIP
        self.vehicle.refresh_from_db()
        assert self.vehicle.status == VehicleStatus.ON_TRIP

        # Transition status to COMPLETED
        comp_res = self.client.post(
            f"/api/v1/trips/{trip_id}/status/",
            {"status": TripStatus.COMPLETED, "notes": "Delivered successfully"},
            format="json",
        )
        assert comp_res.status_code == status.HTTP_200_OK
        assert comp_res.data["status"] == TripStatus.COMPLETED
        assert comp_res.data["actual_arrival"] is not None

        # Verify vehicle status returned to AVAILABLE
        self.vehicle.refresh_from_db()
        assert self.vehicle.status == VehicleStatus.AVAILABLE
