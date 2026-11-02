"""
SIH26002 — Hazard Provider Interface.

Decouples the routing engine from AI/ML prediction models.
The routing engine consumes standardized HazardScoreData (edge_id, hazard_score, confidence, timestamp, model_version)
without directly depending on XGBoost, Random Forest, or Spatial GCN architectures.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from django.utils import timezone

from apps.transport_graph.models import TransportEdge


@dataclass
class HazardScoreData:
    """
    Standardized hazard payload for an edge.
    """
    edge_id: str
    hazard_score: float  # [0.0, 1.0]
    confidence: float    # [0.0, 1.0]
    timestamp: datetime
    model_version: str


class HazardProvider(ABC):
    """
    Abstract interface for retrieving or predicting geohazard scores for transport edges.
    """

    @abstractmethod
    def get_hazard(self, edge: TransportEdge) -> HazardScoreData:
        """Returns hazard assessment for a given transport edge."""
        pass


class StaticHazardProvider(HazardProvider):
    """
    Standard provider: pulls hazard scores stored on the TransportEdge model
    with defined fallback behavior for missing data.
    """

    def __init__(self, fallback_score: float = 0.0):
        self.fallback_score = fallback_score

    def get_hazard(self, edge: TransportEdge) -> HazardScoreData:
        score = float(edge.hazard_score) if getattr(edge, "hazard_score", None) is not None else self.fallback_score
        # Bound score to [0.0, 1.0]
        score = max(0.0, min(1.0, score))

        data_src = getattr(edge, "data_source", None)
        confidence = 0.90 if data_src != "manual" else 0.70
        timestamp = getattr(edge, "last_updated", None) or timezone.now()

        return HazardScoreData(
            edge_id=str(edge.id),
            hazard_score=score,
            confidence=confidence,
            timestamp=timestamp,
            model_version="static-corridor-baseline-v1",
        )


class MockHazardProvider(HazardProvider):
    """
    Provider for deterministic test suites and scenario simulations.
    Allows overriding hazard scores by edge_id or setting a global default.
    """

    def __init__(self, overrides: Optional[Dict[str, float]] = None, default_score: Optional[float] = None):
        self.overrides = overrides or {}
        self.default_score = default_score

    def get_hazard(self, edge: TransportEdge) -> HazardScoreData:
        if self.default_score is not None:
            score = self.default_score
        else:
            score = self.overrides.get(str(edge.id), float(getattr(edge, "hazard_score", 0.0) or 0.0))
        score = max(0.0, min(1.0, score))

        return HazardScoreData(
            edge_id=str(edge.id),
            hazard_score=score,
            confidence=1.0,
            timestamp=timezone.now(),
            model_version="mock-simulation-v1",
        )


class PredictionHazardProvider(HazardProvider):
    """
    Production hazard provider connecting the routing engine directly to the
    Hazard Intelligence & Risk Prediction Engine.
    Consumes live or cached HazardScore predictions with defined stale data behavior.
    """

    def __init__(
        self,
        stale_penalty: float = 0.10,
        enable_realtime_inference: bool = True,
    ):
        self.stale_penalty = stale_penalty
        self.enable_realtime_inference = enable_realtime_inference
        self._prediction_service = None

    @property
    def prediction_service(self):
        if self._prediction_service is None:
            from apps.hazards.services.prediction_service import HazardPredictionService
            self._prediction_service = HazardPredictionService()
        return self._prediction_service

    def get_hazard(self, edge: TransportEdge) -> HazardScoreData:
        """
        Retrieves hazard assessment:
        1. Checks active HazardScore from DB
        2. Evaluates freshness: applies conservative penalty if stale
        3. Falls back to real-time inference or static edge hazard score
        """
        try:
            from apps.hazards.models import HazardScore
            latest_score = (
                HazardScore.objects.filter(edge=edge, is_current=True)
                .order_by("-predicted_at")
                .first()
            )
        except Exception:
            latest_score = None

        if latest_score:
            score = float(latest_score.hazard_index)
            conf = float(latest_score.confidence)
            ver = latest_score.model_version
            ts = latest_score.predicted_at

            # Stale Data Behavior:
            # If past valid_until, penalize score conservatively and lower confidence
            if latest_score.is_stale:
                score = min(1.0, score + self.stale_penalty)
                conf = max(0.40, conf * 0.70)
                ver = f"{ver}-stale"

            return HazardScoreData(
                edge_id=str(edge.id),
                hazard_score=score,
                confidence=conf,
                timestamp=ts,
                model_version=ver,
            )

        # If no active score in DB, run inference service if enabled
        if self.enable_realtime_inference:
            try:
                res = self.prediction_service.predict_single_edge(edge, persist_score=False)
                return HazardScoreData(
                    edge_id=str(edge.id),
                    hazard_score=res.hazard_index,
                    confidence=res.confidence,
                    timestamp=res.predicted_at,
                    model_version=res.model_version,
                )
            except Exception:
                pass

        # Final fallback: edge baseline score
        base_score = float(getattr(edge, "hazard_score", 0.0) or 0.0)
        return HazardScoreData(
            edge_id=str(edge.id),
            hazard_score=max(0.0, min(1.0, base_score)),
            confidence=0.50,
            timestamp=getattr(edge, "last_updated", None) or timezone.now(),
            model_version="static-fallback-v1",
        )

