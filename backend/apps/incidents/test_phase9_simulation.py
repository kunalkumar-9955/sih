"""
SIH26002 — Phase 9 Network Disruption Simulation Tests.
"""
import pytest
from apps.incidents.models import DisruptionSimulationRun, ScenarioType, SimulationImpact
from apps.incidents.services.simulation_engine import DisruptionSimulationEngine
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode


@pytest.mark.django_db
class TestPhase9DisruptionSimulation:
    @pytest.fixture(autouse=True)
    def setup_network_graph(self):
        self.node_a = TransportNode.objects.create(
            name="Guwahati Intermodal Terminal",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.73 26.18)",
            is_active=True,
        )
        self.node_b = TransportNode.objects.create(
            name="Shillong Pass",
            node_type=NodeType.LOCAL_HUB,
            geometry="POINT(91.89 25.57)",
            is_active=True,
        )
        self.edge = TransportEdge.objects.create(
            source_node=self.node_a,
            target_node=self.node_b,
            mode=TransportMode.ROAD,
            distance_m=95000,
            base_transit_time_min=150,
            road_name="NH-6",
            hazard_score=0.15,
            status=EdgeStatus.OPEN,
            is_available=True,
        )

    def test_simulation_does_not_mutate_live_database(self):
        initial_hazard = self.edge.hazard_score
        initial_status = self.edge.status

        res = DisruptionSimulationEngine.run_scenario(
            scenario_type=ScenarioType.LANDSLIDE,
            target_corridor="NH-6",
            persist=True,
        )

        assert res["success"] is True
        assert res["is_simulation"] is True
        assert res["data_source"] == "SIMULATION"

        # Verify live production TransportEdge was NOT mutated
        self.edge.refresh_from_db()
        assert self.edge.hazard_score == initial_hazard
        assert self.edge.status == initial_status

    def test_simulation_impact_metrics_and_resilience_deltas(self):
        res = DisruptionSimulationEngine.run_scenario(
            scenario_type=ScenarioType.HEAVY_RAINFALL,
            custom_parameters={"rainfall_intensity_mm": 120.0},
            persist=True,
        )

        assert res["success"] is True
        assert "impact_metrics" in res
        assert "resilience_delta" in res

        delta = res["resilience_delta"]
        assert "pre_disruption_accessibility" in delta
        assert "post_disruption_accessibility" in delta
        assert "accessibility_delta_pct" in delta

        # Verify simulation run was recorded
        sim_id = res["simulation_id"]
        sim_record = DisruptionSimulationRun.objects.get(id=sim_id)
        assert sim_record.is_simulation is True
        assert sim_record.scenario_type == ScenarioType.HEAVY_RAINFALL

    def test_scenario_comparison(self):
        comp = DisruptionSimulationEngine.compare_scenarios(
            scenario_types=[ScenarioType.NORMAL, ScenarioType.HEAVY_RAINFALL, ScenarioType.LANDSLIDE]
        )
        assert comp["success"] is True
        assert comp["scenarios_compared_count"] == 3
        assert len(comp["comparisons"]) == 3
        for c in comp["comparisons"]:
            assert "scenario" in c
            assert "accessibility_score" in c
            assert "affected_edges" in c
