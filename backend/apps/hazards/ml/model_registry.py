"""
SIH26002 — Model Registry Service.

Manages model versions, active deployment flags, artifact caching, and database registration.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import joblib

from apps.hazards.models import HazardModelRecord
from .train import TrainingResult

logger = logging.getLogger("sih.hazards.model_registry")

# In-memory singleton model cache to prevent repeated disk I/O on hot inference paths
_LOADED_MODELS_CACHE: Dict[str, Any] = {}


class ModelRegistry:
    """
    Orchestrates registered ML model records and runtime artifact loading.
    """

    @classmethod
    def register_trained_model(
        cls,
        training_result: TrainingResult,
        set_active: bool = True,
    ) -> HazardModelRecord:
        """
        Records a newly trained model in the database registry.
        """
        if set_active:
            # Mark previous active models as inactive
            HazardModelRecord.objects.filter(is_active=True).update(is_active=False)

        record = HazardModelRecord.objects.create(
            model_id=training_result.model_id,
            model_version=training_result.model_version,
            algorithm=training_result.algorithm,
            feature_version=training_result.feature_version,
            dataset_type=training_result.dataset_type,
            training_samples=training_result.training_samples,
            metrics=training_result.metrics,
            feature_importances=training_result.feature_importances,
            artifact_path=training_result.artifact_path,
            is_active=set_active,
        )

        # Cache loaded object
        _LOADED_MODELS_CACHE[record.model_version] = training_result.model
        logger.info(f"Registered model {record.model_version} (Active={set_active})")
        return record

    @classmethod
    def load_model_artifact(cls, artifact_path: str) -> Optional[Any]:
        """Loads serialized model from filesystem."""
        if not os.path.exists(artifact_path):
            logger.warning(f"Model artifact not found at {artifact_path}")
            return None
        try:
            return joblib.load(artifact_path)
        except Exception as e:
            logger.error(f"Failed to load model artifact from {artifact_path}: {e}")
            return None

    @classmethod
    def get_active_model(cls) -> Tuple[Optional[HazardModelRecord], Optional[Any]]:
        """
        Retrieves active model record and loaded estimator.
        """
        record = HazardModelRecord.objects.filter(is_active=True).first()
        if not record:
            # Fallback to latest registered model
            record = HazardModelRecord.objects.order_by("-trained_at").first()

        if not record:
            return None, None

        if record.model_version in _LOADED_MODELS_CACHE:
            return record, _LOADED_MODELS_CACHE[record.model_version]

        estimator = cls.load_model_artifact(record.artifact_path)
        if estimator is not None:
            _LOADED_MODELS_CACHE[record.model_version] = estimator

        return record, estimator

    @classmethod
    def clear_cache(cls) -> None:
        _LOADED_MODELS_CACHE.clear()
