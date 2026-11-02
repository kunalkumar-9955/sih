"""
SIH26002 — Automated Multi-Factor Load Matching Engine.

Implements an explainable, multi-criteria recommendation engine matching
freight loads with optimal vehicles considering capacity fit, proximity,
availability, corridor geohazard safety, operational costs, delivery deadlines,
and disaster mode priorities.
"""
import math
from typing import Any, Dict, List, Optional
from django.db.models import Avg
from django.utils import timezone

from apps.vehicles.models import Vehicle, VehicleStatus
from apps.fleet.models import (
    CargoType,
    DisasterFleetModeState,
    FreightLoad,
    MatchingRecommendation,
)
from apps.fleet.services.eligibility_service import FleetAvailabilityEngine
from apps.fleet.services.cost_service import LogisticsCostOptimizer
from apps.fleet.services.deadline_service import DeliveryDeadlineIntelligence
from apps.transport_graph.models import TransportEdge


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class AutomatedLoadMatchingEngine:
    """
    Evaluates and ranks candidate vehicles for freight demands.
    """

    @classmethod
    def find_and_rank_candidates(
        cls,
        load: FreightLoad,
        candidate_vehicles: Optional[List[Vehicle]] = None,
        persist_recommendations: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Ranks all eligible vehicles for the given load.
        """
        vehicles = candidate_vehicles
        if vehicles is None:
            vehicles = list(
                Vehicle.objects.filter(is_active=True).exclude(
                    status__in=[VehicleStatus.MAINTENANCE, VehicleStatus.EMERGENCY, VehicleStatus.INACTIVE]
                ).select_related("owner", "assigned_driver")
            )

        disaster_state = DisasterFleetModeState.get_current()
        is_disaster = disaster_state.is_disaster_mode

        # Corridor hazard baseline
        avg_corridor_hazard = TransportEdge.objects.filter(is_available=True).aggregate(
            avg=Avg("hazard_score")
        )["avg"] or 0.15

        # Approximate distance from origin to destination
        origin_lat = load.origin_node.geometry.y if load.origin_node.geometry else 26.14
        origin_lon = load.origin_node.geometry.x if load.origin_node.geometry else 91.73
        dest_lat = load.destination_node.geometry.y if load.destination_node.geometry else 25.57
        dest_lon = load.destination_node.geometry.x if load.destination_node.geometry else 91.89

        trip_distance_km = max(10.0, haversine_km(origin_lat, origin_lon, dest_lat, dest_lon))
        estimated_transit_min = (trip_distance_km / 40.0) * 60.0  # Approx 40 km/h mountain corridor speed

        ranked_results: List[Dict[str, Any]] = []

        for veh in vehicles:
            # Step 1: Physical & Operational Eligibility
            eligibility = FleetAvailabilityEngine.evaluate_vehicle_eligibility(veh, load)
            if not eligibility["eligible"]:
                continue

            # Step 2: Multi-Factor Scoring (0 - 100 each)
            veh_cap = float(veh.capacity_kg or 1.0)
            req_weight = float(load.weight_kg or 0.0)

            # 2a. Capacity Fit Score (20%): optimal payload utilization is 75%-95%
            utilization = req_weight / veh_cap
            cap_score = max(40.0, min(100.0, 100.0 - (abs(0.85 - utilization) * 100.0)))

            # 2b. Distance to Pickup Score (15%):
            if veh.current_location:
                veh_lat = veh.current_location.y
                veh_lon = veh.current_location.x
                dist_to_pickup_km = haversine_km(veh_lat, veh_lon, origin_lat, origin_lon)
                dist_score = max(10.0, min(100.0, 100.0 - (dist_to_pickup_km * 0.90)))
            else:
                dist_to_pickup_km = 25.0
                dist_score = 70.0

            # 2c. Availability Score (15%):
            if veh.status == VehicleStatus.AVAILABLE:
                avail_score = 100.0
            elif veh.status == VehicleStatus.ASSIGNED:
                avail_score = 65.0
            else:
                avail_score = 45.0

            # 2d. Route Safety Score (20% - or 30% in disaster mode):
            safety_score = max(10.0, min(100.0, (1.0 - avg_corridor_hazard) * 100.0))

            # 2e. Cost Score (10% - or 5% in disaster mode):
            cost_eval = LogisticsCostOptimizer.estimate_trip_cost(
                distance_km=trip_distance_km + dist_to_pickup_km,
                vehicle=veh,
                average_hazard_index=avg_corridor_hazard,
            )
            est_cost_inr = cost_eval["total_estimated_cost_inr"]
            # Higher fuel efficiency yields higher cost score
            cost_score = min(100.0, max(20.0, (float(veh.fuel_efficiency_kmpl) / 6.0) * 100.0))

            # 2f. Deadline Compliance Score (10% - or 20% in disaster mode):
            deadline_eval = DeliveryDeadlineIntelligence.evaluate_deadline_risk(
                load=load,
                estimated_transit_time_min=estimated_transit_min,
            )
            deadline_score = deadline_eval["compliance_score"]

            # 2g. Mode & Cargo Compatibility Score (10%):
            compat_score = 80.0
            if load.is_perishable and "REFRIGERATED" in veh.supported_modes:
                compat_score = 100.0
            elif load.cargo_type == CargoType.BULK and veh.vehicle_type == "HEAVY_TRUCK":
                compat_score = 95.0

            # Weight distribution
            if is_disaster:
                w_cap, w_dist, w_avail, w_safe, w_cost, w_dead, w_compat = (
                    0.20, 0.15, 0.10, 0.30, 0.05, 0.15, 0.05
                )
            else:
                w_cap, w_dist, w_avail, w_safe, w_cost, w_dead, w_compat = (
                    0.20, 0.15, 0.15, 0.20, 0.10, 0.10, 0.10
                )

            final_score = (
                (cap_score * w_cap)
                + (dist_score * w_dist)
                + (avail_score * w_avail)
                + (safety_score * w_safe)
                + (cost_score * w_cost)
                + (deadline_score * w_dead)
                + (compat_score * w_compat)
            )

            # Generate explainability bullet points
            reasons = [
                f"Capacity fit: {utilization * 100.0:.0f}% payload utilization (cap: {veh_cap:.0f}kg)",
                f"Pickup proximity: {dist_to_pickup_km:.1f} km from origin",
                f"Route safety index: {safety_score:.0f}/100",
                f"Deadline status: {deadline_eval['status']} ({deadline_eval['slack_time_min']:.0f}m buffer)",
                f"Est. operational cost: \u20b9{est_cost_inr:,.2f}",
            ]
            if is_disaster:
                reasons.append("Disaster Response mode active (safety & deadline prioritized)")

            explanation = " | ".join(reasons)

            ranked_results.append({
                "vehicle_id": str(veh.id),
                "registration_number": veh.registration_number,
                "vehicle_type": veh.vehicle_type,
                "capacity_kg": veh_cap,
                "status": veh.status,
                "final_score": round(final_score, 1),
                "subscores": {
                    "capacity_score": round(cap_score, 1),
                    "distance_score": round(dist_score, 1),
                    "availability_score": round(avail_score, 1),
                    "safety_score": round(safety_score, 1),
                    "cost_score": round(cost_score, 1),
                    "deadline_score": round(deadline_score, 1),
                    "compatibility_score": round(compat_score, 1),
                },
                "distance_to_pickup_km": round(dist_to_pickup_km, 1),
                "estimated_cost_inr": est_cost_inr,
                "estimated_travel_time_min": round(estimated_transit_min, 1),
                "deadline_risk": deadline_eval["status"],
                "explanation": explanation,
                "reasons": reasons,
                "vehicle_obj": veh,
            })

        # Sort descending by final score
        ranked_results.sort(key=lambda x: x["final_score"], reverse=True)

        # Assign ranks
        for idx, item in enumerate(ranked_results, start=1):
            item["rank"] = idx

        # Persist top recommendations if requested
        if persist_recommendations and ranked_results:
            MatchingRecommendation.objects.filter(load=load).delete()
            for item in ranked_results[:5]:
                MatchingRecommendation.objects.create(
                    load=load,
                    vehicle=item["vehicle_obj"],
                    rank=item["rank"],
                    final_score=item["final_score"],
                    capacity_score=item["subscores"]["capacity_score"],
                    distance_score=item["subscores"]["distance_score"],
                    availability_score=item["subscores"]["availability_score"],
                    safety_score=item["subscores"]["safety_score"],
                    cost_score=item["subscores"]["cost_score"],
                    deadline_score=item["subscores"]["deadline_score"],
                    compatibility_score=item["subscores"]["compatibility_score"],
                    estimated_cost_inr=item["estimated_cost_inr"],
                    estimated_travel_time_min=item["estimated_travel_time_min"],
                    explanation=item["explanation"],
                )

        return ranked_results
