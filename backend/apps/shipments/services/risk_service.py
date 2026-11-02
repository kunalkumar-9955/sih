"""
SIH26002 — End-to-End Shipment Risk Intelligence Engine.

Provides:
- Composite multi-factor shipment risk classification (LOW, MEDIUM, HIGH, CRITICAL)
- Aggregation across corridor geohazard, delivery deadline slack, cold-chain thermal variance, vehicle status, and checkpost discrepancies
- Explainable risk summaries for control room operators
"""
import logging
from typing import Dict, Any
from django.utils import timezone

from apps.shipments.models import DigitalShipmentDocument, ColdChainStatus, ShipmentRiskLevel
from apps.checkposts.models import VerificationResult

logger = logging.getLogger(__name__)


class ShipmentRiskEngine:
    """
    Synthesizes multiple operational telemetry streams into an explainable shipment risk score.
    """

    @classmethod
    def evaluate_shipment_risk(cls, document: DigitalShipmentDocument) -> Dict[str, Any]:
        reasons = []
        risk_level = ShipmentRiskLevel.LOW

        # 1. Cold-Chain IoT Evaluation
        cold_chain_risk = "LOW"
        sensor = document.cold_chain_sensors.first()
        if sensor:
            if sensor.status == ColdChainStatus.CRITICAL:
                cold_chain_risk = "CRITICAL"
                reasons.append(f"Cold-chain thermal breach: {sensor.current_temperature:.1f}°C")
                risk_level = ShipmentRiskLevel.CRITICAL
            elif sensor.status == ColdChainStatus.WARNING:
                cold_chain_risk = "HIGH"
                reasons.append(f"Cold-chain thermal variance warning: {sensor.current_temperature:.1f}°C")
                if risk_level not in [ShipmentRiskLevel.CRITICAL]:
                    risk_level = ShipmentRiskLevel.HIGH
            elif sensor.status == ColdChainStatus.SENSOR_OFFLINE:
                cold_chain_risk = "MEDIUM"
                reasons.append("IoT thermal sensor signal lost / offline")
                if risk_level == ShipmentRiskLevel.LOW:
                    risk_level = ShipmentRiskLevel.MEDIUM

        # 2. Checkpost Inspection Status
        checkpost_risk = "LOW"
        recent_verification = document.verifications.order_by("-verified_at").first()
        if recent_verification:
            if recent_verification.verification_result in [VerificationResult.BLOCKED, VerificationResult.INVALID]:
                checkpost_risk = "CRITICAL"
                reasons.append(f"Checkpost flag: {recent_verification.verification_result} at {recent_verification.checkpost.code}")
                risk_level = ShipmentRiskLevel.CRITICAL
            elif recent_verification.verification_result == VerificationResult.MISMATCH:
                checkpost_risk = "HIGH"
                reasons.append(f"Checkpost discrepancy: {recent_verification.reason}")
                if risk_level not in [ShipmentRiskLevel.CRITICAL]:
                    risk_level = ShipmentRiskLevel.HIGH

        # 3. Vehicle Operational Status
        vehicle_risk = "LOW"
        if document.vehicle:
            veh_status = str(document.vehicle.status).upper()
            if veh_status == "EMERGENCY":
                vehicle_risk = "CRITICAL"
                reasons.append("Assigned vehicle has active SOS distress event")
                risk_level = ShipmentRiskLevel.CRITICAL
            elif veh_status == "MAINTENANCE":
                vehicle_risk = "HIGH"
                reasons.append("Assigned vehicle flagged for mechanical maintenance")
                if risk_level not in [ShipmentRiskLevel.CRITICAL]:
                    risk_level = ShipmentRiskLevel.HIGH

        # 4. Delivery Deadline & Route Slack
        deadline_risk = "LOW"
        if document.valid_until and document.valid_until < timezone.now():
            deadline_risk = "CRITICAL"
            reasons.append("Shipment has exceeded its certified delivery window")
            risk_level = ShipmentRiskLevel.CRITICAL

        # 5. Route Hazard Factor (Corridor Landslide / Flood Status)
        route_hazard_risk = "LOW"
        if document.load and getattr(document.load, "assigned_trip", None):
            trip = document.load.assigned_trip
            if hasattr(trip, "dynamic_reroute_state"):
                if trip.dynamic_reroute_state.get("is_hazard_triggered"):
                    route_hazard_risk = "HIGH"
                    reasons.append("Route traversed active geohazard zone (dynamic bypass active)")
                    if risk_level not in [ShipmentRiskLevel.CRITICAL]:
                        risk_level = ShipmentRiskLevel.HIGH

        if not reasons:
            reasons.append("Corridor operational parameters within optimal tolerance. Journey on schedule.")

        explanation = ". ".join(reasons) + "."

        return {
            "shipment_number": document.shipment_number,
            "overall_risk": risk_level,
            "explanation": explanation,
            "factors": {
                "cold_chain_risk": cold_chain_risk,
                "checkpost_risk": checkpost_risk,
                "vehicle_risk": vehicle_risk,
                "deadline_risk": deadline_risk,
                "route_hazard_risk": route_hazard_risk,
            },
            "evaluated_at": timezone.now().isoformat(),
        }
