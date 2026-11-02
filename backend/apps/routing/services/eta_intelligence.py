"""
SIH26002 — Predictive ETA & Delay Intelligence Engine.

Provides an explainable, multi-factor delay estimation and ETA prediction
service for multi-modal mountain corridors across the North Eastern Region.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.routing.models import ETAPredictionRecord, Route
from apps.transport_graph.models import EdgeStatus, TransportEdge, TransportMode, TransportNode

logger = logging.getLogger("sih.routing.eta_intelligence")


class BaseDelayModelProvider(ABC):
    """Abstract interface for predictive ETA and delay models."""

    @abstractmethod
    def predict(
        self,
        base_transit_time_min: float,
        route_distance_km: float,
        hazard_score: float,
        weather_rainfall_mm: float = 0.0,
        has_incidents: bool = False,
        transfer_count: int = 0,
        departure_time: Optional[datetime] = None,
        is_hill_corridor: bool = True,
    ) -> Dict[str, Any]:
        pass


class MountainCorridorDelayModel(BaseDelayModelProvider):
    """
    Calibrated domain model for North Eastern Region mountain corridors.
    Accounts for monsoon rainfall, hill gradient resistance, active geohazards,
    and intermodal switching delays.
    """

    MODEL_VERSION = "ner-mountain-eta-v2.1"
    DATA_SOURCE_MODE = "CONFIGURED"

    def predict(
        self,
        base_transit_time_min: float,
        route_distance_km: float,
        hazard_score: float,
        weather_rainfall_mm: float = 0.0,
        has_incidents: bool = False,
        transfer_count: int = 0,
        departure_time: Optional[datetime] = None,
        is_hill_corridor: bool = True,
        is_mountain_pass: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        # 1. Weather Impact (Rainfall intensity)
        # In NER, > 20mm/hr causes surface runoff; > 50mm causes road crawl
        weather_delay = 0.0
        if weather_rainfall_mm > 5.0:
            weather_delay = min(90.0, weather_rainfall_mm * 1.4)

        # 2. Geohazard Impact (Landslide / slope instability caution)
        # Hazard in [0, 1] — high hazard forces driver slowdown to 15-20 km/h
        hazard_delay = round(hazard_score * 50.0, 1)

        # 3. Incident / Blockage Impact
        incident_delay = 45.0 if has_incidents else 0.0

        # 4. Multimodal Transfer Buffers
        # Each intermodal transfer requires crane/yard unloading & inspection buffer
        transfer_delay = round(transfer_count * 25.0, 1)

        # 5. Mountain Terrain Gradient Delay
        terrain_delay = round((route_distance_km * 0.15) if is_hill_corridor else 0.0, 1)

        # 6. Peak-Hour Congestion Proxy (Urban corridor junctions: 08-11h, 16-19h)
        dep_time = departure_time or timezone.now()
        dep_hour = dep_time.hour
        is_peak = (8 <= dep_hour <= 11) or (16 <= dep_hour <= 19)
        congestion_delay = 18.0 if is_peak else 0.0

        # Total expected delay beyond base unimpeded transit
        total_expected_delay = round(
            weather_delay + hazard_delay + incident_delay + transfer_delay + terrain_delay + congestion_delay,
            1,
        )

        predicted_transit_min = round(base_transit_time_min + total_expected_delay, 1)
        predicted_eta = dep_time + timedelta(minutes=predicted_transit_min)

        # Delay probability modeled via logistic function of composite risk
        risk_sum = (hazard_score * 2.0) + (weather_rainfall_mm / 30.0) + (1.0 if has_incidents else 0.0)
        delay_prob = round(min(0.98, max(0.05, 1.0 / (1.0 + (2.718 ** (-(risk_sum - 1.2)))))), 2)

        # Model confidence is high for standard operational envelopes
        confidence = round(max(0.70, min(0.95, 0.92 - (hazard_score * 0.15))), 2)

        factors = {
            "weather_rainfall_delay_min": round(weather_delay, 1),
            "geohazard_risk_delay_min": round(hazard_delay, 1),
            "corridor_incident_delay_min": round(incident_delay, 1),
            "multimodal_transfer_delay_min": round(transfer_delay, 1),
            "mountain_terrain_delay_min": round(terrain_delay, 1),
            "peak_congestion_proxy_min": round(congestion_delay, 1),
            "rainfall_recorded_mm": weather_rainfall_mm,
            "corridor_hazard_index": round(hazard_score, 3),
        }

        return {
            "predicted_eta": predicted_eta,
            "predicted_transit_time_min": predicted_transit_min,
            "expected_delay_min": total_expected_delay,
            "delay_probability": delay_prob,
            "confidence_score": confidence,
            "contributing_factors": factors,
            "model_version": self.MODEL_VERSION,
            "data_source_mode": self.DATA_SOURCE_MODE,
        }

    predict_delay = predict


class PredictiveETAService:
    """
    High-level ETA intelligence orchestration service.
    """

    _provider: BaseDelayModelProvider = MountainCorridorDelayModel()

    @classmethod
    def set_provider(cls, provider: BaseDelayModelProvider):
        cls._provider = provider

    @classmethod
    def predict_for_route(
        cls,
        route_id: str,
        departure_time: Optional[datetime] = None,
        weather_rainfall_mm: float = 0.0,
        trip_id: str = "",
        vehicle_id: str = "",
        persist: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculates predictive ETA and delay breakdown for an existing Route.
        """
        try:
            route = Route.objects.select_related("origin_node", "destination_node").get(id=route_id)
        except Route.DoesNotExist:
            return {"success": False, "error": f"Route '{route_id}' not found."}

        route_dist_km = route.total_distance_m / 1000.0
        base_time_min = route.total_time_min
        hazard_score = route.hazard_penalty_score
        transfer_count = route.transfer_count
        has_incidents = route.critical_edge_count > 0

        dep_time = departure_time or timezone.now()

        pred = cls._provider.predict(
            base_transit_time_min=base_time_min,
            route_distance_km=route_dist_km,
            hazard_score=hazard_score,
            weather_rainfall_mm=weather_rainfall_mm,
            has_incidents=has_incidents,
            transfer_count=transfer_count,
            departure_time=dep_time,
        )

        record_id = None
        if persist:
            record = ETAPredictionRecord.objects.create(
                route=route,
                trip_id=trip_id,
                vehicle_id=vehicle_id,
                origin_node=route.origin_node,
                destination_node=route.destination_node,
                departure_time=dep_time,
                base_transit_time_min=base_time_min,
                route_distance_km=round(route_dist_km, 1),
                predicted_transit_time_min=pred["predicted_transit_time_min"],
                predicted_eta=pred["predicted_eta"],
                delay_probability=pred["delay_probability"],
                expected_delay_min=pred["expected_delay_min"],
                confidence_score=pred["confidence_score"],
                contributing_factors=pred["contributing_factors"],
                model_version=pred["model_version"],
                data_source_mode=pred["data_source_mode"],
            )
            record_id = str(record.id)

        prediction_payload = {
            "predicted_eta": pred["predicted_eta"].isoformat(),
            "base_transit_time_min": base_time_min,
            "predicted_transit_minutes": pred["predicted_transit_time_min"],
            "predicted_transit_time_min": pred["predicted_transit_time_min"],
            "expected_delay_minutes": pred["expected_delay_min"],
            "expected_delay_min": pred["expected_delay_min"],
            "delay_probability": pred["delay_probability"],
            "delay_risk_level": "HIGH" if pred["delay_probability"] > 0.65 else ("MODERATE" if pred["delay_probability"] > 0.35 else "LOW"),
            "confidence": pred["confidence_score"],
            "confidence_score": pred["confidence_score"],
            "contributing_factors": [
                {"factor": k.replace("_", " ").title(), "delay_minutes": v}
                for k, v in pred["contributing_factors"].items()
                if isinstance(v, (int, float)) and v > 0
            ] if isinstance(pred["contributing_factors"], dict) else pred["contributing_factors"],
        }

        return {
            "success": True,
            "eta_prediction_id": record_id,
            "route_id": str(route.id),
            "origin_name": route.origin_node.name,
            "destination_name": route.destination_node.name,
            "departure_time": dep_time.isoformat(),
            "predicted_eta": pred["predicted_eta"].isoformat(),
            "base_transit_time_min": base_time_min,
            "predicted_transit_time_min": pred["predicted_transit_time_min"],
            "expected_delay_min": pred["expected_delay_min"],
            "delay_probability": pred["delay_probability"],
            "delay_risk_level": "HIGH" if pred["delay_probability"] > 0.65 else ("MODERATE" if pred["delay_probability"] > 0.35 else "LOW"),
            "confidence_score": pred["confidence_score"],
            "contributing_factors": pred["contributing_factors"],
            "prediction": prediction_payload,
            "model_metadata": {
                "algorithm": pred["model_version"],
                "data_mode": pred["data_source_mode"],
            },
        }

    @classmethod
    def predict_adhoc(
        cls,
        origin_node_id: str,
        destination_node_id: str,
        departure_time: Optional[datetime] = None,
        weather_rainfall_mm: float = 0.0,
        trip_id: str = "",
        vehicle_id: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Ad-hoc prediction by computing fastest/safest path first."""
        try:
            origin = TransportNode.objects.get(id=origin_node_id, is_active=True)
            destination = TransportNode.objects.get(id=destination_node_id, is_active=True)
        except TransportNode.DoesNotExist as e:
            return {"success": False, "error": f"Node not found: {str(e)}"}

        from apps.routing.engine import RoutingEngine
        engine = RoutingEngine()
        routes = engine.compute_all_routes(origin=origin, destination=destination, requested_types=["SAFEST"], persist=True)

        if not routes:
            return {"success": False, "error": "No viable path found between nodes."}

        return cls.predict_for_route(
            route_id=str(routes[0].id),
            departure_time=departure_time,
            weather_rainfall_mm=weather_rainfall_mm,
            trip_id=trip_id,
            vehicle_id=vehicle_id,
            persist=True,
            **kwargs,
        )
