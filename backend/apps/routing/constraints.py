"""
SIH26002 — Vehicle & Operational Routing Constraints.

Evaluates cargo payload weight, vehicle mode compatibility,
waterway draft/depth requirements, and seasonal operational windows.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from apps.transport_graph.models import TransportEdge, TransportMode
from apps.vehicles.models import Vehicle, VehicleType


@dataclass
class VehicleContext:
    vehicle_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_capacity_kg: Optional[float] = None
    cargo_weight_kg: Optional[float] = None
    cargo_weight_tons: Optional[float] = None
    cargo_type: Optional[str] = None
    water_draft_m: Optional[float] = None
    draft_m: Optional[float] = None
    departure_time: Optional[datetime] = None
    avoid_modes: List[str] = None
    preferred_modes: List[str] = None
    allow_multimodal: bool = True
    max_hazard_threshold: Optional[float] = None

    def __post_init__(self):
        if self.cargo_weight_tons is not None and self.cargo_weight_kg is None:
            self.cargo_weight_kg = float(self.cargo_weight_tons) * 1000.0
        if self.draft_m is not None and self.water_draft_m is None:
            self.water_draft_m = float(self.draft_m)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VehicleContext":
        cargo_weight = data.get("cargo_weight") or data.get("cargo_weight_kg")
        if cargo_weight is not None:
            cargo_weight = float(cargo_weight)

        return cls(
            vehicle_id=data.get("vehicle_id"),
            vehicle_type=data.get("vehicle_type"),
            vehicle_capacity_kg=float(data["vehicle_capacity"]) if data.get("vehicle_capacity") else None,
            cargo_weight_kg=cargo_weight,
            cargo_type=data.get("cargo_type"),
            water_draft_m=float(data["water_draft_m"]) if data.get("water_draft_m") else None,
            departure_time=data.get("departure_time"),
            avoid_modes=[TransportMode.normalize(m) for m in data.get("avoid_modes", [])],
            preferred_modes=[TransportMode.normalize(m) for m in data.get("preferred_modes", [])],
            allow_multimodal=data.get("allow_multimodal", True),
            max_hazard_threshold=float(data["max_hazard_threshold"]) if data.get("max_hazard_threshold") is not None else None,
        )



class ConstraintChecker:
    """
    Evaluates whether an edge satisfies all operational, mode,
    and physical vehicle constraints.
    """

    def is_edge_traversable(
        self,
        edge: TransportEdge,
        context: Optional[VehicleContext],
    ) -> bool:
        """Convenience boolean check for edge traversability."""
        allowed, _ = self.is_edge_allowed(edge, context)
        return allowed

    def is_edge_allowed(
        self,
        edge: TransportEdge,
        context: Optional[VehicleContext],
    ) -> Tuple[bool, str]:
        """
        Returns (is_allowed: bool, rejection_reason: str).
        """
        if context is None:
            return True, ""

        norm_mode = edge.normalized_mode

        # 1. Mode Avoidance
        if context.avoid_modes and norm_mode in context.avoid_modes:
            return False, f"Mode '{norm_mode}' is explicitly in avoid_modes."

        # 2. Multimodal Permission
        if not context.allow_multimodal and norm_mode in (TransportMode.RAIL, TransportMode.WATER, TransportMode.TRANSFER):
            return False, "Multimodal intermodal switching is disabled for this route request."

        # 3. Cargo Payload vs Edge Capacity
        if context.cargo_weight_kg is not None and edge.capacity_kg is not None:
            if context.cargo_weight_kg > float(edge.capacity_kg):
                return False, (
                    f"Cargo weight ({context.cargo_weight_kg:.0f} kg) exceeds "
                    f"edge maximum capacity ({float(edge.capacity_kg):.0f} kg)."
                )

        # 4. Waterway Depth & Draft Constraints
        if edge.is_waterway:
            required_draft = context.water_draft_m or float(edge.draft_requirement_m or 1.5)
            if edge.min_required_depth_m is not None:
                if required_draft > float(edge.min_required_depth_m):
                    return False, (
                        f"Vessel draft requirement ({required_draft:.1f}m) exceeds "
                        f"minimum channel depth ({float(edge.min_required_depth_m):.1f}m)."
                    )
            if edge.water_level_m is not None:
                if float(edge.water_level_m) < required_draft:
                    return False, (
                        f"Current water level ({float(edge.water_level_m):.1f}m) is below "
                        f"navigable draft ({required_draft:.1f}m)."
                    )

        # 5. Seasonal Availability
        if context.departure_time and edge.seasonal_open_month and edge.seasonal_close_month:
            dep_month = context.departure_time.month
            open_m = edge.seasonal_open_month
            close_m = edge.seasonal_close_month

            if open_m <= close_m:
                is_open = open_m <= dep_month <= close_m
            else:
                # Wraps around year end (e.g. Nov to Feb)
                is_open = dep_month >= open_m or dep_month <= close_m

            if not is_open:
                return False, f"Edge is closed for season in month {dep_month} (Open: {open_m}–{close_m})."

        # 6. Operating Hours
        if context.departure_time and edge.operating_hours_start and edge.operating_hours_end:
            dep_time = context.departure_time.time()
            if edge.operating_hours_start <= edge.operating_hours_end:
                in_hours = edge.operating_hours_start <= dep_time <= edge.operating_hours_end
            else:
                in_hours = dep_time >= edge.operating_hours_start or dep_time <= edge.operating_hours_end
            if not in_hours:
                return False, f"Edge operates between {edge.operating_hours_start} and {edge.operating_hours_end}; departure time is outside window."

        # 7. Maximum Allowable Geohazard Threshold
        if context.max_hazard_threshold is not None:
            if float(edge.hazard_score) > float(context.max_hazard_threshold):
                return False, f"Edge hazard score ({edge.hazard_score:.2f}) exceeds maximum allowed risk ({context.max_hazard_threshold:.2f})."

        return True, ""
