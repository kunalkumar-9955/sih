"""
SIH26002 — Logistics Cost Optimization & Breakdown Service.

Computes explainable, deterministic cost estimates for freight movements
across North Eastern Region mountain roads, rail sidings, and NW-2 river terminals.
All numbers are transparently tagged as estimates.
"""
from typing import Any, Dict
from apps.vehicles.models import Vehicle


class LogisticsCostOptimizer:
    """
    Computes itemized logistics operational cost estimates.
    """

    # Baseline NER economic parameters (2026 average)
    DIESEL_PRICE_PER_LITER = 92.50  # INR / L
    TOLL_RATE_PER_KM = 1.65         # INR / km on National Highways
    CHECKPOST_FEE_INR = 250.0       # Base state entry and forest checkpost fee
    TRANSFER_HANDLING_INR = 1200.0  # Intermodal freight transfer & stevedoring fee
    CREW_COST_PER_KM = 3.50         # Crew and vehicle maintenance allocation per km

    @classmethod
    def estimate_trip_cost(
        cls,
        distance_km: float,
        vehicle: Vehicle,
        transfers_count: int = 0,
        average_hazard_index: float = 0.10,
    ) -> Dict[str, Any]:
        """
        Calculates itemized estimated cost for a given distance and vehicle.
        """
        distance = max(1.0, float(distance_km))
        eff_kmpl = max(1.5, float(getattr(vehicle, "fuel_efficiency_kmpl", 4.5) or 4.5))

        # 1. Fuel Cost
        fuel_liters = distance / eff_kmpl
        fuel_cost = fuel_liters * cls.DIESEL_PRICE_PER_LITER

        # 2. Toll & Checkpost Costs
        toll_cost = distance * cls.TOLL_RATE_PER_KM
        checkpost_cost = cls.CHECKPOST_FEE_INR if distance > 40.0 else 0.0

        # 3. Crew & Fleet Maintenance Allocation
        crew_maintenance = distance * cls.CREW_COST_PER_KM

        # 4. Intermodal Transfer Fees
        transfer_cost = float(transfers_count) * cls.TRANSFER_HANDLING_INR

        # Base Operational Subtotal
        base_subtotal = fuel_cost + toll_cost + checkpost_cost + crew_maintenance + transfer_cost

        # 5. Geohazard Risk & Insurance Surcharge
        # High monsoon or landslide risk segments incur detour/standby risk cost
        hazard_risk_surcharge = 0.0
        if average_hazard_index > 0.50:
            surcharge_rate = (average_hazard_index - 0.50) * 0.40  # up to 20% surcharge
            hazard_risk_surcharge = base_subtotal * surcharge_rate

        total_estimated_cost = round(base_subtotal + hazard_risk_surcharge, 2)

        return {
            "total_estimated_cost_inr": total_estimated_cost,
            "cost_per_km": round(total_estimated_cost / distance, 2),
            "breakdown": {
                "fuel_cost_inr": round(fuel_cost, 2),
                "estimated_fuel_liters": round(fuel_liters, 2),
                "fuel_efficiency_kmpl": eff_kmpl,
                "toll_cost_inr": round(toll_cost, 2),
                "checkpost_fees_inr": round(checkpost_cost, 2),
                "crew_and_maintenance_inr": round(crew_maintenance, 2),
                "transfer_handling_inr": round(transfer_cost, 2),
                "hazard_risk_surcharge_inr": round(hazard_risk_surcharge, 2),
            },
            "is_estimate": True,
            "disclaimer": "Cost estimate based on NER regional fuel norms, distance, and transfer penalties; actual costs may vary.",
        }
