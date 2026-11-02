"""
SIH26002 — Vehicles app tests.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import UserRole
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestVehicles:

    def setup_method(self):
        self.client = APIClient()
        self.fleet_user = User.objects.create_user(
            email="fleetowner@ner.in",
            password="Password123!",
            role=UserRole.FLEET_OPERATOR,
        )
        self.client.force_authenticate(user=self.fleet_user)
        self.list_url = "/api/v1/vehicles/"

    def test_create_and_list_vehicle(self):
        payload = {
            "registration_number": "AS-01-GB-1234",
            "vehicle_type": VehicleType.MEDIUM_TRUCK,
            "make": "Tata Motors",
            "model_name": "Ultra T.12",
            "year": 2023,
            "capacity_kg": 7500.0,
            "capacity_cbm": 30.0,
            "fuel_type": "DIESEL",
        }
        response = self.client.post(self.list_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["registration_number"] == "AS-01-GB-1234"

        # List vehicles
        get_res = self.client.get(self.list_url)
        assert get_res.status_code == status.HTTP_200_OK
        assert len(get_res.data["data"]) == 1
