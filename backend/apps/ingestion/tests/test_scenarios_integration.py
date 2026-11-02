"""
Integration tests for Demo Scenario Engine, API Endpoints, and Accessibility Intelligence.
Tests scenario activation (LANDSLIDE, HEAVY_RAIN, MULTIMODAL_SWITCH, NORMAL),
ensuring edge risk updates, reroute triggers, API responses, and baseline resets.
"""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, LineString
from apps.transport_graph.models import TransportNode, TransportEdge
from apps.hazards.models import HazardScore
from apps.ingestion.models import DataProvider, DemoScenarioRecord
from apps.ingestion.services.scenario_engine import DemoScenarioEngine
from apps.transport_graph.services.accessibility import AccessibilityIntelligenceService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="admin_phase6@sih.gov.in",
        password="AdminSecurePassword123!",
        role="SUPER_ADMIN",
        first_name="Admin",
        last_name="Super",
    )


@pytest.fixture
def corridor_graph(db):
    """Seed minimal corridor graph: Guwahati -> Nongpoh -> Shillong with road and rail edges."""
    node_ghy = TransportNode.objects.create(
        name="Guwahati Hub",
        short_code="GHY-01",
        state="Assam",
        geometry=Point(91.7362, 26.1445, srid=4326),
        node_type="MULTIMODAL_HUB",
    )
    node_nongpoh = TransportNode.objects.create(
        name="Nongpoh",
        short_code="NGP-01",
        state="Meghalaya",
        geometry=Point(91.8804, 25.9034, srid=4326),
        node_type="ROAD_INTERSECTION",
    )
    node_shillong = TransportNode.objects.create(
        name="Shillong",
        short_code="SHL-01",
        state="Meghalaya",
        geometry=Point(91.8933, 25.5788, srid=4326),
        node_type="LOGISTICS_HUB",
    )

    edge_road_1 = TransportEdge.objects.create(
        source_node=node_ghy,
        target_node=node_nongpoh,
        mode="ROAD",
        distance_m=52000.0,
        base_transit_time_min=70.0,
        geometry=LineString([(91.7362, 26.1445), (91.8804, 25.9034)], srid=4326),
        status="OPEN",
    )
    edge_road_2 = TransportEdge.objects.create(
        source_node=node_nongpoh,
        target_node=node_shillong,
        mode="ROAD",
        distance_m=48000.0,
        base_transit_time_min=65.0,
        geometry=LineString([(91.8804, 25.9034), (91.8933, 25.5788)], srid=4326),
        status="OPEN",
    )

    # Waterway edge for multimodal demo: Guwahati to Pandu Port
    node_pandu = TransportNode.objects.create(
        name="Pandu Port (NW-2)",
        short_code="PND-01",
        state="Assam",
        geometry=Point(91.6800, 26.1750, srid=4326),
        node_type="PORT",
    )
    edge_water = TransportEdge.objects.create(
        source_node=node_ghy,
        target_node=node_pandu,
        mode="WATER",
        distance_m=12000.0,
        base_transit_time_min=45.0,
        geometry=LineString([(91.7362, 26.1445), (91.6800, 26.1750)], srid=4326),
        status="OPEN",
    )

    return {
        "nodes": [node_ghy, node_nongpoh, node_shillong, node_pandu],
        "edges": [edge_road_1, edge_road_2, edge_water],
    }


@pytest.mark.django_db
class TestDemoScenarioEngine:
    def test_heavy_rain_scenario_activation(self, corridor_graph):
        engine = DemoScenarioEngine()
        result = engine.activate_scenario("HEAVY_RAIN")

        assert result["status"] == "ACTIVATED"
        assert result["scenario"] == "HEAVY_RAIN"
        assert result["is_simulation"] is True
        assert result["affected_edges_count"] > 0

        # Check demo record was logged
        demo_record = DemoScenarioRecord.objects.filter(name="HEAVY_RAIN").first()
        assert demo_record is not None
        assert demo_record.is_active is True

    def test_landslide_scenario_blocks_edges_and_updates_hazard(self, corridor_graph):
        engine = DemoScenarioEngine()
        result = engine.activate_scenario("LANDSLIDE")

        assert result["status"] == "ACTIVATED"
        assert result["scenario"] == "LANDSLIDE"

        # Check that hazard score records were created
        hazard_scores = HazardScore.objects.filter(edge__in=corridor_graph["edges"])
        assert hazard_scores.exists()

        critical_scores = hazard_scores.filter(hazard_index__gte=0.85)
        assert critical_scores.count() >= 1

    def test_scenario_reset_to_baseline(self, corridor_graph):
        engine = DemoScenarioEngine()
        engine.activate_scenario("ROAD_BLOCKAGE")
        
        # Reset to baseline
        reset_res = engine.reset_to_baseline()
        assert reset_res["status"] == "ACTIVATED"
        assert reset_res["scenario"] == "NORMAL"

        # Check all edges restored to OPEN
        for edge in corridor_graph["edges"]:
            edge.refresh_from_db()
            assert edge.status == "OPEN"


@pytest.mark.django_db
class TestAccessibilityIntelligence:
    def test_accessibility_score_computation(self, corridor_graph):
        service = AccessibilityIntelligenceService()
        res = service.evaluate_corridor_accessibility(region="Guwahati - Shillong Corridor")

        assert 0.0 <= res["accessibility_score"] <= 100.0
        assert "contributing_factors" in res
        assert "connectivity_density" in res["contributing_factors"]
        assert "geohazard_safety" in res["contributing_factors"]
        assert "multimodal_redundancy" in res["contributing_factors"]
        assert "disclaimer" in res
        assert "logistical intelligence" in res["disclaimer"]


@pytest.mark.django_db
class TestIngestionAndHealthAPIEndpoints:
    def test_get_providers_endpoint(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)
        # Ensure at least 1 provider registered
        DataProvider.objects.get_or_create(
            source_code="IMD_WEATHER",
            defaults={"name": "IMD Weather", "source_type": "WEATHER"}
        )

        response = api_client.get("/api/v1/ingestion/providers/")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_get_freshness_summary(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)
        response = api_client.get("/api/v1/ingestion/freshness/")
        assert response.status_code == 200
        assert "total_providers" in response.data
        assert "providers" in response.data

    def test_activate_and_reset_demo_scenario_via_api(self, api_client, superuser, corridor_graph):
        api_client.force_authenticate(user=superuser)

        # Activate HEAVY_RAIN
        act_resp = api_client.post(
            "/api/v1/ingestion/scenarios/activate/",
            {"scenario_name": "HEAVY_RAIN"},
            format="json",
        )
        assert act_resp.status_code == 200
        assert act_resp.data["is_simulation"] is True

        # Reset
        rst_resp = api_client.post("/api/v1/ingestion/scenarios/reset/")
        assert rst_resp.status_code == 200
        assert rst_resp.data["scenario"] == "NORMAL"

    def test_detailed_health_endpoint(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)
        response = api_client.get("/api/v1/health/detailed/")
        assert response.status_code == 200
        assert response.data["status"] in ["HEALTHY", "DEGRADED"]
        assert "subsystems" in response.data
        assert "database" in response.data["subsystems"]
        assert "postgis" in response.data["subsystems"]
