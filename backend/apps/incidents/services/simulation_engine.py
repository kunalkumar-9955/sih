"""
SIH26002 — Network Disruption Simulation Engine.

Simulates extreme environmental events, natural hazards, and infrastructure
failures across the North Eastern Region multimodal network without mutating
production database records.
"""
import copy
import logging
import uuid
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.fleet.models import FreightLoad
from apps.incidents.models import DisruptionSimulationRun, ScenarioType, SimulationImpact
from apps.routing.models import Route
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.transport_graph.services.accessibility import AccessibilityIntelligenceService
from apps.vehicles.models import Vehicle

logger = logging.getLogger("sih.incidents.simulation")


class DisruptionSimulationEngine:
    """
    Simulates network-wide disruption scenarios and calculates resilience deltas.
    """

    @classmethod
    def run_scenario(
        cls,
        scenario_type: str,
        target_corridor: str = "",
        target_state: str = "",
        custom_parameters: Optional[Dict[str, Any]] = None,
        persist: bool = True,
        operator_user: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes a named disruption scenario and computes impact metrics.
        """
        params = custom_parameters or {}

        # 1. Baseline Accessibility Score
        base_access = AccessibilityIntelligenceService.evaluate_corridor_accessibility(region="NER_CORRIDOR")
        pre_score = float(base_access.get("composite_accessibility_score", 84.5))

        # 2. Identify Target Edges to Disrupt
        edges_pool = list(TransportEdge.objects.select_related("source_node", "target_node").all())
        affected_edges: List[TransportEdge] = []
        affected_nodes_ids = set()
        impact_records: List[Dict[str, Any]] = []

        scenario_name = f"Scenario: {scenario_type}"

        if scenario_type == ScenarioType.LANDSLIDE:
            scenario_name = "Major Landslide Corridor Blockage (NH-6 Meghalaya Sector)"
            # Find edges in hill sectors or matching NH-6 / Shillong / Silchar
            for e in edges_pool:
                road_str = (e.road_name or "").upper()
                node_names = f"{e.source_node.name} {e.target_node.name}".upper()
                if "NH-6" in road_str or "SHILLONG" in node_names or "SILCHAR" in node_names or e.hazard_score >= 0.35:
                    affected_edges.append(e)
                    affected_nodes_ids.add(str(e.source_node_id))
                    affected_nodes_ids.add(str(e.target_node_id))
                    impact_records.append({
                        "entity_type": "EDGE",
                        "entity_id": str(e.id),
                        "entity_name": f"{e.source_node.name} → {e.target_node.name} ({e.road_name or 'Hwy'})",
                        "impact_type": "BLOCKED" if len(affected_edges) <= 2 else "RESTRICTED",
                        "hazard_score_delta": 0.55,
                        "delay_added_min": 180.0,
                        "notes": "Debris flow on mountain slope; carriageway impassable for heavy trucks.",
                    })
                    if len(affected_edges) >= 6:
                        break

        elif scenario_type == ScenarioType.HEAVY_RAINFALL:
            scenario_name = "Monsoon Heavy Rainfall (IMD Red Alert — Meghalaya/Assam)"
            rain_mm = float(params.get("rainfall_mm", 65.0))
            for e in edges_pool:
                if e.normalized_mode == TransportMode.ROAD:
                    affected_edges.append(e)
                    affected_nodes_ids.add(str(e.source_node_id))
                    affected_nodes_ids.add(str(e.target_node_id))
                    impact_records.append({
                        "entity_type": "EDGE",
                        "entity_id": str(e.id),
                        "entity_name": f"{e.source_node.name} → {e.target_node.name}",
                        "impact_type": "DELAYED",
                        "hazard_score_delta": 0.30,
                        "delay_added_min": 45.0,
                        "notes": f"Heavy precipitation ({rain_mm:.0f}mm); waterlogging and surface mud reduce average convoy speed.",
                    })
                    if len(affected_edges) >= 12:
                        break

        elif scenario_type == ScenarioType.FLOOD:
            scenario_name = "Brahmaputra Basin Flood (Assam Lowlands Inundation)"
            for e in edges_pool:
                node_names = f"{e.source_node.name} {e.target_node.name}".upper()
                if "GUWAHATI" in node_names or "DHUBRI" in node_names or "JORHAT" in node_names or e.is_waterway:
                    affected_edges.append(e)
                    affected_nodes_ids.add(str(e.source_node_id))
                    affected_nodes_ids.add(str(e.target_node_id))
                    impact_records.append({
                        "entity_type": "EDGE",
                        "entity_id": str(e.id),
                        "entity_name": f"{e.source_node.name} → {e.target_node.name}",
                        "impact_type": "BLOCKED" if e.normalized_mode == TransportMode.ROAD else "RESTRICTED",
                        "hazard_score_delta": 0.65,
                        "delay_added_min": 240.0,
                        "notes": "River embankment breach; road approaches submerged under 1.2m water.",
                    })
                    if len(affected_edges) >= 8:
                        break

        elif scenario_type == ScenarioType.TERMINAL_OUTAGE:
            scenario_name = "Guwahati Multimodal Terminal Operational Shutdown"
            for e in edges_pool:
                if e.normalized_mode == TransportMode.TRANSFER or "GUWAHATI" in e.source_node.name.upper():
                    affected_edges.append(e)
                    affected_nodes_ids.add(str(e.source_node_id))
                    affected_nodes_ids.add(str(e.target_node_id))
                    impact_records.append({
                        "entity_type": "TERMINAL",
                        "entity_id": str(e.source_node_id),
                        "entity_name": e.source_node.name,
                        "impact_type": "ISOLATED",
                        "hazard_score_delta": 0.0,
                        "delay_added_min": 360.0,
                        "notes": "Gantry crane failure and rail yard signal maintenance.",
                    })
                    if len(affected_edges) >= 4:
                        break

        elif scenario_type == ScenarioType.CRITICAL_CORRIDOR:
            scenario_name = "Multi-Hazard Simultaneous Critical Corridor Blockage (NH-6 + NH-27)"
            # Combination of heavy rain + road blockage
            for e in edges_pool[:10]:
                affected_edges.append(e)
                affected_nodes_ids.add(str(e.source_node_id))
                affected_nodes_ids.add(str(e.target_node_id))
                impact_records.append({
                    "entity_type": "EDGE",
                    "entity_id": str(e.id),
                    "entity_name": f"{e.source_node.name} → {e.target_node.name}",
                    "impact_type": "BLOCKED",
                    "hazard_score_delta": 0.75,
                    "delay_added_min": 300.0,
                    "notes": "Simultaneous flash flood and hillside collapse.",
                })

        else:
            # NORMAL baseline scenario
            scenario_name = "Normal Baseline Operational State"
            affected_edges = []
            affected_nodes_ids = set()

        # 3. Calculate Impacted Shipments and Vehicles
        affected_edge_ids_set = set(str(e.id) for e in affected_edges)
        impacted_shipments_count = 0
        impacted_vehicles_count = 0

        active_loads = FreightLoad.objects.filter(status__in=["MATCHED", "IN_TRANSIT", "AVAILABLE"])
        for load in active_loads:
            # Check if origin or destination touches affected nodes
            if str(load.origin_node_id) in affected_nodes_ids or str(load.destination_node_id) in affected_nodes_ids:
                impacted_shipments_count += 1
                if load.assigned_vehicle_id:
                    impacted_vehicles_count += 1

        # 4. Compute Post-Disruption Accessibility & Redundancy Delta
        disruption_factor = min(0.60, (len(affected_edges) * 0.05) + (len(affected_nodes_ids) * 0.03))
        post_score = round(max(20.0, pre_score * (1.0 - disruption_factor)), 1)
        access_delta_pct = round(((post_score - pre_score) / max(1.0, pre_score)) * 100.0, 1)

        redundancy_before = 88.0
        # Redundancy degrades when multimodal transfers are compromised
        redundancy_after = round(max(35.0, redundancy_before * (1.0 - (disruption_factor * 0.8))), 1)
        redundancy_delta_pct = round(((redundancy_after - redundancy_before) / redundancy_before) * 100.0, 1)

        est_delay_hours = round(sum(i["delay_added_min"] for i in impact_records) / 60.0, 1) if impact_records else 0.0
        alternative_routes_count = max(1, 4 - min(3, len(affected_edges) // 3))

        # 5. Formulate Prioritized Recovery Recommendations
        recovery_actions = []
        if len(affected_edges) > 0:
            recovery_actions.append("Divert inter-state freight through NF Railway Lumding-Badarpur corridor.")
            recovery_actions.append("Prioritize Border Roads Organisation (BRO) emergency clearing teams to key landslide sectors.")
            recovery_actions.append("Mobilize National Waterway 2 (NW-2) Ro-Ro barges between Dhubri and Pandu for heavy truck bypass.")
            recovery_actions.append("Alert state disaster management authorities (SDMA) and broadcast automated IVR warnings to in-transit drivers.")
        else:
            recovery_actions.append("Network operating at normal parameters. Maintain scheduled preventive road maintenance.")

        impact_summary = {
            "scenario": scenario_type,
            "corridor": target_corridor or "NER_REGIONAL_NETWORK",
            "state": target_state or "MULTIPLE_STATES",
            "critical_bottlenecks": [i["entity_name"] for i in impact_records[:4]],
            "modal_divergence_available": alternative_routes_count > 1,
        }

        # 6. Persist Simulation Run to Database
        sim_run_id = None
        if persist:
            with transaction.atomic():
                run_obj = DisruptionSimulationRun.objects.create(
                    scenario_name=scenario_name,
                    scenario_type=scenario_type,
                    severity_level="CRITICAL" if disruption_factor > 0.35 else ("HIGH" if disruption_factor > 0.15 else "LOW"),
                    target_corridor=target_corridor,
                    target_state=target_state,
                    parameters=params,
                    affected_edges_count=len(affected_edges),
                    affected_nodes_count=len(affected_nodes_ids),
                    impacted_shipments_count=impacted_shipments_count,
                    impacted_vehicles_count=impacted_vehicles_count,
                    pre_disruption_accessibility_score=pre_score,
                    post_disruption_accessibility_score=post_score,
                    accessibility_delta_pct=access_delta_pct,
                    multimodal_redundancy_before=redundancy_before,
                    multimodal_redundancy_after=redundancy_after,
                    redundancy_delta_pct=redundancy_delta_pct,
                    estimated_network_delay_hours=est_delay_hours,
                    alternative_routes_available=alternative_routes_count,
                    impact_summary=impact_summary,
                    recovery_recommendations=recovery_actions,
                    is_simulation=True,
                    executed_by=operator_user,
                )
                sim_run_id = str(run_obj.id)

                for rec in impact_records:
                    SimulationImpact.objects.create(
                        simulation=run_obj,
                        entity_type=rec["entity_type"],
                        entity_id=rec["entity_id"],
                        entity_name=rec["entity_name"],
                        impact_type=rec["impact_type"],
                        hazard_score_delta=rec["hazard_score_delta"],
                        delay_added_min=rec["delay_added_min"],
                        notes=rec["notes"],
                    )

        return {
            "success": True,
            "simulation_id": sim_run_id,
            "scenario_name": scenario_name,
            "scenario_type": scenario_type,
            "is_simulation": True,
            "data_source": "SIMULATION",
            "impact_metrics": {
                "affected_edges_count": len(affected_edges),
                "affected_nodes_count": len(affected_nodes_ids),
                "impacted_shipments_count": impacted_shipments_count,
                "impacted_vehicles_count": impacted_vehicles_count,
                "estimated_delay_hours": est_delay_hours,
                "alternative_routes_available": alternative_routes_count,
            },
            "resilience_delta": {
                "pre_disruption_accessibility": pre_score,
                "post_disruption_accessibility": post_score,
                "accessibility_delta_pct": access_delta_pct,
                "multimodal_redundancy_before": redundancy_before,
                "multimodal_redundancy_after": redundancy_after,
                "redundancy_delta_pct": redundancy_delta_pct,
            },
            "impact_details": impact_records[:10],
            "recovery_recommendations": recovery_actions,
            "impact_summary": impact_summary,
        }

    @classmethod
    def compare_scenarios(
        cls,
        scenario_types: List[str],
    ) -> Dict[str, Any]:
        """
        Runs and compares multiple scenarios side-by-side (e.g. NORMAL vs HEAVY_RAINFALL vs LANDSLIDE).
        """
        comparisons = []
        for s in scenario_types:
            res = cls.run_scenario(scenario_type=s, persist=False)
            comparisons.append({
                "scenario": s,
                "name": res["scenario_name"],
                "accessibility_score": res["resilience_delta"]["post_disruption_accessibility"],
                "accessibility_delta_pct": res["resilience_delta"]["accessibility_delta_pct"],
                "redundancy_score": res["resilience_delta"]["multimodal_redundancy_after"],
                "affected_edges": res["impact_metrics"]["affected_edges_count"],
                "impacted_shipments": res["impact_metrics"]["impacted_shipments_count"],
                "estimated_delay_hours": res["impact_metrics"]["estimated_delay_hours"],
            })

        return {
            "success": True,
            "scenarios_compared_count": len(comparisons),
            "comparisons": comparisons,
            "is_simulation": True,
            "data_source": "SIMULATION",
        }

    @classmethod
    def create_and_run_simulation(
        cls,
        title: str = "",
        scenario_type: str = ScenarioType.HEAVY_RAINFALL,
        rainfall_intensity_mm: float = 0.0,
        target_corridor: str = "",
        notes: str = "",
        operator_user: Optional[Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        params = kwargs.copy()
        if rainfall_intensity_mm > 0:
            params["rainfall_intensity_mm"] = rainfall_intensity_mm
        if notes:
            params["notes"] = notes
        res = cls.run_scenario(
            scenario_type=scenario_type,
            target_corridor=target_corridor,
            custom_parameters=params,
            persist=True,
            operator_user=operator_user,
        )
        metrics = res.get("impact_metrics", {})
        delta = res.get("resilience_delta", {})
        res["impact"] = {
            "affected_edges_count": metrics.get("affected_edges_count", 0),
            "severity_score": round(abs(delta.get("accessibility_delta_pct", 15.0)) / 4.0, 1),
            "accessibility_after": delta.get("post_disruption_accessibility", 59.2),
            "accessibility_delta": round(delta.get("post_disruption_accessibility", 59.2) - delta.get("pre_disruption_accessibility", 88.5), 1),
        }
        return res
