"""
SIH26002 — Freight Load Consolidation Service.

Evaluates grouping compatible cargo shipments with common origins, destinations,
and handling classes to optimize vehicle utilization, reduce ton-km fuel burn,
and lower logistics costs.
"""
from typing import Any, Dict, List, Tuple
from apps.fleet.models import CargoStatus, CargoType, FreightLoad
from apps.fleet.services.matching_engine import haversine_km


class LoadConsolidationEngine:
    """
    Identifies bundle opportunities between active freight loads.
    """

    MAX_ORIGIN_PROXIMITY_KM = 35.0
    MAX_DEST_PROXIMITY_KM = 35.0

    # Incompatible cargo matrices: cannot ship together in the same vehicle bay
    INCOMPATIBLE_PAIRS = [
        {CargoType.HAZMAT, CargoType.PERISHABLE},
        {CargoType.HAZMAT, CargoType.COLD_CHAIN},
        {CargoType.HAZMAT, CargoType.EMERGENCY_AID},
        {CargoType.BULK, CargoType.FRAGILE},
    ]

    @classmethod
    def are_cargo_types_compatible(cls, type_a: str, type_b: str) -> bool:
        """Returns True if two cargo classes can be legally co-loaded."""
        if type_a == type_b:
            return True
        for pair in cls.INCOMPATIBLE_PAIRS:
            if type_a in pair and type_b in pair:
                return False
        return True

    @classmethod
    def evaluate_consolidation_pair(
        cls, load_a: FreightLoad, load_b: FreightLoad, vehicle_capacity_kg: float = 14000.0
    ) -> Dict[str, Any]:
        """
        Evaluates pairing two loads into a consolidated multi-stop shipment.
        """
        if load_a.id == load_b.id:
            return {"can_consolidate": False, "reason": "Identical load"}

        # 1. Cargo Compatibility Check
        if not cls.are_cargo_types_compatible(load_a.cargo_type, load_b.cargo_type):
            return {
                "can_consolidate": False,
                "reason": f"Incompatible cargo classes: cannot co-load {load_a.get_cargo_type_display()} with {load_b.get_cargo_type_display()}.",
                "constraints": ["CARGO_CLASS_CONFLICT"],
            }

        # 2. Origin Proximity Check
        a_orig_lat = load_a.origin_node.geometry.y if load_a.origin_node.geometry else 26.14
        a_orig_lon = load_a.origin_node.geometry.x if load_a.origin_node.geometry else 91.73
        b_orig_lat = load_b.origin_node.geometry.y if load_b.origin_node.geometry else 26.14
        b_orig_lon = load_b.origin_node.geometry.x if load_b.origin_node.geometry else 91.73

        origin_dist_km = haversine_km(a_orig_lat, a_orig_lon, b_orig_lat, b_orig_lon)
        if origin_dist_km > cls.MAX_ORIGIN_PROXIMITY_KM:
            return {
                "can_consolidate": False,
                "reason": f"Pickup origins are too far apart ({origin_dist_km:.1f} km > {cls.MAX_ORIGIN_PROXIMITY_KM} km).",
                "constraints": ["ORIGIN_PROXIMITY_EXCEEDED"],
            }

        # 3. Destination Proximity Check
        a_dst_lat = load_a.destination_node.geometry.y if load_a.destination_node.geometry else 25.57
        a_dst_lon = load_a.destination_node.geometry.x if load_a.destination_node.geometry else 91.89
        b_dst_lat = load_b.destination_node.geometry.y if load_b.destination_node.geometry else 25.57
        b_dst_lon = load_b.destination_node.geometry.x if load_b.destination_node.geometry else 91.89

        dest_dist_km = haversine_km(a_dst_lat, a_dst_lon, b_dst_lat, b_dst_lon)
        if dest_dist_km > cls.MAX_DEST_PROXIMITY_KM:
            return {
                "can_consolidate": False,
                "reason": f"Delivery destinations are too far apart ({dest_dist_km:.1f} km > {cls.MAX_DEST_PROXIMITY_KM} km).",
                "constraints": ["DEST_PROXIMITY_EXCEEDED"],
            }

        # 4. Combined Weight & Volume Check
        comb_weight = float(load_a.weight_kg) + float(load_b.weight_kg)
        if comb_weight > vehicle_capacity_kg:
            return {
                "can_consolidate": False,
                "reason": f"Combined weight ({comb_weight:.0f} kg) exceeds vehicle payload limit ({vehicle_capacity_kg:.0f} kg).",
                "constraints": ["CAPACITY_OVERLOAD"],
            }

        comb_volume = (float(load_a.volume_cbm or 0.0)) + (float(load_b.volume_cbm or 0.0))

        # 5. Estimated Logistics Savings & Detour Delay
        # Baseline: two separate trips of ~100 km cost ~2x INR 12,000 = INR 24,000
        # Consolidated: one trip + origin pickup detour + dest delivery detour
        detour_km = origin_dist_km + dest_dist_km
        detour_delay_min = round((detour_km / 35.0) * 60.0, 1)  # 35 km/h local pickup speed

        # Estimated cost savings: ~30% to 40% reduction in total trip expenditure
        estimated_savings_inr = round(max(1500.0, comb_weight * 1.85 - (detour_km * 45.0)), 2)

        return {
            "can_consolidate": True,
            "load_ids": [str(load_a.id), str(load_b.id)],
            "combined_weight_kg": comb_weight,
            "combined_volume_cbm": round(comb_volume, 2),
            "pickup_detour_km": round(origin_dist_km, 1),
            "delivery_detour_km": round(dest_dist_km, 1),
            "total_detour_km": round(detour_km, 1),
            "additional_delay_min": detour_delay_min,
            "estimated_savings_inr": estimated_savings_inr,
            "route_compatibility": "HIGH",
            "is_estimate": True,
        }

    @classmethod
    def find_all_consolidations(cls) -> List[Dict[str, Any]]:
        """
        Scans all AVAILABLE loads and returns valid consolidation bundles.
        """
        available_loads = list(
            FreightLoad.objects.filter(status__in=[CargoStatus.CREATED, CargoStatus.AVAILABLE])
            .select_related("origin_node", "destination_node")
        )
        opportunities = []
        for i in range(len(available_loads)):
            for j in range(i + 1, len(available_loads)):
                res = cls.evaluate_consolidation_pair(available_loads[i], available_loads[j])
                if res.get("can_consolidate"):
                    opportunities.append(res)
        return opportunities
