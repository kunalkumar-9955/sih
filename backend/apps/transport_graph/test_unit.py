"""
SIH26002 — Transport Graph Unit Tests (Pure Python / In-Memory).
Tests graph validation rules, bounding boxes, topology, and node/edge checks.
"""
import pytest
from apps.transport_graph.models import EdgeStatus, NodeType, TransportMode
from apps.transport_graph.validation import TransportGraphValidator, GraphValidationResult


class MockGeometryPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class MockGeometryLine:
    def __init__(self, coords):
        self.coords = coords


class MockNode:
    def __init__(self, node_id, name, lon, lat, node_type=NodeType.LOCAL_HUB, is_active=True):
        self.id = node_id
        self.name = name
        self.geometry = MockGeometryPoint(lon, lat)
        self.node_type = node_type
        self.is_active = is_active
        self.short_code = name[:6].upper()
        self.elevation_m = 100.0

    def __str__(self):
        return f"{self.name} ({self.short_code})"


class MockEdge:
    def __init__(
        self,
        edge_id,
        source_node,
        target_node,
        mode=TransportMode.ROAD,
        distance_m=10000.0,
        base_transit_time_min=30.0,
        cost_inr=500.0,
        hazard_score=0.1,
        status=EdgeStatus.OPEN,
        is_available=True,
    ):
        self.id = edge_id
        self.source_node = source_node
        self.source_node_id = source_node.id
        self.target_node = target_node
        self.target_node_id = target_node.id
        self.mode = mode
        self.distance_m = distance_m
        self.base_transit_time_min = base_transit_time_min
        self.cost_inr = cost_inr
        self.hazard_score = hazard_score
        self.status = status
        self.is_available = is_available
        self.seasonal_open_month = None
        self.seasonal_close_month = None
        self.water_level_m = None
        self.min_required_depth_m = None
        self.draft_requirement_m = None
        self.max_payload_tons = None
        self.transfer_time_min = None
        self.geometry = MockGeometryLine([
            (source_node.geometry.x, source_node.geometry.y),
            (target_node.geometry.x, target_node.geometry.y)
        ])

    @property
    def normalized_mode(self):
        return TransportMode.normalize(self.mode)

    @property
    def is_transfer(self):
        return self.normalized_mode == TransportMode.TRANSFER

    @property
    def is_waterway(self):
        return self.normalized_mode == TransportMode.WATER

    def __str__(self):
        return f"{self.source_node.name} -> {self.target_node.name} ({self.mode})"


class TestTransportGraphUnitValidation:

    def test_validation_passes_valid_corridor(self):
        nA = MockNode("n1", "Guwahati", 91.7362, 26.1445, NodeType.MULTIMODAL_HUB)
        nB = MockNode("n2", "Shillong", 91.8830, 25.5788, NodeType.LOCAL_HUB)
        eAB = MockEdge("e1", nA, nB, TransportMode.ROAD, 100000.0, 180.0, 2500.0, 0.2)

        validator = TransportGraphValidator()
        result = validator.validate_full_graph(nodes=[nA, nB], edges=[eAB])
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.stats["total_nodes"] == 2
        assert result.stats["total_edges"] == 1

    def test_validation_catches_invalid_latitude_longitude(self):
        nInvalid = MockNode("n_bad", "Invalid Hub", 250.0, 120.0)
        validator = TransportGraphValidator()
        issues = validator.validate_node(nInvalid)
        assert len(issues) > 0
        assert any("Invalid longitude" in i for i in issues)
        assert any("Invalid latitude" in i for i in issues)

    def test_validation_catches_non_positive_distance_or_time(self):
        nA = MockNode("n1", "Guwahati", 91.7362, 26.1445)
        nB = MockNode("n2", "Shillong", 91.8830, 25.5788)
        eBad = MockEdge("e_bad", nA, nB, distance_m=-500.0, base_transit_time_min=0.0)

        validator = TransportGraphValidator()
        issues = validator.validate_edge(eBad)
        assert any("Non-positive distance" in i for i in issues)
        assert any("Non-positive base transit time" in i for i in issues)

    def test_validation_warns_on_isolated_node(self):
        nA = MockNode("n1", "Guwahati", 91.7362, 26.1445)
        nB = MockNode("n2", "Shillong", 91.8830, 25.5788)
        nIsolated = MockNode("n3", "Isolated Hub", 92.0, 26.0)
        eAB = MockEdge("e1", nA, nB)

        validator = TransportGraphValidator()
        result = validator.validate_full_graph(nodes=[nA, nB, nIsolated], edges=[eAB])
        assert result.is_valid is True  # Warning does not invalidate graph
        assert any("Isolated Hub" in w and "isolated" in w.lower() for w in result.warnings)
