"""
SIH26002 — Authentication and User RBAC unit/integration tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestAuthentication:
    """Test user registration, login, token refresh, and logout."""

    def setup_method(self):
        self.client = APIClient()
        self.register_url = "/api/v1/auth/register/"
        self.login_url = "/api/v1/auth/login/"
        self.me_url = "/api/v1/auth/me/"

    def test_user_registration_success(self):
        payload = {
            "email": "driver1@ner.gov.in",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "Rongsen",
            "last_name": "Ao",
            "role": UserRole.DRIVER,
            "preferred_language": "en",
        }
        response = self.client.post(self.register_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert "tokens" in response.data["data"]
        assert response.data["data"]["user"]["email"] == "driver1@ner.gov.in"

    def test_user_login_success(self):
        user = User.objects.create_user(
            email="fleet@ner.gov.in",
            password="SecurePassword123!",
            role=UserRole.FLEET_OPERATOR,
        )
        payload = {
            "email": "fleet@ner.gov.in",
            "password": "SecurePassword123!",
        }
        response = self.client.post(self.login_url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data["data"]
        assert "access" in response.data["data"]["tokens"]

    def test_get_current_user_me(self):
        user = User.objects.create_user(
            email="shipper@ner.gov.in",
            password="SecurePassword123!",
            role=UserRole.SHIPPER,
            first_name="Bimal",
            last_name="Roy",
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.me_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["email"] == "shipper@ner.gov.in"
        assert response.data["data"]["role"] == UserRole.SHIPPER
