"""
SIH26002 — Phase 10 Demo Readiness, Safe Reset & Orchestration Tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.demo_views import SafeDemoResetService, run_deterministic_phase10_demo
from apps.transport_graph.models import EdgeStatus, TransportEdge

User = get_user_model()


@pytest.mark.django_db
class TestPhase10DemoAndReadiness:
    def setup_method(self):
        self.client = APIClient()

    def test_demo_readiness_endpoint(self):
        """Validates that /api/v1/demo/readiness/ returns READY with all 15 checks passing."""
        response = self.client.get("/api/v1/demo/readiness/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "READY"
        assert data.get("success") is True

        checks = data.get("checks", {})
        required_checks = [
            "database", "postgis", "migrations", "transport_graph",
            "hazards", "routing", "fleet", "freight", "marketplace",
            "tracking", "accessibility", "optimization", "simulation",
            "ai_models", "offline_bundle",
        ]
        for rc in required_checks:
            assert rc in checks, f"Missing check: {rc}"
            assert checks[rc] == "PASS", f"Check {rc} did not PASS: {checks[rc]}"

    def test_demo_reset_requires_confirmation_token(self):
        """Validates that demo reset rejects unconfirmed or non-demo mode requests."""
        # Missing payload
        res1 = self.client.post("/api/v1/demo/reset/", {})
        assert res1.status_code == 400
        assert "Safety guard" in res1.json().get("error", "")

        # Missing confirm_demo_reset
        res2 = self.client.post("/api/v1/demo/reset/", {"mode": "DEMO"})
        assert res2.status_code == 400

        # Wrong mode
        res3 = self.client.post("/api/v1/demo/reset/", {"confirm_demo_reset": True, "mode": "PRODUCTION"})
        assert res3.status_code == 400

    def test_safe_demo_reset_execution(self):
        """Validates that safe demo reset restores baseline state."""
        # Create a real production user to verify it is NOT deleted
        real_user = User.objects.create(
            email="official_pwd_admin@gov.in",
            phone="+919876500001",
            first_name="Official",
            last_name="PWD",
            role="MINISTRY_ADMIN",
            is_active=True,
        )

        response = self.client.post("/api/v1/demo/reset/", {
            "confirm_demo_reset": True,
            "mode": "DEMO",
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("data", {}).get("demo_reset_status") == "SUCCESS"

        # Verify real user was preserved
        assert User.objects.filter(email="official_pwd_admin@gov.in").exists()

        # Verify edge status restored to OPEN
        blocked_edges = TransportEdge.objects.filter(status=EdgeStatus.BLOCKED).count()
        assert blocked_edges == 0

    def test_24_step_demo_orchestrator(self):
        """Validates full execution of 24-step deterministic demo."""
        results = run_deterministic_phase10_demo()
        assert len(results) == 24
        for step in results:
            assert step["status"] == "SUCCESS", f"Step {step['step']} failed: {step['title']}"

        assert results[0]["step"] == 1
        assert results[23]["step"] == 24
        assert results[23]["details"]["verification_result"] == "PASSED_24_OF_24"

    def test_demo_orchestrate_api(self):
        """Validates POST /api/v1/demo/orchestrate/ returns complete 24 steps."""
        response = self.client.post("/api/v1/demo/orchestrate/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("total_steps") == 24
        assert len(data.get("steps_log", [])) == 24

    def test_demo_generalization_report_api(self):
        """Validates GET /api/v1/demo/generalization-report/ exposes 5 unseen scenarios."""
        response = self.client.get("/api/v1/demo/generalization-report/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        report = data.get("report", {})
        assert "disclaimer" in report
        assert "Synthetic evaluation only" in report["disclaimer"]
        assert "out_of_distribution_generalization" in report
        scenarios = report["out_of_distribution_generalization"]["scenario_breakdown"]
        assert len(scenarios) == 5
