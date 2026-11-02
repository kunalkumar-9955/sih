"""
SIH26002 — Disaster Fleet Mode Service.

Coordinates system-wide transition between NORMAL_OPERATIONS and DISASTER_RESPONSE.
During disaster response, emergency medical aid and relief supplies receive priority
over commercial freight, and high-hazard mountain corridors are restricted.
"""
from typing import Any, Dict, List, Optional
from django.utils import timezone
from apps.fleet.models import DisasterFleetModeState


class DisasterFleetModeService:
    """
    Controls platform disaster response escalation state.
    """

    @classmethod
    def get_current_state(cls) -> Dict[str, Any]:
        """Returns the current operational mode and metadata."""
        state = DisasterFleetModeState.get_current()
        return {
            "is_disaster_mode": state.is_disaster_mode,
            "mode": "DISASTER_RESPONSE" if state.is_disaster_mode else "NORMAL_OPERATIONS",
            "activated_at": state.activated_at.isoformat() if state.activated_at else None,
            "activated_by": state.activated_by,
            "affected_corridors": state.affected_corridors,
            "notes": state.notes,
        }

    @classmethod
    def activate_disaster_mode(
        cls,
        activated_by: str = "DISASTER_COORDINATOR",
        affected_corridors: Optional[List[str]] = None,
        notes: str = "Severe weather / landslide escalation protocol activated.",
    ) -> Dict[str, Any]:
        """
        Activates disaster response mode.
        """
        state = DisasterFleetModeState.get_current()
        state.is_disaster_mode = True
        state.activated_at = timezone.now()
        state.activated_by = activated_by
        state.affected_corridors = affected_corridors or ["NH-6_SHILLONG_CORRIDOR", "BARAK_VALLEY_PASS"]
        state.notes = notes
        state.save()

        return {
            "status": "ACTIVATED",
            "mode": "DISASTER_RESPONSE",
            "activated_at": state.activated_at.isoformat(),
            "activated_by": state.activated_by,
            "affected_corridors": state.affected_corridors,
            "operational_directives": [
                "Prioritize EMERGENCY and URGENT medical/relief freight over commercial cargo",
                "Route planner enforces strict safety-first heuristics",
                "Pre-position available vehicles near designated relief staging depots",
                "Real-time monitoring of driver SOS distress beacons elevated to highest priority",
            ],
            "notes": state.notes,
        }

    @classmethod
    def reset_to_normal_operations(cls, reset_by: str = "OPERATOR") -> Dict[str, Any]:
        """
        Restores standard commercial and multimodal logistics operations.
        """
        state = DisasterFleetModeState.get_current()
        state.is_disaster_mode = False
        state.activated_at = None
        state.activated_by = ""
        state.affected_corridors = []
        state.notes = f"Reset to normal operations by {reset_by}."
        state.save()

        return {
            "status": "RESET",
            "mode": "NORMAL_OPERATIONS",
            "message": "Platform restored to standard commercial fleet scheduling and routing.",
        }
