"""
SIH26002 — Delivery Deadline Intelligence & Slack Time Service.

Evaluates delivery time windows, ETA feasibility, and deadline breach risks
considering real-time mountain terrain transit delays and geohazards.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from django.utils import timezone

from apps.fleet.models import FreightLoad


class DeadlineRiskStatus:
    ON_TIME = "ON_TIME"
    AT_RISK = "AT_RISK"
    LIKELY_LATE = "LIKELY_LATE"
    CRITICAL = "CRITICAL"


class DeliveryDeadlineIntelligence:
    """
    Computes delivery feasibility, ETA, buffer slack time, and risk category.
    """

    @classmethod
    def evaluate_deadline_risk(
        cls,
        load: FreightLoad,
        estimated_transit_time_min: float,
        departure_time: Optional[datetime] = None,
        is_route_blocked: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates delivery feasibility for a load and transit duration.
        """
        start_time = departure_time or timezone.now()
        transit_duration = max(5.0, float(estimated_transit_time_min))
        eta = start_time + timedelta(minutes=transit_duration)

        deadline = load.required_delivery_time or load.delivery_window_end

        if not deadline:
            return {
                "eta": eta.isoformat(),
                "deadline": None,
                "slack_time_min": 999.0,
                "status": DeadlineRiskStatus.ON_TIME,
                "compliance_score": 100.0,
                "recommendation": "No strict delivery deadline specified. On schedule.",
            }

        # Calculate slack buffer in minutes
        slack_seconds = (deadline - eta).total_seconds()
        slack_minutes = round(slack_seconds / 60.0, 1)

        # Severe route degradation override
        if is_route_blocked:
            return {
                "eta": eta.isoformat(),
                "deadline": deadline.isoformat(),
                "slack_time_min": slack_minutes,
                "status": DeadlineRiskStatus.CRITICAL,
                "compliance_score": 0.0,
                "recommendation": "CRITICAL: Route is blocked by geohazard. Delivery cannot be fulfilled on current route.",
            }

        # Classify risk
        if slack_minutes > 60.0:
            status = DeadlineRiskStatus.ON_TIME
            compliance_score = 100.0
            rec = f"Comfortable margin. {slack_minutes:.0f} minutes of buffer before deadline."
        elif 15.0 < slack_minutes <= 60.0:
            status = DeadlineRiskStatus.AT_RISK
            compliance_score = max(50.0, 50.0 + (slack_minutes / 60.0) * 45.0)
            rec = f"Tight margin. Only {slack_minutes:.0f} minutes buffer. Minimal delays permitted."
        elif 0.0 <= slack_minutes <= 15.0:
            status = DeadlineRiskStatus.LIKELY_LATE
            compliance_score = max(20.0, 20.0 + (slack_minutes / 15.0) * 25.0)
            rec = f"High probability of late delivery ({slack_minutes:.0f} min buffer). Recommend high-speed highway or express dispatch."
        else:
            status = DeadlineRiskStatus.CRITICAL
            compliance_score = 0.0
            rec = f"Delivery deadline will be missed by {abs(slack_minutes):.0f} minutes under standard transit conditions. Expedited rerouting required."

        return {
            "eta": eta.isoformat(),
            "deadline": deadline.isoformat(),
            "slack_time_min": slack_minutes,
            "status": status,
            "compliance_score": round(compliance_score, 1),
            "recommendation": rec,
        }
