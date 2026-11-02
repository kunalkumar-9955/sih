"""
SIH26002 — Model Training Pipeline.

Trains XGBoost and Random Forest classifiers on the standardized feature pipeline,
measures actual test metrics, ranks feature contributions, and serializes model artifacts.
"""
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
try:
    from sklearn.ensemble import RandomForestClassifier
except (ImportError, Exception):
    RandomForestClassifier = None
from xgboost import XGBClassifier

from .dataset import DatasetSplit, HazardDatasetGenerator
from .evaluate import EvaluationMetrics, ModelEvaluator
from .features import FEATURE_NAMES

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


@dataclass
class TrainingResult:
    model_id: str
    model_version: str
    algorithm: str
    feature_version: str
    dataset_type: str
    training_samples: int
    metrics: Dict[str, Any]
    feature_importances: Dict[str, float]
    artifact_path: str
    model: Any


class HazardModelTrainer:
    """
    Executes reproducible, deterministic model training and artifact persistence.
    """

    @classmethod
    def train_xgboost(
        cls,
        split: Optional[DatasetSplit] = None,
        model_version: Optional[str] = None,
        n_estimators: int = 120,
        max_depth: int = 5,
        learning_rate: float = 0.08,
        random_seed: int = 42,
    ) -> TrainingResult:
        """
        Trains baseline XGBoost hazard classification model.
        """
        if split is None:
            df = HazardDatasetGenerator.generate_synthetic_corpus(n_samples=1200, random_seed=random_seed)
            split = HazardDatasetGenerator.create_train_val_test_split(df, random_seed=random_seed)

        model_id = str(uuid.uuid4())
        version = model_version or f"hazard-xgb-v{uuid.uuid4().hex[:6]}"

        xgb_model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_seed,
            eval_metric="logloss",
        )

        # Train on train split
        xgb_model.fit(
            split.X_train,
            split.y_train,
            eval_set=[(split.X_val, split.y_val)],
            verbose=False,
        )

        # Evaluate strictly on held-out test split
        y_test_pred = xgb_model.predict(split.X_test)
        y_test_prob = xgb_model.predict_proba(split.X_test)[:, 1]

        eval_res = ModelEvaluator.evaluate_binary(
            y_true=split.y_test,
            y_pred=y_test_pred,
            y_prob=y_test_prob,
        )

        # Extract feature importances
        raw_importances = xgb_model.feature_importances_
        feature_imp_map = {
            name: round(float(imp), 4)
            for name, imp in zip(FEATURE_NAMES, raw_importances)
        }
        # Sort descending by importance
        sorted_imp = dict(sorted(feature_imp_map.items(), key=lambda item: item[1], reverse=True))

        # Serialize model artifact
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        artifact_filename = f"{version}.joblib"
        artifact_path = os.path.join(ARTIFACTS_DIR, artifact_filename)
        joblib.dump(xgb_model, artifact_path)

        return TrainingResult(
            model_id=model_id,
            model_version=version,
            algorithm="XGBOOST",
            feature_version="fv1",
            dataset_type=split.metadata.get("dataset_type", "SYNTHETIC_DEMO"),
            training_samples=len(split.X_train),
            metrics=eval_res.to_dict(),
            feature_importances=sorted_imp,
            artifact_path=artifact_path,
            model=xgb_model,
        )

    @classmethod
    def train_random_forest(
        cls,
        split: Optional[DatasetSplit] = None,
        model_version: Optional[str] = None,
        n_estimators: int = 100,
        max_depth: int = 8,
        random_seed: int = 42,
    ) -> TrainingResult:
        """
        Trains comparison Random Forest hazard classification baseline.
        """
        if split is None:
            df = HazardDatasetGenerator.generate_synthetic_corpus(n_samples=1200, random_seed=random_seed)
            split = HazardDatasetGenerator.create_train_val_test_split(df, random_seed=random_seed)

        model_id = str(uuid.uuid4())
        version = model_version or f"hazard-rf-v{uuid.uuid4().hex[:6]}"

        rf_model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_seed,
            class_weight="balanced",
        )

        rf_model.fit(split.X_train, split.y_train)

        # Evaluate on test split
        y_test_pred = rf_model.predict(split.X_test)
        y_test_prob = rf_model.predict_proba(split.X_test)[:, 1]

        eval_res = ModelEvaluator.evaluate_binary(
            y_true=split.y_test,
            y_pred=y_test_pred,
            y_prob=y_test_prob,
        )

        raw_importances = rf_model.feature_importances_
        feature_imp_map = {
            name: round(float(imp), 4)
            for name, imp in zip(FEATURE_NAMES, raw_importances)
        }
        sorted_imp = dict(sorted(feature_imp_map.items(), key=lambda item: item[1], reverse=True))

        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        artifact_filename = f"{version}.joblib"
        artifact_path = os.path.join(ARTIFACTS_DIR, artifact_filename)
        joblib.dump(rf_model, artifact_path)

        return TrainingResult(
            model_id=model_id,
            model_version=version,
            algorithm="RANDOM_FOREST",
            feature_version="fv1",
            dataset_type=split.metadata.get("dataset_type", "SYNTHETIC_DEMO"),
            training_samples=len(split.X_train),
            metrics=eval_res.to_dict(),
            feature_importances=sorted_imp,
            artifact_path=artifact_path,
            model=rf_model,
        )
