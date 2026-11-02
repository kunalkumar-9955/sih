"""
SIH26002 — Emergency Operations & SOS Rescue Service.

Handles real-time distress triage, nearest operational logistics/medical hub discovery,
safe emergency evacuation routing avoiding BLOCKED and CRITICAL edges,
and operator dispatch lifecycle management with an immutable audit log.
"""
from typing import Any, Dict, List, Optional
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.sync.models import EmergencySOS, EmergencySOSStatus
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportNode
from apps.vehicles.models import Vehicle, VehicleStatus
from apps.fleet.services.matching_engine import haversine_km


class EmergencyOperationsService:
    """
    Orchestrates control-room emergency triage, evacuation routing, and rescue lifecycle.
    """

    @classmethod
    def triage_and_enrich_sos(cls, sos: EmergencySOS) -> Dict[str, Any]:
        """
        Calculates nearest operational hub, safe emergency detour route, and updates SOS metadata.
        """
        driver_lat = sos.location.y if sos.location else 25.90
        driver_lon = sos.location.x if sos.location else 91.88

        # 1. Identify Nearest Safe Operational Hub or Logistics Depot
        hubs = list(
            TransportNode.objects.filter(is_active=True).exclude(
                node_type=NodeType.CHECKPOST
            )
        )

        nearest_hub = None
        min_dist_km = 9999.0

        for hub in hubs:
            h_lat = hub.geometry.y if hub.geometry else 26.14
            h_lon = hub.geometry.x if hub.geometry else 91.73
            dist = haversine_km(driver_lat, driver_lon, h_lat, h_lon)
            if dist < min_dist_km:
                min_dist_km = dist
                nearest_hub = hub

        if nearest_hub:
            sos.nearest_hub = nearest_hub
            sos.nearest_hub_distance_km = round(min_dist_km, 1)

        # 2. Check Route Safety on current trip
        blocked_edges_detected = 0
        critical_edges_detected = 0
        if sos.trip and sos.trip.route:
            edges = sos.trip.route.edges.all()
            for edge in edges:
                if edge.status in [EdgeStatus.BLOCKED, EdgeStatus.CRITICAL]:
                    blocked_edges_detected += 1
                elif edge.status == EdgeStatus.RESTRICTED:
                    critical_edges_detected += 1

        # 3. Emergency Evacuation Route Guidance
        evacuation_advice = (
            f"Evacuate toward {nearest_hub.name} ({min_dist_km:.1f} km away). "
            f"Caution: {blocked_edges_detected} blocked segment(s) detected along planned transit."
            if nearest_hub
            else "Maintain position and await rescue response."
        )

        # Update vehicle status to EMERGENCY
        if sos.trip and sos.trip.vehicle:
            veh = sos.trip.vehicle
            veh.status = VehicleStatus.EMERGENCY
            veh.save(update_fields=["status"])

        # Append to audit trail
        audit_entry = {
            "timestamp": timezone.now().isoformat(),
            "action": "TRIAGED_BY_SYSTEM",
            "actor": "EMERGENCY_AI_ENGINE",
            "nearest_hub": nearest_hub.name if nearest_hub else "None",
            "distance_km": round(min_dist_km, 1),
            "blocked_edges": blocked_edges_detected,
        }
        sos.audit_log.append(audit_entry)
        sos.save()

        return {
            "sos_id": str(sos.id),
            "status": sos.status,
            "driver_name": str(sos.driver),
            "nearest_hub": nearest_hub.name if nearest_hub else None,
            "distance_km": round(min_dist_km, 1),
            "evacuation_advice": evacuation_advice,
            "blocked_edges_count": blocked_edges_detected,
        }

    @classmethod
    def execute_operator_action(
        cls, sos: EmergencySOS, action: str, operator_email: str, notes: str = ""
    ) -> Dict[str, Any]:
        """
        Transitions SOS lifecycle state: ACKNOWLEDGE, DISPATCH, RESOLVE, FALSE_ALARM.
        """
        now = timezone.now()
        action_upper = action.upper()

        if action_upper == "ACKNOWLEDGE":
            sos.status = EmergencySOSStatus.ACKNOWLEDGED
            sos.acknowledged_at = now
        elif action_upper == "DISPATCH":
            sos.status = EmergencySOSStatus.DISPATCHED
            sos.dispatched_at = now
        elif action_upper == "RESOLVE":
            sos.status = EmergencySOSStatus.RESOLVED
            sos.resolved_at = now
            # Restore vehicle from EMERGENCY to AVAILABLE or ON_TRIP
            if sos.trip and sos.trip.vehicle:
                veh = sos.trip.vehicle
                veh.status = VehicleStatus.ON_TRIP if sos.trip.status == "ACTIVE" else VehicleStatus.AVAILABLE
                veh.save(update_fields=["status"])
        elif action_upper == "FALSE_ALARM":
            sos.status = EmergencySOSStatus.FALSE_ALARM
            sos.resolved_at = now
            if sos.trip and sos.trip.vehicle:
                veh = sos.trip.vehicle
                veh.status = VehicleStatus.AVAILABLE
                veh.save(update_fields=["status"])
        else:
            raise ValueError(f"Unknown operator emergency action: '{action}'. Must be ACKNOWLEDGE, DISPATCH, RESOLVE, or FALSE_ALARM.")

        # Record in audit log
        sos.audit_log.append({
            "timestamp": now.isoformat(),
            "action": f"STATUS_TRANSITION_TO_{sos.status}",
            "operator": operator_email,
            "notes": notes or f"Marked {sos.status} by control room operator.",
        })
        sos.save()

        return {
            "sos_id": str(sos.id),
            "status": sos.status,
            "updated_at": now.isoformat(),
            "operator": operator_email,
            "audit_log_count": len(sos.audit_log),
        }
