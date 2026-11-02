"""
SIH26002 — Hazard Prediction & Inference Service.

Orchestrates live and batch edge risk predictions:
Feature Extraction -> ML Model Inference -> Top Contributing Factor Analysis -> Severity Assignment
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from django.conf import settings
from django.utils import timezone

from apps.hazards.ml.features import FEATURE_NAMES, HazardFeatureExtractor
from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.models import HazardScore, HazardSeverity
from apps.hazards.services.terrain_service import MockTerrainProvider, TerrainData, TerrainProvider
from apps.hazards.services.weather_service import MockWeatherProvider, WeatherData, WeatherProvider
from apps.transport_graph.models import TransportEdge

logger = logging.getLogger("sih.hazards.prediction_service")


@dataclass
class HazardPredictionResult:
    edge_id: str
    hazard_index: float
    confidence: float
    severity: str
    model_version: str
    feature_version: str
    contributing_factors: Dict[str, Any]
    features_snapshot: Dict[str, float]
    predicted_at: datetime
    valid_until: datetime
    is_stale: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "hazard_index": round(self.hazard_index, 4),
            "confidence": round(self.confidence, 3),
            "severity": self.severity,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "contributing_factors": self.contributing_factors,
            "features_snapshot": self.features_snapshot,
            "predicted_at": self.predicted_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "is_stale": self.is_stale,
        }


class HazardPredictionService:
    """
    High-performance, deterministic hazard prediction engine.
    """

    def __init__(
        self,
        weather_provider: Optional[WeatherProvider] = None,
        terrain_provider: Optional[TerrainProvider] = None,
    ):
        self.weather_provider = weather_provider or MockWeatherProvider()
        self.terrain_provider = terrain_provider or MockTerrainProvider()

    def compute_contributing_factors(
        self,
        features: Dict[str, float],
        hazard_index: float,
        model_record: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Explains top contributing physical factors for admin/developer inspection.
        Never states causality — describes relative risk elevation factors.
        """
        factors = {}
        rain_24h = features.get("rainfall_24h_mm", 0.0)
        slope = features.get("slope_deg", 0.0)
        soil_sat = features.get("soil_saturation", 0.0)
        hist_incidents = features.get("historical_incident_count", 0.0)
        fault_dist = features.get("fault_line_distance_km", 20.0)

        if rain_24h > 50.0:
            factors["monsoon_rainfall"] = f"Heavy 24h precipitation ({rain_24h:.1f} mm)"
        elif rain_24h > 20.0:
            factors["monsoon_rainfall"] = f"Moderate 24h precipitation ({rain_24h:.1f} mm)"

        if slope > 20.0:
            factors["terrain_steepness"] = f"Severe mountain gradient ({slope:.1f}° slope)"
        elif slope > 10.0:
            factors["terrain_steepness"] = f"Moderate gradient ({slope:.1f}° slope)"

        if soil_sat > 0.65:
            factors["soil_saturation"] = f"High pore-water saturation ({int(soil_sat * 100)}%)"

        if hist_incidents >= 3.0:
            factors["historical_instability"] = f"Frequent prior slope washouts ({int(hist_incidents)} events)"

        if fault_dist < 10.0:
            factors["geological_fault"] = f"Tectonic fracture proximity ({fault_dist:.1f} km)"

        return factors

    def predict_single_edge(
        self,
        edge: TransportEdge,
        weather_data: Optional[WeatherData] = None,
        terrain_data: Optional[TerrainData] = None,
        incident_stats: Optional[Dict[str, Any]] = None,
        persist_score: bool = False,
    ) -> HazardPredictionResult:
        """
        Performs inference for an individual edge.
        """
        w_data = weather_data or self.weather_provider.get_weather_for_edge(edge)
        t_data = terrain_data or self.terrain_provider.get_terrain_for_edge(edge)

        # Build feature vector
        features = HazardFeatureExtractor.extract_from_raw(
            terrain=t_data.to_dict() if hasattr(t_data, "to_dict") else vars(t_data),
            weather=w_data.to_dict() if hasattr(w_data, "to_dict") else vars(w_data),
            incident_stats=incident_stats or {},
            edge_stats={"distance_m": float(edge.distance_m or 10000.0)},
        )
        vec = HazardFeatureExtractor.to_array(features).reshape(1, -1)

        # Get active model from registry
        model_record, estimator = ModelRegistry.get_active_model()

        predicted_at = timezone.now()
        freshness_hours = getattr(settings, "HAZARD_PREDICTION_VALIDITY_HOURS", 6)
        valid_until = predicted_at + timedelta(hours=freshness_hours)

        if estimator is not None:
            model_ver = model_record.model_version
            conf = 0.90
            try:
                # Binary classification disruption probability -> hazard index
                prob = float(estimator.predict_proba(vec)[0, 1])
                hazard_score = max(0.01, min(0.99, prob))
            except Exception as e:
                logger.error(f"Inference error with model {model_ver}: {e}. Using fallback.")
                hazard_score = float(edge.hazard_score or 0.15)
                conf = 0.50
        else:
            # Fallback heuristic if no model is registered yet
            model_ver = "fallback-heuristic-v1"
            conf = 0.65
            slope = features.get("slope_deg", 5.0)
            rain_24h = features.get("rainfall_24h_mm", 0.0)
            soil_sat = features.get("soil_saturation", 0.3)
            # Physical approximation
            raw = (0.35 * min(1.0, slope / 35.0)) + (0.45 * min(1.0, rain_24h / 120.0)) + (0.20 * soil_sat)
            hazard_score = max(0.02, min(0.98, raw))

        severity = HazardSeverity.classify(hazard_score)
        contributing_factors = self.compute_contributing_factors(features, hazard_score, model_record)

        result = HazardPredictionResult(
            edge_id=str(edge.id),
            hazard_index=hazard_score,
            confidence=conf,
            severity=severity,
            model_version=model_ver,
            feature_version="fv1",
            contributing_factors=contributing_factors,
            features_snapshot=features,
            predicted_at=predicted_at,
            valid_until=valid_until,
            is_stale=False,
        )

        if persist_score:
            # Mark previous active scores as non-current
            HazardScore.objects.filter(edge=edge, is_current=True).update(is_current=False)
            HazardScore.objects.create(
                edge=edge,
                hazard_index=hazard_score,
                confidence=conf,
                severity=severity,
                model_version=model_ver,
                feature_version="fv1",
                predicted_at=predicted_at,
                valid_until=valid_until,
                source="ml_inference",
                contributing_factors=contributing_factors,
                features_snapshot=features,
                is_current=True,
            )

        return result

    def bulk_predict_edges(
        self,
        edges: List[TransportEdge],
        persist_scores: bool = True,
    ) -> List[HazardPredictionResult]:
        """
        Batch prediction across multiple transport edges with optimized bulk inference.
        """
        if not edges:
            return []

        # 1. Gather features for all edges
        feature_dicts: List[Dict[str, float]] = []
        for e in edges:
            w_data = self.weather_provider.get_weather_for_edge(e)
            t_data = self.terrain_provider.get_terrain_for_edge(e)
            f = HazardFeatureExtractor.extract_from_raw(
                terrain=t_data.to_dict() if hasattr(t_data, "to_dict") else vars(t_data),
                weather=w_data.to_dict() if hasattr(w_data, "to_dict") else vars(w_data),
                edge_stats={"distance_m": float(e.distance_m or 10000.0)},
            )
            feature_dicts.append(f)

        X_batch = np.array([HazardFeatureExtractor.to_array(f) for f in feature_dicts], dtype=np.float32)

        # 2. Run model inference in single vectorized call
        model_record, estimator = ModelRegistry.get_active_model()
        predicted_at = timezone.now()
        freshness_hours = getattr(settings, "HAZARD_PREDICTION_VALIDITY_HOURS", 6)
        valid_until = predicted_at + timedelta(hours=freshness_hours)

        if estimator is not None:
            model_ver = model_record.model_version
            conf = 0.90
            try:
                probs = estimator.predict_proba(X_batch)[:, 1]
                scores = np.clip(probs, 0.01, 0.99).tolist()
            except Exception as e:
                logger.error(f"Bulk inference error with model {model_ver}: {e}")
                scores = [float(e.hazard_score or 0.15) for e in edges]
                conf = 0.50
        else:
            model_ver = "fallback-heuristic-v1"
            conf = 0.65
            scores = []
            for f in feature_dicts:
                slope = f.get("slope_deg", 5.0)
                rain_24h = f.get("rainfall_24h_mm", 0.0)
                soil_sat = f.get("soil_saturation", 0.3)
                raw = (0.35 * min(1.0, slope / 35.0)) + (0.45 * min(1.0, rain_24h / 120.0)) + (0.20 * soil_sat)
                scores.append(float(np.clip(raw, 0.02, 0.98)))

        results: List[HazardPredictionResult] = []
        scores_to_create: List[HazardScore] = []

        edge_ids = [e.id for e in edges]
        if persist_scores:
            HazardScore.objects.filter(edge_id__in=edge_ids, is_current=True).update(is_current=False)

        for e, score, f_dict in zip(edges, scores, feature_dicts):
            sev = HazardSeverity.classify(score)
            factors = self.compute_contributing_factors(f_dict, score, model_record)

            res = HazardPredictionResult(
                edge_id=str(e.id),
                hazard_index=score,
                confidence=conf,
                severity=sev,
                model_version=model_ver,
                feature_version="fv1",
                contributing_factors=factors,
                features_snapshot=f_dict,
                predicted_at=predicted_at,
                valid_until=valid_until,
                is_stale=False,
            )
            results.append(res)

            if persist_scores:
                scores_to_create.append(
                    HazardScore(
                        edge=e,
                        hazard_index=score,
                        confidence=conf,
                        severity=sev,
                        model_version=model_ver,
                        feature_version="fv1",
                        predicted_at=predicted_at,
                        valid_until=valid_until,
                        source="ml_inference",
                        contributing_factors=factors,
                        features_snapshot=f_dict,
                        is_current=True,
                    )
                )

        if persist_scores and scores_to_create:
            HazardScore.objects.bulk_create(scores_to_create)

        return results
