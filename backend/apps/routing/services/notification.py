"""
SIH26002 — Reroute Notification Service.

Generates structured, multilingual, driver- and dispatcher-facing alert
payloads when a route change is recommended or enforced.
"""
import logging
from typing import Any, Dict, Optional

from apps.routing.models import Route

logger = logging.getLogger("sih.routing.notification")


class RerouteNotificationService:
    """
    Constructs driver-friendly notifications for dynamic rerouting events.
    """

    @classmethod
    def build_notification_payload(
        cls,
        old_route: Optional[Route],
        new_route: Route,
        trigger_reason: str,
        is_mandatory: bool = False,
        improvement_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Creates a rich payload suitable for mobile in-app alert dialogs,
        push notifications, SMS/IVR fallback, and web dispatch consoles.
        """
        old_time = old_route.total_time_min if old_route else 0.0
        new_time = new_route.total_time_min
        time_delta_min = round(new_time - old_time, 1)

        old_dist = (old_route.total_distance_m / 1000.0) if old_route else 0.0
        new_dist = round(new_route.total_distance_m / 1000.0, 1)
        dist_delta_km = round(new_dist - old_dist, 1)

        old_max_h = getattr(old_route, "max_hazard_score", 0.0) if old_route else 0.0
        new_max_h = getattr(new_route, "max_hazard_score", 0.0)

        urgency = "CRITICAL" if is_mandatory else ("HIGH" if improvement_pct >= 0.3 else "MODERATE")

        if is_mandatory:
            title_en = "⛔ Road Blockage / Severe Hazard: Route Rerouted"
            body_en = (
                f"Your planned route is blocked or critically hazardous. "
                f"A safe bypass route ({new_dist:.1f} km, {new_time:.0f} min) has been assigned."
            )
        else:
            title_en = "⚠️ Safer Route Available"
            time_str = f"{abs(time_delta_min):.0f} min {'longer' if time_delta_min > 0 else 'shorter'}"
            body_en = (
                f"Hazard increased on current corridor. A safer alternative reduces risk by "
                f"{improvement_pct * 100:.0f}% ({time_str})."
            )

        actions = [
            {"action": "ACCEPT", "label": "Switch to Safe Route", "primary": True}
        ]
        if not is_mandatory:
            actions.append(
                {"action": "DECLINE", "label": "Keep Current Route", "primary": False}
            )

        return {
            "title": title_en,
            "message": body_en,
            "reason": trigger_reason,
            "urgency": urgency,
            "is_mandatory": is_mandatory,
            "improvement_pct": round(improvement_pct * 100.0, 1),
            "metrics": {
                "time_delta_min": time_delta_min,
                "distance_delta_km": dist_delta_km,
                "old_time_min": round(old_time, 1),
                "new_time_min": round(new_time, 1),
                "old_distance_km": round(old_dist, 1),
                "new_distance_km": new_dist,
                "old_max_hazard": round(old_max_h, 2),
                "new_max_hazard": round(new_max_h, 2),
                "new_policy": new_route.route_type,
            },
            "actions": actions,
            "i18n": {
                "en": {"title": title_en, "message": body_en},
                "as": {
                    "title": "⛔ পথ বন্ধ / বিপদজনক সংকেত" if is_mandatory else "⚠️ সুৰক্ষিত বিকল্প পথ উপলব্ধ",
                    "message": "সুৰক্ষিত বিকল্প পথেৰে যাত্ৰা অব্যাহত ৰাখক।"
                },
                "hi": {
                    "title": "⛔ रास्ता बंद / उच्च जोखिम: नया मार्ग तय" if is_mandatory else "⚠️ सुरक्षित वैकल्पिक मार्ग उपलब्ध",
                    "message": "आगे के मार्ग पर भूस्खलन/जोखिम बढ़ा है। सुरक्षित विकल्प चुनें।"
                }
            }
        }
