"""
SIH26002 — Phase 10 RBAC Authorization & Security Audit Tests.

Verifies role-based access restrictions across all 7 platform roles:
DRIVER, FLEET_OPERATOR, SHIPPER, CHECKPOST_OPERATOR,
COMMUNITY_NODE_MANAGER, MINISTRY_ADMIN, SUPER_ADMIN.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestPhase10RBACSecurityAudit:
    def setup_method(self):
        self.client = APIClient()
        self.roles = [
            UserRole.DRIVER,
            UserRole.FLEET_OPERATOR,
            UserRole.SHIPPER,
            UserRole.CHECKPOST_OPERATOR,
            UserRole.COMMUNITY_NODE_MANAGER,
            UserRole.MINISTRY_ADMIN,
            UserRole.SUPER_ADMIN,
        ]

    def test_unauthenticated_request_rejected_on_protected_endpoints(self):
        """Unauthenticated requests to protected endpoints return 401 Unauthorized."""
        protected_endpoints = [
            "/api/v1/intelligence/network/",
            "/api/v1/intelligence/corridors/",
            "/api/v1/intelligence/recommendations/",
            "/api/v1/auth/me/",
        ]
        for ep in protected_endpoints:
            res = self.client.get(ep)
            assert res.status_code == status.HTTP_401_UNAUTHORIZED, f"Endpoint {ep} should require auth"

    def test_all_roles_can_access_own_profile(self):
        """Every authenticated role can access /api/v1/auth/me/."""
        for role in self.roles:
            user = User.objects.create_user(
                email=f"user_{role.lower()}@ner.gov.in",
                password="TestPassword123!",
                role=role,
            )
            client = APIClient()
            client.force_authenticate(user=user)
            res = client.get("/api/v1/auth/me/")
            assert res.status_code == status.HTTP_200_OK
            assert res.json().get("data", {}).get("role") == role

    def test_public_health_and_demo_endpoints_no_secret_leak(self):
        """Readiness and health endpoints are accessible without auth and do not expose passwords or keys."""
        public_endpoints = [
            "/api/v1/health/",
            "/api/v1/health/db/",
            "/api/v1/demo/readiness/",
        ]
        for ep in public_endpoints:
            res = self.client.get(ep)
            assert res.status_code == status.HTTP_200_OK
            text = res.content.decode("utf-8").lower()
            assert "secret_key" not in text
            assert "password" not in text
            assert "sih_pass" not in text
