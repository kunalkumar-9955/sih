"""
SIH26002 — Dynamic Reroute Decision Service.

Orchestrates real-time hazard evaluation and intelligent rerouting for active trips.
"""
import logging
from typing import Any, Dict, List, Optional
from django.conf import settings
from django.utils import timezone

from apps.hazards.models import HazardSeverity
from apps.routing.engine import RoutingEngine
from apps.routing.models import Route, RouteType
from apps.trips.models import RerouteEvent, RerouteEventStatus, Trip, TripStatus
from .cache_invalidation import RouteCacheInvalidator
from .hazard_change import HazardChangeDetector
from .notification import RerouteNotificationService
from .route_risk import RouteRiskEvaluator

logger = logging.getLogger("sih.routing.reroute_decision")


class RerouteDecisionService:
    """
    Automated decision engine evaluating whether an active trip requires rerouting,
    computing optimal alternative corridors, and dispatching audit events.
    """

    def __init__(
        self,
        min_improvement_pct: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        routing_engine: Optional[RoutingEngine] = None,
    ):
        sih_settings = getattr(settings, "SIH_SETTINGS", {})
        self.min_improvement_pct = (
            min_improvement_pct
            if min_improvement_pct is not None
            else sih_settings.get("REROUTE_MIN_IMPROVEMENT_PCT", 0.10)
        )
        self.critical_threshold = (
            critical_threshold
            if critical_threshold is not None
            else sih_settings.get("REROUTE_CRITICAL_THRESHOLD", 0.85)
        )
        self.routing_engine = routing_engine or RoutingEngine()
        self.change_detector = HazardChangeDetector(
            critical_threshold=self.critical_threshold
        )

    def evaluate_and_reroute_trip(
        self,
        trip: Trip,
        auto_apply: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Main entry point for trip rerouting workflow.

        Parameters
        ----------
        trip: Trip
            Trip to evaluate.
        auto_apply: bool
            If True, automatically assigns new route to trip without waiting for driver.
            (Always automatically applied if current route is physically BLOCKED).
        force: bool
            If True, force re-calculation regardless of hazard delta threshold.
        """
        if trip.status not in [TripStatus.ACTIVE, TripStatus.PLANNED]:
            return {
                "rerouted": False,
                "reason": f"Trip is in state {trip.status}, only ACTIVE/PLANNED trips are rerouted.",
                "trip_id": str(trip.id),
            }

        current_route = trip.route
        if not current_route:
            return {
                "rerouted": False,
                "reason": "Trip has no assigned route to evaluate.",
                "trip_id": str(trip.id),
            }

        # 1. Detect hazard changes on current route
        change_info = self.change_detector.detect_route_change(
            route=current_route,
            baseline_hazard=getattr(current_route, "max_hazard_score", 0.0),
        )

        should_reroute = change_info["should_reroute"] or force
        if not should_reroute:
            return {
                "rerouted": False,
                "reason": "Hazard conditions on current route are within safe tolerance.",
                "trip_id": str(trip.id),
                "change_info": change_info,
            }

        # 2. Compute candidate alternative routes from origin to destination
        origin = trip.origin_node
        destination = trip.destination_node
        if not origin or not destination:
            return {
                "rerouted": False,
                "reason": "Trip lacks valid origin or destination node.",
                "trip_id": str(trip.id),
            }

        candidate_routes = self.routing_engine.compute_all_routes(
            origin=origin,
            destination=destination,
            requested_types=[
                RouteType.SAFEST,
                RouteType.MULTIMODAL,
                RouteType.FASTEST,
            ],
            persist=True,
            deduplicate=True,
        )

        if not candidate_routes:
            return {
                "rerouted": False,
                "reason": "No traversable alternative routes found across graph.",
                "trip_id": str(trip.id),
                "change_info": change_info,
            }

        # 3. Select best alternative (safest policy or lowest max hazard)
        best_candidate: Optional[Route] = None
        current_route_edge_ids = [
            str(s.get("edge_id")) for s in (current_route.segments or []) if s.get("edge_id")
        ]

        # Prioritize routes that don't share the blocked/critical edges
        triggering_ids = set(change_info["triggering_edge_ids"])
        viable_candidates: List[Route] = []

        for r in candidate_routes:
            cand_edge_ids = [
                str(s.get("edge_id")) for s in (r.segments or []) if s.get("edge_id")
            ]
            # Must not be identical segment sequence if current route is blocked
            if cand_edge_ids == current_route_edge_ids and change_info["is_blocked"]:
                continue
            # Avoid routes that still use the triggering hazardous edges
            has_triggering_edge = any(eid in triggering_ids for eid in cand_edge_ids)
            if not has_triggering_edge:
                viable_candidates.append(r)

        candidates_pool = viable_candidates if viable_candidates else candidate_routes

        # Sort candidate routes: lowest max_hazard_score, then lowest hazard_penalty_score
        candidates_pool.sort(
            key=lambda r: (
                getattr(r, "max_hazard_score", 0.0),
                getattr(r, "hazard_penalty_score", 0.0),
                r.total_time_min,
            )
        )
        best_candidate = candidates_pool[0]

        # 4. Compare candidate against current route
        old_h = change_info["current_max_hazard"]
        new_h = getattr(best_candidate, "max_hazard_score", 0.0)

        improvement_pct = 0.0
        if old_h > 0.0:
            improvement_pct = max(0.0, (old_h - new_h) / old_h)

        is_mandatory = change_info["is_blocked"] or change_info["is_critical"]

        if not is_mandatory and improvement_pct < self.min_improvement_pct and not force:
            return {
                "rerouted": False,
                "reason": (
                    f"Best alternative provides only {improvement_pct * 100:.1f}% hazard reduction "
                    f"(minimum required: {self.min_improvement_pct * 100:.1f}%)."
                ),
                "trip_id": str(trip.id),
                "improvement_pct": improvement_pct,
                "candidate_route_id": str(best_candidate.id),
            }

        # 5. Idempotency check: check if an identical pending reroute event exists
        pending_events = RerouteEvent.objects.filter(
            trip=trip,
            status__in=[RerouteEventStatus.PENDING, RerouteEventStatus.SENT],
            new_route=best_candidate,
        )
        if pending_events.exists():
            existing = pending_events.first()
            return {
                "rerouted": True,
                "event_id": str(existing.id),
                "status": existing.status,
                "is_existing": True,
                "reason": "Existing pending reroute event already active for this route.",
                "new_route_id": str(best_candidate.id),
            }

        # 6. Build notification payload
        notif_payload = RerouteNotificationService.build_notification_payload(
            old_route=current_route,
            new_route=best_candidate,
            trigger_reason=change_info["trigger_reason"],
            is_mandatory=is_mandatory,
            improvement_pct=improvement_pct,
        )

        # 7. Create RerouteEvent
        event_status = RerouteEventStatus.PENDING
        should_apply_now = auto_apply or is_mandatory

        if should_apply_now:
            event_status = RerouteEventStatus.APPLIED

        event = RerouteEvent.objects.create(
            trip=trip,
            old_route=current_route,
            new_route=best_candidate,
            trigger_reason=change_info["trigger_reason"],
            triggering_edge_ids=change_info["triggering_edge_ids"],
            old_hazard_exposure=old_h,
            new_hazard_exposure=new_h,
            improvement_pct=improvement_pct,
            trip_route_version=trip.route_version,
            status=event_status,
            notification_payload=notif_payload,
        )

        # 8. Apply route to trip if mandatory or auto_apply requested
        if should_apply_now:
            self._apply_route_to_trip(trip, best_candidate)

        # Invalidate affected route caches
        RouteCacheInvalidator.invalidate_pair(str(origin.id), str(destination.id))

        return {
            "rerouted": True,
            "event_id": str(event.id),
            "status": event.status,
            "applied": should_apply_now,
            "is_mandatory": is_mandatory,
            "improvement_pct": round(improvement_pct, 4),
            "old_route_id": str(current_route.id),
            "new_route_id": str(best_candidate.id),
            "trigger_reason": change_info["trigger_reason"],
            "notification": notif_payload,
        }

    def _apply_route_to_trip(self, trip: Trip, new_route: Route):
        """Applies new route to trip and updates version and timestamps."""
        now = timezone.now()
        trip.route = new_route
        trip.route_version = (trip.route_version or 1) + 1
        trip.route_assigned_at = now
        trip.route_hazard_snapshot_at = now
        trip.route_snapshot = {
            "route_id": str(new_route.id),
            "policy": new_route.route_type,
            "total_distance_m": new_route.total_distance_m,
            "total_time_min": new_route.total_time_min,
            "total_cost_inr": float(new_route.total_cost_inr or 0.0),
            "max_hazard_score": getattr(new_route, "max_hazard_score", 0.0),
            "assigned_at": now.isoformat(),
        }
        trip.save(
            update_fields=[
                "route",
                "route_version",
                "route_assigned_at",
                "route_hazard_snapshot_at",
                "route_snapshot",
                "updated_at",
            ]
        )
        logger.info(f"Trip {trip.id} route updated to v{trip.route_version} (Route {new_route.id})")
