"""
SIH26002 — Phase 9 Explainable AI, Accessibility & Command Center Tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.analytics.models import DecisionRecommendation, NetworkHealthSnapshot
from apps.analytics.services.explainability_service import DecisionExplanationService
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.transport_graph.services.accessibility import AccessibilityIntelligenceService

User = get_user_model()


@pytest.mark.django_db
class TestPhase9ExplainabilityAndAccessibility:
    @pytest.fixture(autouse=True)
    def setup_intelligence_data(self):
        self.user = User.objects.create(
            email="admin_intelligence@nerlogistics.gov.in",
            phone="+919876543009",
            first_name="Admin",
            last_name="Intelligence",
            role="SUPER_ADMIN",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.node = TransportNode.objects.create(
            name="Guwahati Gate Hub",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.73 26.18)",
            state="Assam",
            district="Kamrup Metro",
            is_active=True,
        )

    def test_explainability_service_records_decision_contract(self):
        rec = DecisionExplanationService.record_decision(
            decision_type=DecisionRecommendation.DecisionType.ROUTE_RECOMMENDATION,
            title="Recommended multimodal rail bypass for tea freight",
            target_entity_type="Route",
            target_entity_id="ROUTE-101",
            recommendation_payload={"suggested_mode": "RAIL", "transit_time_h": 14.5},
            confidence=0.89,
            primary_factors=[
                {"factor": "NH-6 Monsoonal Hazard", "weight": 0.55, "detail": "Active mudslide warning"},
                {"factor": "Bulk Capacity Clearance", "weight": 0.30, "detail": "Freight rake available at Guwahati"},
            ],
            tradeoffs=[
                {"tradeoff": "Transit duration vs Disaster risk", "time_cost": "+2.5h", "risk_mitigation": "-78%"},
            ],
            is_simulation=True,
        )

        assert rec.id is not None
        assert rec.confidence == 0.89
        assert len(rec.primary_factors) == 2
        assert rec.is_simulation is True

    def test_accessibility_intelligence_service(self):
        data = AccessibilityIntelligenceService.get_network_accessibility_intelligence()
        assert "composite_accessibility_index" in data
        assert "state_accessibility" in data
        assert "corridors" in data
        assert "most_vulnerable_nodes" in data
        assert "recovery_priorities" in data

    def test_network_operational_summary_api(self):
        response = self.client.get("/api/v1/intelligence/network/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "severity_state" in data
        assert "metrics" in data
        assert "data_source" in data

    def test_corridors_health_api(self):
        response = self.client.get("/api/v1/intelligence/corridors/")
        assert response.status_code == 200
        data = response.json()
        assert "corridors" in data
        assert len(data["corridors"]) >= 1

    def test_recommendations_api(self):
        response = self.client.get("/api/v1/intelligence/recommendations/")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    def test_detailed_health_check_api(self):
        response = self.client.get("/api/v1/health/detailed/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["HEALTHY", "DEGRADED", "UNAVAILABLE"]
        assert "subsystems" in data
        assert "fleet_optimizer" in data["subsystems"]
        assert "simulation_engine" in data["subsystems"]
        assert "eta_intelligence" in data["subsystems"]
