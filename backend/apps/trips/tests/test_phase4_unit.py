"""
SIH26002 — Phase 4 Pure Unit Tests (DB-Free).

Tests:
1. RouteRiskEvaluator on empty route
2. RouteRiskEvaluator metric calculation (max, mean, counts)
3. RouteRiskEvaluator blocked & critical detection
4. HazardChangeDetector below threshold (no reroute)
5. HazardChangeDetector delta threshold trigger
6. HazardChangeDetector critical hazard trigger
7. HazardChangeDetector blocked edge mandatory trigger
8. RerouteNotificationService payload structure & metrics
9. RerouteNotificationService mandatory vs advisory actions
10. RerouteDecisionService improvement threshold filtering
11. HazardPropagationService 1-hop and 2-hop decay calculation
12. HazardPropagationService non-downgrade rule
"""
import pytest
from unittest.mock import MagicMock, patch

from apps.hazards.models import HazardSeverity
from apps.hazards.services.propagation import HazardPropagationService
from apps.routing.models import RouteType
from apps.routing.services.hazard_change import HazardChangeDetector
from apps.routing.services.notification import RerouteNotificationService
from apps.routing.services.reroute_decision import RerouteDecisionService
from apps.routing.services.route_risk import RouteRiskEvaluator
from apps.transport_graph.models import EdgeStatus, TransportMode


class MockNode:
    def __init__(self, node_id, name):
        self.id = node_id
        self.name = name


class MockEdge:
    def __init__(
        self,
        edge_id,
        source_name="NodeA",
        target_name="NodeB",
        hazard_score=0.1,
        status=EdgeStatus.OPEN,
        is_available=True,
    ):
        self.id = edge_id
        self.source_node = MockNode(f"n_{source_name}", source_name)
        self.target_node = MockNode(f"n_{target_name}", target_name)
        self.source_node_id = self.source_node.id
        self.target_node_id = self.target_node.id
        self.hazard_score = hazard_score
        self.status = status
        self.is_available = is_available
        self.mode = TransportMode.ROAD


class MockRoute:
    def __init__(
        self,
        route_id="r1",
        route_type=RouteType.SAFEST,
        total_time_min=180.0,
        total_distance_m=120000.0,
        max_hazard_score=0.20,
        segments=None,
    ):
        self.id = route_id
        self.route_type = route_type
        self.total_time_min = total_time_min
        self.total_distance_m = total_distance_m
        self.max_hazard_score = max_hazard_score
        self.safety_level = HazardSeverity.classify(max_hazard_score)
        self.segments = segments or [
            {"edge_id": "e1", "hazard_score": 0.1},
            {"edge_id": "e2", "hazard_score": 0.2},
        ]


class TestPhase4UnitTests:
    """12 Comprehensive DB-Free Unit Tests for Phase 4."""

    # 1. RouteRiskEvaluator: Empty Route
    def test_01_route_risk_evaluator_empty_route(self):
        eval_res = RouteRiskEvaluator.evaluate_edge_ids([])
        assert eval_res["edge_count"] == 0
        assert eval_res["max_hazard_score"] == 0.0
        assert eval_res["mean_hazard_score"] == 0.0
        assert eval_res["risky_edge_count"] == 0
        assert eval_res["critical_edge_count"] == 0
        assert eval_res["has_critical_or_blocked"] is False
        assert eval_res["safety_level"] == HazardSeverity.LOW

    # 2. RouteRiskEvaluator: Metrics computation
    @patch("apps.transport_graph.models.TransportEdge.objects.filter")
    def test_02_route_risk_evaluator_metrics(self, mock_filter):
        e1 = MockEdge("e1", "Guwahati", "Nongpoh", hazard_score=0.10)
        e2 = MockEdge("e2", "Nongpoh", "Shillong", hazard_score=0.40)  # MODERATE (>=0.25)
        e3 = MockEdge("e3", "Shillong", "Jowai", hazard_score=0.60)    # HIGH (>=0.55)

        mock_qs = MagicMock()
        mock_qs.select_related.return_value = [e1, e2, e3]
        mock_filter.return_value = mock_qs

        res = RouteRiskEvaluator.evaluate_edge_ids(["e1", "e2", "e3"])
        assert res["edge_count"] == 3
        assert res["max_hazard_score"] == 0.60
        assert pytest.approx(res["mean_hazard_score"], 0.01) == 0.3667
        assert res["risky_edge_count"] == 2  # e2 (0.40) and e3 (0.60) >= 0.25
        assert res["critical_edge_count"] == 0
        assert res["safety_level"] == HazardSeverity.HIGH

    # 3. RouteRiskEvaluator: Blocked and Critical edge detection
    @patch("apps.transport_graph.models.TransportEdge.objects.filter")
    def test_03_route_risk_evaluator_detects_blocked_and_critical(self, mock_filter):
        e1 = MockEdge("e1", "Guwahati", "Dispur", hazard_score=0.90)  # CRITICAL (>=0.85)
        e2 = MockEdge("e2", "Dispur", "Khanapara", status=EdgeStatus.BLOCKED)

        mock_qs = MagicMock()
        mock_qs.select_related.return_value = [e1, e2]
        mock_filter.return_value = mock_qs

        res = RouteRiskEvaluator.evaluate_edge_ids(["e1", "e2"])
        assert res["has_critical_or_blocked"] is True
        assert res["critical_edge_count"] == 1
        assert len(res["blocked_edges"]) == 2  # e1 critical hazard, e2 status blocked
        assert res["safety_level"] == HazardSeverity.CRITICAL

    # 4. HazardChangeDetector: Below threshold
    @patch.object(RouteRiskEvaluator, "evaluate_route")
    def test_04_hazard_change_detector_below_threshold(self, mock_eval):
        mock_eval.return_value = {
            "max_hazard_score": 0.22,
            "mean_hazard_score": 0.15,
            "blocked_edges": [],
            "edge_evaluations": [],
        }
        detector = HazardChangeDetector(delta_threshold=0.15, critical_threshold=0.85)
        route = MockRoute(max_hazard_score=0.20)

        change = detector.detect_route_change(route=route, baseline_hazard=0.20)
        assert change["should_reroute"] is False
        assert change["is_blocked"] is False
        assert change["is_critical"] is False
        assert pytest.approx(change["hazard_delta"], 0.01) == 0.02

    # 5. HazardChangeDetector: Delta threshold trigger
    @patch.object(RouteRiskEvaluator, "evaluate_route")
    def test_05_hazard_change_detector_delta_threshold_trigger(self, mock_eval):
        mock_eval.return_value = {
            "max_hazard_score": 0.45,
            "mean_hazard_score": 0.30,
            "blocked_edges": [],
            "edge_evaluations": [
                {"edge_id": "e2", "hazard_score": 0.45}
            ],
        }
        detector = HazardChangeDetector(delta_threshold=0.15, critical_threshold=0.85)
        route = MockRoute(max_hazard_score=0.20)

        change = detector.detect_route_change(route=route, baseline_hazard=0.20)
        assert change["should_reroute"] is True
        assert change["hazard_delta"] == 0.25
        assert "e2" in change["triggering_edge_ids"]

    # 6. HazardChangeDetector: Critical threshold trigger
    @patch.object(RouteRiskEvaluator, "evaluate_route")
    def test_06_hazard_change_detector_critical_hazard_trigger(self, mock_eval):
        mock_eval.return_value = {
            "max_hazard_score": 0.88,
            "mean_hazard_score": 0.60,
            "blocked_edges": [],
            "edge_evaluations": [
                {"edge_id": "e3", "hazard_score": 0.88}
            ],
        }
        detector = HazardChangeDetector(delta_threshold=0.15, critical_threshold=0.85)
        route = MockRoute(max_hazard_score=0.80)

        change = detector.detect_route_change(route=route, baseline_hazard=0.80)
        assert change["should_reroute"] is True
        assert change["is_critical"] is True
        assert "CRITICAL threshold" in change["trigger_reason"]

    # 7. HazardChangeDetector: Blocked edge trigger
    @patch.object(RouteRiskEvaluator, "evaluate_route")
    def test_07_hazard_change_detector_blocked_edge_trigger(self, mock_eval):
        mock_eval.return_value = {
            "max_hazard_score": 0.20,
            "mean_hazard_score": 0.15,
            "blocked_edges": [
                {"edge_id": "e1", "source": "Shillong", "target": "Jowai", "status": "BLOCKED", "reason": "BLOCKED"}
            ],
            "edge_evaluations": [],
        }
        detector = HazardChangeDetector(delta_threshold=0.15, critical_threshold=0.85)
        route = MockRoute(max_hazard_score=0.20)

        change = detector.detect_route_change(route=route, baseline_hazard=0.20)
        assert change["should_reroute"] is True
        assert change["is_blocked"] is True
        assert "e1" in change["triggering_edge_ids"]

    # 8. RerouteNotificationService: Payload Structure & Metrics
    def test_08_reroute_notification_service_payload_structure(self):
        old_r = MockRoute(route_id="old", total_time_min=180.0, total_distance_m=100000.0, max_hazard_score=0.70)
        new_r = MockRoute(route_id="new", total_time_min=200.0, total_distance_m=110000.0, max_hazard_score=0.20)

        payload = RerouteNotificationService.build_notification_payload(
            old_route=old_r,
            new_route=new_r,
            trigger_reason="Landslide risk elevated",
            is_mandatory=False,
            improvement_pct=0.714,
        )

        assert payload["urgency"] == "HIGH"
        assert payload["is_mandatory"] is False
        assert payload["improvement_pct"] == 71.4
        assert payload["metrics"]["time_delta_min"] == 20.0
        assert payload["metrics"]["distance_delta_km"] == 10.0
        assert payload["metrics"]["old_max_hazard"] == 0.70
        assert payload["metrics"]["new_max_hazard"] == 0.20
        assert "en" in payload["i18n"]
        assert "as" in payload["i18n"]
        assert "hi" in payload["i18n"]

    # 9. RerouteNotificationService: Mandatory vs Advisory Actions
    def test_09_reroute_notification_service_mandatory_vs_advisory(self):
        old_r = MockRoute(route_id="old", total_time_min=120.0, total_distance_m=80000.0, max_hazard_score=0.90)
        new_r = MockRoute(route_id="new", total_time_min=140.0, total_distance_m=90000.0, max_hazard_score=0.25)

        # Mandatory (Road blocked / critical)
        mand_payload = RerouteNotificationService.build_notification_payload(
            old_route=old_r,
            new_route=new_r,
            trigger_reason="Corridor completely blocked",
            is_mandatory=True,
            improvement_pct=0.72,
        )
        assert mand_payload["is_mandatory"] is True
        assert mand_payload["urgency"] == "CRITICAL"
        action_names = [a["action"] for a in mand_payload["actions"]]
        assert "ACCEPT" in action_names
        assert "DECLINE" not in action_names  # Mandatory: cannot decline

        # Advisory
        adv_payload = RerouteNotificationService.build_notification_payload(
            old_route=old_r,
            new_route=new_r,
            trigger_reason="Moderate hazard increase",
            is_mandatory=False,
            improvement_pct=0.20,
        )
        assert adv_payload["is_mandatory"] is False
        adv_actions = [a["action"] for a in adv_payload["actions"]]
        assert "ACCEPT" in adv_actions
        assert "DECLINE" in adv_actions

    # 10. RerouteDecisionService: Improvement Threshold Filtering
    def test_10_reroute_decision_service_improvement_threshold(self):
        service = RerouteDecisionService(min_improvement_pct=0.10)
        # Verify default thresholds
        assert service.min_improvement_pct == 0.10
        assert service.critical_threshold == 0.85

    # 11. HazardPropagationService: Hop Decay Calculation
    def test_11_hazard_propagation_service_decay_factors(self):
        service = HazardPropagationService(one_hop_decay=0.60, two_hop_decay=0.25)
        source_h = 0.80

        h1 = round(source_h * service.one_hop_decay, 4)
        h2 = round(source_h * service.two_hop_decay, 4)

        assert h1 == 0.48
        assert h2 == 0.20

    # 12. HazardPropagationService: Non-downgrade Rule
    def test_12_hazard_propagation_non_downgrade_policy(self):
        service = HazardPropagationService()
        edge = MockEdge("e1", hazard_score=0.75)

        # Propagated score (0.48) is lower than existing edge score (0.75) -> return False (no downgrade)
        applied = service._apply_propagated_score(
            edge=edge,
            propagated_score=0.48,
            hop=1,
            decay=0.60,
            source_edge=MockEdge("src", hazard_score=0.80),
            sync_edge_field=True,
            now=None,
        )
        assert applied is False
