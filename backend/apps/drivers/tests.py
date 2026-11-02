"""
NorthLink / SIH26002 — Drivers app & RBAC isolation tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestDriverProfile:

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="driver@ner.in",
            password="Password123!",
            role=UserRole.DRIVER,
            first_name="Tenzing",
            last_name="Norgay",
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/drivers/profile/"

    def test_get_driver_profile_auto_creates(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["email"] == "driver@ner.in"
        assert Driver.objects.filter(user=self.user).exists()

    def test_update_driver_profile(self):
        payload = {
            "license_number": "AS-01-2024-009876",
            "home_state": "Assam",
            "home_district": "Kamrup Metro",
        }
        response = self.client.put(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["license_number"] == "AS-01-2024-009876"
        assert response.data["data"]["home_state"] == "Assam"


@pytest.mark.django_db
class TestDriverRBACAndDashboard:

    def setup_method(self):
        self.client = APIClient()
        self.driver_user = User.objects.create_user(
            email="driver_test@northlink.ner",
            password="Password123!",
            role=UserRole.DRIVER,
            first_name="Ramesh",
            last_name="Baruah",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin_test@northlink.ner",
            password="AdminPassword123!",
            first_name="Ministry",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
        )

    def test_driver_dashboard_scoped_data(self):
        self.client.force_authenticate(user=self.driver_user)
        res = self.client.get("/api/v1/driver/dashboard/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["success"] is True
        assert res.data["data"]["driver"]["email"] == "driver_test@northlink.ner"
        assert "active_trip" in res.data["data"]
        assert "route_hazards" in res.data["data"]
        assert "sync_status" in res.data["data"]

    def test_driver_forbidden_from_admin_simulations(self):
        """Driver must receive HTTP 403 when trying to access admin disruption simulator."""
        self.client.force_authenticate(user=self.driver_user)
        res = self.client.get("/api/v1/simulations/")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_permitted_on_simulations(self):
        """Admin must receive HTTP 200 on simulations."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get("/api/v1/simulations/")
        assert res.status_code == status.HTTP_200_OK

    def test_driver_sos_trigger_and_resolve(self):
        self.client.force_authenticate(user=self.driver_user)
        res_trig = self.client.post("/api/v1/driver/sos/", {"action": "TRIGGER", "notes": "Engine heating"}, format="json")
        assert res_trig.status_code == status.HTTP_201_CREATED
        assert res_trig.data["status"] == "TRIGGERED"

        res_res = self.client.post("/api/v1/driver/sos/", {"action": "RESOLVE"}, format="json")
        assert res_res.status_code == status.HTTP_200_OK
        assert res_res.data["status"] == "RESOLVED"
