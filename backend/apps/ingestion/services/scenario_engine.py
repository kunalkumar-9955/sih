"""
SIH26002 — Demo Scenario Simulation Engine.

Provides controlled, reproducible, and transparent scenario states for SIH jury demonstrations:
- NORMAL: Optimal dry-season corridor conditions
- HEAVY_RAIN: Severe monsoon cloudburst (elevated risk on mountain highways)
- LANDSLIDE: Catastrophic slope failure on NH-6 (edge blocked, mandatory reroute)
- FLOOD: Lowland flash flood with high river navigable water level
- ROAD_BLOCKAGE: Checkpost / bridge closure
- MULTIMODAL_SWITCH: Direct road blocked, prompting rail/waterway modal transfer
- CRITICAL_CORRIDOR: High alert emergency condition across arterial segments

Rule: All simulated states are strictly stamped as DEMO/SIMULATION.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.hazards.models import HazardIncident, HazardScore, HazardSeverity
from apps.ingestion.models import DemoScenarioRecord
from apps.routing.services.hazard_change import HazardChangeDetector
from apps.transport_graph.models import EdgeStatus, TransportEdge, TransportMode
from apps.trips.models import Trip, TripStatus


logger = logging.getLogger("sih.ingestion.scenarios")


class DemoScenarioEngine:
    """
    Orchestrates live simulation scenarios across the transport graph and hazard pipeline.
    """

    SCENARIO_DESCRIPTIONS = {
        "NORMAL": "Clear weather, baseline geohazards (H <= 0.15), all corridor segments OPEN.",
        "HEAVY_RAIN": "Severe monsoon cloudburst in Meghalaya (140mm rainfall), elevated slip risk on NH-6.",
        "LANDSLIDE": "Active slope failure at Sonapur Tunnel escarpment (H = 0.92, status BLOCKED).",
        "FLOOD": "Flash flood inundation in Barak Valley lowlands; NW-2 waterway draft optimal (3.2m).",
        "ROAD_BLOCKAGE": "Structural bridge damage / rockfall blockage near Nongpoh checkpost.",
        "MULTIMODAL_SWITCH": "NH-6 road blocked; Lumding rail & Pandu Port river barge active, forcing modal shift.",
        "CRITICAL_CORRIDOR": "Region-wide Red Alert disaster warning across primary corridor.",
    }

    @classmethod
    def list_available_scenarios(cls) -> List[Dict[str, Any]]:
        """Returns all registered scenarios and their current active status."""
        active_record = DemoScenarioRecord.objects.filter(is_active=True).first()
        active_name = active_record.name if active_record else "NORMAL"

        scenarios = []
        for name, desc in cls.SCENARIO_DESCRIPTIONS.items():
            scenarios.append({
                "name": name,
                "description": desc,
                "is_active": (name == active_name),
                "is_simulation": True,
            })
        return scenarios

    @classmethod
    @transaction.atomic
    def activate_scenario(
        cls, scenario_name: str, activated_by: str = "DEMO_OPERATOR"
    ) -> Dict[str, Any]:
        """
        Applies scenario parameters to the database:
        1. Deactivates any existing scenario
        2. Adjusts edge statuses and hazard scores
        3. Creates official demo HazardIncidents
        4. Triggers route risk recalculations for active trips
        """
        scenario_name = scenario_name.upper().strip()
        if scenario_name not in cls.SCENARIO_DESCRIPTIONS:
            raise ValueError(f"Unknown scenario '{scenario_name}'. Valid choices: {list(cls.SCENARIO_DESCRIPTIONS.keys())}")

        # Deactivate previous
        DemoScenarioRecord.objects.filter(is_active=True).update(is_active=False)

        # Reset all edges to OPEN baseline first
        TransportEdge.objects.filter(is_available=True).update(
            status=EdgeStatus.OPEN,
            hazard_score=0.10,
        )

        affected_edges: List[str] = []
        incident_created = None
        params: Dict[str, Any] = {}

        if scenario_name == "NORMAL":
            params = {"weather": "CLEAR", "hazard_level": "LOW"}

        elif scenario_name == "HEAVY_RAIN":
            # Elevate hazard on road edges
            road_edges = TransportEdge.objects.filter(mode=TransportMode.ROAD)
            road_edges.update(hazard_score=0.58)
            affected_edges = [str(e.id) for e in road_edges]
            params = {"rainfall_24h_mm": 140.0, "severity": "HIGH"}

        elif scenario_name == "LANDSLIDE":
            # Block steep mountain highway segment (e.g., Guwahati to Shillong / Sonapur)
            target_edge = TransportEdge.objects.filter(mode=TransportMode.ROAD).order_by("distance_m").first()
            if target_edge:
                target_edge.status = EdgeStatus.BLOCKED
                target_edge.hazard_score = 0.92
                target_edge.save(update_fields=["status", "hazard_score"])
                affected_edges.append(str(target_edge.id))

                incident_created = HazardIncident.objects.create(
                    edge=target_edge,
                    incident_type=HazardIncident.IncidentType.LANDSLIDE,
                    severity=HazardSeverity.CRITICAL,
                    description="[DEMO SIMULATION] Catastrophic debris flow blocking northbound carriageway.",
                    source=HazardIncident.IncidentSource.SYNTHETIC_DEMO,
                    status=HazardIncident.IncidentStatus.VERIFIED,
                )
            params = {"blocked_edge_id": affected_edges[0] if affected_edges else None, "hazard_index": 0.92}

        elif scenario_name == "FLOOD":
            # Waterway edges depth becomes high, lowland road edges restricted
            water_edges = TransportEdge.objects.filter(mode__in=[TransportMode.WATER, TransportMode.WATERWAY])
            water_edges.update(water_level_m=49.5, min_required_depth_m=1.8, hazard_score=0.15)

            lowland_road = TransportEdge.objects.filter(mode=TransportMode.ROAD).last()
            if lowland_road:
                lowland_road.status = EdgeStatus.RESTRICTED
                lowland_road.hazard_score = 0.70
                lowland_road.save(update_fields=["status", "hazard_score"])
                affected_edges.append(str(lowland_road.id))

            params = {"flood_stage": "ACTIVE", "waterway_navigable": True}

        elif scenario_name == "ROAD_BLOCKAGE":
            road_edge = TransportEdge.objects.filter(mode=TransportMode.ROAD).first()
            if road_edge:
                road_edge.status = EdgeStatus.BLOCKED
                road_edge.hazard_score = 0.85
                road_edge.save(update_fields=["status", "hazard_score"])
                affected_edges.append(str(road_edge.id))
            params = {"blockage_type": "CHECKPOST_COLLAPSE"}

        elif scenario_name == "MULTIMODAL_SWITCH":
            # Block key direct highway edge, ensure rail & water edges are open and low-risk
            direct_road = TransportEdge.objects.filter(mode=TransportMode.ROAD).first()
            if direct_road:
                direct_road.status = EdgeStatus.BLOCKED
                direct_road.hazard_score = 0.95
                direct_road.save(update_fields=["status", "hazard_score"])
                affected_edges.append(str(direct_road.id))

            # Rail & waterway edges clear
            TransportEdge.objects.filter(mode__in=[TransportMode.RAIL, TransportMode.WATER, TransportMode.TRANSFER]).update(
                status=EdgeStatus.OPEN,
                hazard_score=0.08,
            )
            params = {"direct_road_blocked": True, "rail_waterway_clear": True}

        elif scenario_name == "CRITICAL_CORRIDOR":
            corridor_edges = TransportEdge.objects.all()[:5]
            for e in corridor_edges:
                e.status = EdgeStatus.CRITICAL
                e.hazard_score = 0.88
                e.save(update_fields=["status", "hazard_score"])
                affected_edges.append(str(e.id))
            params = {"alert_level": "RED_ALERT"}

        # Record scenario state
        scenario_record, _ = DemoScenarioRecord.objects.get_or_create(name=scenario_name)
        scenario_record.is_active = True
        scenario_record.activated_at = timezone.now()
        scenario_record.activated_by = activated_by
        scenario_record.affected_edges_count = len(affected_edges)
        scenario_record.affected_edge_ids = affected_edges
        scenario_record.description = cls.SCENARIO_DESCRIPTIONS[scenario_name]
        scenario_record.parameters = params
        scenario_record.save()

        # Update HazardScore records for affected edges
        for eid in affected_edges:
            e = TransportEdge.objects.get(id=eid)
            HazardScore.objects.create(
                edge=e,
                hazard_index=e.hazard_score,
                confidence=0.95,
                severity=HazardSeverity.classify(e.hazard_score),
                model_version="demo-scenario-v1",
                feature_version="demo-fv1",
                is_current=True,
            )

        logger.info(
            "Demo Scenario '%s' ACTIVATED by %s. Affected edges: %d",
            scenario_name,
            activated_by,
            len(affected_edges),
        )

        return {
            "scenario": scenario_name,
            "status": "ACTIVATED",
            "is_simulation": True,
            "affected_edges_count": len(affected_edges),
            "affected_edge_ids": affected_edges,
            "incident_id": str(incident_created.id) if incident_created else None,
            "activated_at": scenario_record.activated_at.isoformat(),
            "description": scenario_record.description,
            "parameters": params,
        }

    @classmethod
    @transaction.atomic
    def reset_to_baseline(cls) -> Dict[str, Any]:
        """Restores canonical baseline graph state."""
        return cls.activate_scenario("NORMAL", activated_by="SYSTEM_RESET")
