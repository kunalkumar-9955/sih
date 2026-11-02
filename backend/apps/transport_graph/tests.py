"""
SIH26002 — Transport graph tests: models, validation, spatial queries.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from rest_framework import status
from rest_framework.test import APIClient

from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.transport_graph.spatial import (
    find_nearest_node,
    find_nearby_hubs,
    get_corridor_subgraph_edges,
)
from apps.transport_graph.validation import TransportGraphValidator
from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestTransportGraph:

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="driver@test.com", password="Password123!", role=UserRole.DRIVER
        )
        self.admin = User.objects.create_superuser(
            email="admin@test.com", password="Password123!"
        )
        self.client.force_authenticate(user=self.user)

        self.node_a = TransportNode.objects.create(
            name="Guwahati Node",
            geometry=Point(91.7362, 26.1445, srid=4326),
            node_type=NodeType.MULTIMODAL_HUB,
            short_code="GAU-TEST",
        )
        self.node_b = TransportNode.objects.create(
            name="Shillong Node",
            geometry=Point(91.8830, 25.5788, srid=4326),
            node_type=NodeType.LOCAL_HUB,
            short_code="SHL-TEST",
        )
        self.edge = TransportEdge.objects.create(
            source_node=self.node_a,
            target_node=self.node_b,
            mode=TransportMode.ROAD,
            distance_m=100000.0,
            base_transit_time_min=180.0,
            cost_inr=2500.0,
            hazard_score=0.2,
            geometry=LineString([self.node_a.geometry, self.node_b.geometry], srid=4326),
        )

    def test_list_nodes(self):
        res = self.client.get("/api/v1/transport/nodes/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data["results"]) >= 2

    def test_list_edges(self):
        res = self.client.get("/api/v1/transport/edges/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data["results"]) >= 1

    def test_graph_dump(self):
        res = self.client.get("/api/v1/transport/graph/")
        assert res.status_code == status.HTTP_200_OK
        assert "nodes" in res.data
        assert "edges" in res.data
        assert len(res.data["nodes"]) >= 2

    def test_graph_validation_passes_valid_network(self):
        validator = TransportGraphValidator()
        result = validator.validate()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_graph_validation_catches_invalid_geometry(self):
        # Create node outside NER bounds (e.g. London coordinates)
        invalid_node = TransportNode.objects.create(
            name="London Node",
            geometry=Point(-0.1278, 51.5074, srid=4326),
            node_type=NodeType.LOCAL_HUB,
            short_code="LON-INV",
        )
        validator = TransportGraphValidator()
        result = validator.validate()
        assert result.is_valid is False
        assert any("London Node" in err for err in result.errors)
        invalid_node.delete()

    def test_spatial_find_nearest_node(self):
        # Query near Guwahati coordinates
        found = find_nearest_node(26.1400, 91.7300)
        assert found is not None
        assert found.id == self.node_a.id

    def test_spatial_find_nearby_hubs(self):
        hubs = find_nearby_hubs(26.1445, 91.7362, radius_km=50.0)
        assert len(hubs) >= 1
        assert any(h.id == self.node_a.id for h in hubs)

    def test_corridor_subgraph_edges(self):
        edges = get_corridor_subgraph_edges(min_lat=25.0, min_lon=90.0, max_lat=27.0, max_lon=93.0)
        assert len(edges) >= 1
        assert any(e.id == self.edge.id for e in edges)

