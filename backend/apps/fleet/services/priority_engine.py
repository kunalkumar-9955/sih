"""
SIH26002 — Deterministic Freight Priority Engine.

Computes explainable, reproducible priority scores (0–100) for cargo demands
taking into account perishability, delivery urgency, hazard exposure, and active disaster states.
"""
from typing import Any, Dict
from django.utils import timezone

from apps.fleet.models import CargoPriority, CargoType, DisasterFleetModeState, FreightLoad


class DeterministicPriorityEngine:
    """
    Evaluates urgency and logistical precedence for dispatch and matching queues.
    """

    @classmethod
    def calculate_load_priority(cls, load: FreightLoad) -> Dict[str, Any]:
        """
        Computes the priority score (0–100) and contributing factors.
        """
        score = 0.0
        factors = []

        # 1. Base Cargo Priority (Max 40 pts)
        priority_weights = {
            CargoPriority.EMERGENCY: 40.0,
            CargoPriority.URGENT: 30.0,
            CargoPriority.HIGH: 20.0,
            CargoPriority.NORMAL: 10.0,
            CargoPriority.LOW: 0.0,
        }
        p_val = priority_weights.get(load.priority, 10.0)
        score += p_val
        factors.append(f"Cargo Priority: {load.get_priority_display()} (+{p_val:.0f} pts)")

        # 2. Perishability & Cold Chain (Max 25 pts)
        if load.is_perishable or load.cargo_type in [CargoType.PERISHABLE, CargoType.COLD_CHAIN]:
            score += 25.0
            factors.append("Perishable / Temperature Sensitive (+25 pts)")
        elif load.cargo_type == CargoType.EMERGENCY_AID:
            score += 25.0
            factors.append("Disaster Relief Supplies (+25 pts)")

        # 3. Delivery Urgency & Deadline Proximity (Max 20 pts)
        deadline = load.required_delivery_time or load.delivery_window_end
        if deadline:
            now = timezone.now()
            hours_remaining = (deadline - now).total_seconds() / 3600.0
            if hours_remaining <= 4.0:
                score += 20.0
                factors.append("Imminent Delivery Deadline <4h (+20 pts)")
            elif hours_remaining <= 12.0:
                score += 15.0
                factors.append("Tight Delivery Deadline <12h (+15 pts)")
            elif hours_remaining <= 24.0:
                score += 10.0
                factors.append("Delivery Required Within 24h (+10 pts)")
            else:
                score += 5.0
                factors.append("Standard Multi-Day Delivery (+5 pts)")

        # 4. Disaster Mode Escalation (Max 15 pts)
        disaster_state = DisasterFleetModeState.get_current()
        if disaster_state.is_disaster_mode:
            if load.priority in [CargoPriority.EMERGENCY, CargoPriority.URGENT] or load.cargo_type in [
                CargoType.EMERGENCY_AID,
                CargoType.COLD_CHAIN,
            ]:
                score += 15.0
                factors.append("Disaster Response Escalation Active (+15 pts)")
            else:
                factors.append("Commercial Load Deferred during Disaster Response (0 pts)")

        final_score = min(100.0, max(0.0, score))

        # Classification
        if final_score >= 65.0:
            level = "CRITICAL_URGENT"
        elif final_score >= 45.0:
            level = "HIGH_PRIORITY"
        elif final_score >= 25.0:
            level = "STANDARD"
        else:
            level = "LOW_DEFERRED"

        return {
            "priority_score": round(final_score, 1),
            "priority_level": level,
            "is_disaster_mode_active": disaster_state.is_disaster_mode,
            "contributing_factors": factors,
            "explanation": " | ".join(factors),
        }
