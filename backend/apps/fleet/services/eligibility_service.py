"""
SIH26002 — Fleet Availability & Eligibility Engine.

Determines whether a candidate vehicle is legally, physically, and operationally
eligible to accept and transport a specific freight load.
"""
from typing import Any, Dict, List
from django.utils import timezone

from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType
from apps.fleet.models import CargoType, FreightLoad


class FleetAvailabilityEngine:
    """
    Validates physical and operational constraints before allowing matching.
    """

    @classmethod
    def evaluate_vehicle_eligibility(
        cls, vehicle: Vehicle, load: FreightLoad
    ) -> Dict[str, Any]:
        """
        Evaluates a vehicle against a load's requirements.
        Returns:
            {
                "eligible": bool,
                "reason": str,
                "constraints": list[str],
                "estimated_availability": str (ISO-8601)
            }
        """
        constraints: List[str] = []

        # 1. Operational Status Check
        if vehicle.status in [
            VehicleStatus.MAINTENANCE,
            VehicleStatus.EMERGENCY,
            VehicleStatus.OFFLINE,
            VehicleStatus.UNAVAILABLE,
            VehicleStatus.INACTIVE,
        ]:
            return {
                "eligible": False,
                "reason": f"Vehicle is currently {vehicle.get_status_display()} and cannot accept loads.",
                "constraints": [f"STATUS_{vehicle.status}"],
                "estimated_availability": None,
            }

        # If vehicle is ON_TRIP, check if it has an upcoming availability window
        now = timezone.now()
        if vehicle.status == VehicleStatus.ON_TRIP:
            if vehicle.availability_start and vehicle.availability_start > now:
                # Can be eligible only if pickup window is after availability_start
                if load.pickup_window_start and load.pickup_window_start < vehicle.availability_start:
                    return {
                        "eligible": False,
                        "reason": f"Vehicle is on trip until {vehicle.availability_start.strftime('%Y-%m-%d %H:%M')}, which is after requested pickup.",
                        "constraints": ["SCHEDULE_CONFLICT"],
                        "estimated_availability": vehicle.availability_start.isoformat(),
                    }
                constraints.append("CURRENTLY_ON_TRIP_QUEUED")
            else:
                return {
                    "eligible": False,
                    "reason": "Vehicle is currently executing an active trip without confirmed return availability.",
                    "constraints": ["BUSY_ON_TRIP"],
                    "estimated_availability": None,
                }

        # 2. Maintenance Status Check
        if vehicle.maintenance_status.upper() == "CRITICAL":
            return {
                "eligible": False,
                "reason": "Vehicle has a CRITICAL maintenance flag requiring immediate depot inspection.",
                "constraints": ["MAINTENANCE_CRITICAL"],
                "estimated_availability": None,
            }
        elif vehicle.maintenance_status.upper() == "DUE":
            constraints.append("MAINTENANCE_DUE_SOON")

        # 3. Payload Capacity (Weight)
        veh_cap = float(vehicle.capacity_kg or 0.0)
        req_weight = float(load.weight_kg or 0.0)
        if veh_cap < req_weight:
            return {
                "eligible": False,
                "reason": f"Vehicle payload capacity ({veh_cap:.0f} kg) is insufficient for cargo ({req_weight:.0f} kg).",
                "constraints": ["INSUFFICIENT_WEIGHT_CAPACITY"],
                "estimated_availability": None,
            }

        # 4. Volumetric Capacity
        if load.volume_cbm and vehicle.capacity_cbm:
            if float(vehicle.capacity_cbm) < float(load.volume_cbm):
                return {
                    "eligible": False,
                    "reason": f"Vehicle volumetric capacity ({float(vehicle.capacity_cbm):.1f} cbm) is insufficient for cargo ({float(load.volume_cbm):.1f} cbm).",
                    "constraints": ["INSUFFICIENT_VOLUME_CAPACITY"],
                    "estimated_availability": None,
                }

        # 5. Cargo Special Handling & Vehicle Compatibility
        if load.cargo_type == CargoType.HAZMAT:
            if vehicle.vehicle_type in [VehicleType.MINI_TRUCK, VehicleType.PICKUP]:
                return {
                    "eligible": False,
                    "reason": "Hazardous materials (HAZMAT) cannot be transported on Mini Trucks or Pickups per safety norms.",
                    "constraints": ["HAZMAT_VEHICLE_RESTRICTION"],
                    "estimated_availability": None,
                }
            constraints.append("HAZMAT_COMPLIANCE_REQUIRED")

        if load.cargo_type in [CargoType.COLD_CHAIN, CargoType.PERISHABLE]:
            if "REFRIGERATION_REQUIRED" in load.special_handling_requirements:
                # Check vehicle supported modes or specs
                if "REFRIGERATED" not in vehicle.supported_modes:
                    return {
                        "eligible": False,
                        "reason": "Cargo mandates active refrigeration, but vehicle does not have certified reefer equipment.",
                        "constraints": ["NO_REFRIGERATION_EQUIPMENT"],
                        "estimated_availability": None,
                    }

        if load.cargo_type == CargoType.BULK:
            if vehicle.vehicle_type not in [VehicleType.HEAVY_TRUCK, VehicleType.CONTAINER]:
                return {
                    "eligible": False,
                    "reason": "Heavy bulk cargo requires Heavy Trucks or Container carriers.",
                    "constraints": ["BULK_CARRIER_REQUIRED"],
                    "estimated_availability": None,
                }

        # 6. Operating Region
        if vehicle.operating_region and vehicle.operating_region != "NER_CORRIDOR":
            load_state = getattr(load.origin_node, "state", "")
            if load_state and vehicle.operating_region.lower() not in load_state.lower():
                constraints.append(f"CROSS_SECTOR_PERMIT_REQUIRED ({vehicle.operating_region})")

        est_avail = (
            vehicle.availability_start.isoformat()
            if vehicle.availability_start
            else now.isoformat()
        )

        return {
            "eligible": True,
            "reason": "Vehicle meets all payload, volume, cargo safety, and operational criteria.",
            "constraints": constraints,
            "estimated_availability": est_avail,
        }
