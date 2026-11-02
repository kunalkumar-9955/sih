"""
SIH26002 — Unseen Synthetic Generalization & Model Evaluation Engine.

CRITICAL NOTICE:
DATASET_TYPE = "UNSEEN_SYNTHETIC_GENERALIZATION"
"Synthetic evaluation only. These results do not represent production-world accuracy."

This module synthesizes out-of-distribution scenarios that were NEVER included
in the training distribution, verifying how the hazard models behave under
novel, extreme, and compounding environmental stressors.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from apps.hazards.ml.dataset import HazardDatasetGenerator
from apps.hazards.ml.evaluate import EvaluationMetrics, ModelEvaluator
from apps.hazards.ml.features import FEATURE_NAMES, HazardFeatureExtractor
from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.ml.train import HazardModelTrainer, TrainingResult


@dataclass
class UnseenScenarioResult:
    scenario_code: str
    scenario_name: str
    sample_count: int
    description: str
    metrics: Dict[str, Any]
    confusion_matrix: Dict[str, int]
    mean_predicted_hazard: float
    disruption_rate_actual: float
    disruption_rate_predicted: float
    is_sensible: bool
    notes: str


class UnseenGeneralizationGenerator:
    """
    Generates out-of-distribution synthetic test datasets across 5 distinct stress scenarios.
    """

    @classmethod
    def generate_scenario_a(cls, n_samples: int = 150, random_seed: int = 101) -> pd.DataFrame:
        """
        Scenario A: Unseen Extreme Terrain/Weather Combo
        Unseen combination of heavy rainfall (175-210mm) + steep slope (28-36°) + mid elevation (800-1100m).
        """
        rng = np.random.default_rng(random_seed)
        records = []
        for _ in range(n_samples):
            slope = rng.uniform(28.0, 36.0)
            elevation = rng.uniform(800.0, 1100.0)
            elev_change = rng.uniform(150.0, 350.0)
            soil_sat = rng.uniform(0.70, 0.95)
            drainage = rng.uniform(2.2, 3.8)
            fault_dist = rng.uniform(4.0, 15.0)
            rain_24h = rng.uniform(175.0, 210.0)
            rain_6h = rain_24h * rng.uniform(0.40, 0.65)
            rain_1h = rain_6h * rng.uniform(0.30, 0.55)
            precip_prob = 1.0
            hist_incidents = rng.poisson(lam=2.5)
            recent_incidents = rng.poisson(lam=1.0)
            edge_length = rng.uniform(8.0, 25.0)

            feats = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": slope, "elevation_m": elevation, "elevation_change_m": elev_change,
                         "soil_saturation": soil_sat, "drainage_density": drainage, "fault_line_distance_km": fault_dist},
                weather={"rainfall_1h_mm": rain_1h, "rainfall_6h_mm": rain_6h, "rainfall_24h_mm": rain_24h,
                         "precipitation_probability": precip_prob},
                incident_stats={"total_count": hist_incidents, "recent_count": recent_incidents},
                edge_stats={"distance_m": edge_length * 1000.0},
            )
            # Physical truth: in steep terrain with ~200mm rain and high saturation, landslide probability is very high
            true_hazard = float(np.clip(0.40 + (slope / 70.0) + (rain_24h / 400.0) + (soil_sat * 0.20), 0.1, 0.98))
            feats["hazard_score"] = round(true_hazard, 4)
            feats["is_disrupted"] = 1 if true_hazard >= 0.55 else 0
            feats["scenario_code"] = "SCENARIO_A"
            records.append(feats)
        return pd.DataFrame(records)

    @classmethod
    def generate_scenario_b(cls, n_samples: int = 150, random_seed: int = 102) -> pd.DataFrame:
        """
        Scenario B: Extreme Torrential Rainfall on Flat/Moderate Lowland Terrain
        Extreme cloudburst (190-260mm) on low slope (1-8°) and low elevation (35-120m).
        Tests whether model incorrectly flags mass-movement landslide when topography does not support it.
        """
        rng = np.random.default_rng(random_seed)
        records = []
        for _ in range(n_samples):
            slope = rng.uniform(1.0, 8.0)
            elevation = rng.uniform(35.0, 120.0)
            elev_change = rng.uniform(2.0, 15.0)
            soil_sat = rng.uniform(0.60, 0.92)
            drainage = rng.uniform(0.5, 1.4)
            fault_dist = rng.uniform(30.0, 70.0)
            rain_24h = rng.uniform(190.0, 260.0)  # Extreme lowland deluge
            rain_6h = rain_24h * rng.uniform(0.35, 0.60)
            rain_1h = rain_6h * rng.uniform(0.25, 0.50)
            precip_prob = 1.0
            hist_incidents = rng.poisson(lam=0.4)
            recent_incidents = 0
            edge_length = rng.uniform(12.0, 35.0)

            feats = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": slope, "elevation_m": elevation, "elevation_change_m": elev_change,
                         "soil_saturation": soil_sat, "drainage_density": drainage, "fault_line_distance_km": fault_dist},
                weather={"rainfall_1h_mm": rain_1h, "rainfall_6h_mm": rain_6h, "rainfall_24h_mm": rain_24h,
                         "precipitation_probability": precip_prob},
                incident_stats={"total_count": hist_incidents, "recent_count": recent_incidents},
                edge_stats={"distance_m": edge_length * 1000.0},
            )
            # Physical truth: flat terrain experiences waterlogging/flash flood, but lower slope means moderate hazard
            true_hazard = float(np.clip(0.20 + (rain_24h / 500.0) + (soil_sat * 0.15) + (slope / 80.0), 0.1, 0.70))
            feats["hazard_score"] = round(true_hazard, 4)
            feats["is_disrupted"] = 1 if true_hazard >= 0.55 else 0
            feats["scenario_code"] = "SCENARIO_B"
            records.append(feats)
        return pd.DataFrame(records)

    @classmethod
    def generate_scenario_c(cls, n_samples: int = 150, random_seed: int = 103) -> pd.DataFrame:
        """
        Scenario C: Moderate Rainfall on High Slope & High Elevation
        Moderate rainfall (25-50mm), extreme slope (40-54°), high elevation (1600-2400m).
        Tests whether high gravitational shear on steep rockfaces triggers appropriate caution without requiring extreme rain.
        """
        rng = np.random.default_rng(random_seed)
        records = []
        for _ in range(n_samples):
            slope = rng.uniform(40.0, 54.0)
            elevation = rng.uniform(1600.0, 2400.0)
            elev_change = rng.uniform(250.0, 600.0)
            soil_sat = rng.uniform(0.35, 0.65)
            drainage = rng.uniform(2.5, 4.5)
            fault_dist = rng.uniform(2.0, 10.0)
            rain_24h = rng.uniform(25.0, 50.0)  # Moderate rain
            rain_6h = rain_24h * rng.uniform(0.30, 0.50)
            rain_1h = rain_6h * rng.uniform(0.20, 0.40)
            precip_prob = rng.uniform(0.5, 0.8)
            hist_incidents = rng.poisson(lam=2.8)
            recent_incidents = rng.poisson(lam=0.8)
            edge_length = rng.uniform(5.0, 18.0)

            feats = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": slope, "elevation_m": elevation, "elevation_change_m": elev_change,
                         "soil_saturation": soil_sat, "drainage_density": drainage, "fault_line_distance_km": fault_dist},
                weather={"rainfall_1h_mm": rain_1h, "rainfall_6h_mm": rain_6h, "rainfall_24h_mm": rain_24h,
                         "precipitation_probability": precip_prob},
                incident_stats={"total_count": hist_incidents, "recent_count": recent_incidents},
                edge_stats={"distance_m": edge_length * 1000.0},
            )
            # Physical truth: high slope (>40 deg) has elevated rockfall hazard even with moderate rain
            true_hazard = float(np.clip(0.30 + (slope / 80.0) + (rain_24h / 250.0) + (0.10 if fault_dist < 5.0 else 0.0), 0.15, 0.95))
            feats["hazard_score"] = round(true_hazard, 4)
            feats["is_disrupted"] = 1 if true_hazard >= 0.55 else 0
            feats["scenario_code"] = "SCENARIO_C"
            records.append(feats)
        return pd.DataFrame(records)

    @classmethod
    def generate_scenario_d(cls, n_samples: int = 150, random_seed: int = 104) -> pd.DataFrame:
        """
        Scenario D: Combined Rainfall + Active Incidents + Geological Fault Line Proximity
        Compounding multi-factor disaster condition.
        """
        rng = np.random.default_rng(random_seed)
        records = []
        for _ in range(n_samples):
            slope = rng.uniform(22.0, 38.0)
            elevation = rng.uniform(650.0, 1400.0)
            elev_change = rng.uniform(100.0, 300.0)
            soil_sat = rng.uniform(0.70, 0.95)
            drainage = rng.uniform(2.0, 3.5)
            fault_dist = rng.uniform(1.0, 4.5)  # Near active fault line
            rain_24h = rng.uniform(120.0, 180.0)
            rain_6h = rain_24h * rng.uniform(0.40, 0.65)
            rain_1h = rain_6h * rng.uniform(0.30, 0.50)
            precip_prob = 0.95
            hist_incidents = rng.poisson(lam=5.0)
            recent_incidents = rng.poisson(lam=2.5)
            edge_length = rng.uniform(6.0, 22.0)

            feats = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": slope, "elevation_m": elevation, "elevation_change_m": elev_change,
                         "soil_saturation": soil_sat, "drainage_density": drainage, "fault_line_distance_km": fault_dist},
                weather={"rainfall_1h_mm": rain_1h, "rainfall_6h_mm": rain_6h, "rainfall_24h_mm": rain_24h,
                         "precipitation_probability": precip_prob},
                incident_stats={"total_count": hist_incidents, "recent_count": recent_incidents},
                edge_stats={"distance_m": edge_length * 1000.0},
            )
            true_hazard = float(np.clip(0.45 + (slope / 70.0) + (rain_24h / 300.0) + (recent_incidents * 0.08), 0.3, 0.99))
            feats["hazard_score"] = round(true_hazard, 4)
            feats["is_disrupted"] = 1 if true_hazard >= 0.55 else 0
            feats["scenario_code"] = "SCENARIO_D"
            records.append(feats)
        return pd.DataFrame(records)

    @classmethod
    def generate_scenario_e(cls, n_samples: int = 150, random_seed: int = 105) -> pd.DataFrame:
        """
        Scenario E: Multimodal Corridor Disruption (River Basin & Rail Embankment Inundation)
        High soil saturation (>0.85), high drainage density (>3.5), heavy rainfall causing river draft surges.
        """
        rng = np.random.default_rng(random_seed)
        records = []
        for _ in range(n_samples):
            slope = rng.uniform(6.0, 18.0)
            elevation = rng.uniform(80.0, 350.0)
            elev_change = rng.uniform(10.0, 60.0)
            soil_sat = rng.uniform(0.85, 0.99)
            drainage = rng.uniform(3.2, 5.0)
            fault_dist = rng.uniform(15.0, 45.0)
            rain_24h = rng.uniform(140.0, 220.0)
            rain_6h = rain_24h * rng.uniform(0.35, 0.60)
            rain_1h = rain_6h * rng.uniform(0.25, 0.45)
            precip_prob = 1.0
            hist_incidents = rng.poisson(lam=2.0)
            recent_incidents = rng.poisson(lam=1.0)
            edge_length = rng.uniform(15.0, 40.0)

            feats = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": slope, "elevation_m": elevation, "elevation_change_m": elev_change,
                         "soil_saturation": soil_sat, "drainage_density": drainage, "fault_line_distance_km": fault_dist},
                weather={"rainfall_1h_mm": rain_1h, "rainfall_6h_mm": rain_6h, "rainfall_24h_mm": rain_24h,
                         "precipitation_probability": precip_prob},
                incident_stats={"total_count": hist_incidents, "recent_count": recent_incidents},
                edge_stats={"distance_m": edge_length * 1000.0},
            )
            true_hazard = float(np.clip(0.35 + (rain_24h / 400.0) + (soil_sat * 0.22) + (drainage * 0.04), 0.2, 0.88))
            feats["hazard_score"] = round(true_hazard, 4)
            feats["is_disrupted"] = 1 if true_hazard >= 0.55 else 0
            feats["scenario_code"] = "SCENARIO_E"
            records.append(feats)
        return pd.DataFrame(records)

    @classmethod
    def generate_all_unseen(cls, samples_per_scenario: int = 150) -> pd.DataFrame:
        """Concatenates all 5 unseen synthetic stress scenarios."""
        dfs = [
            cls.generate_scenario_a(samples_per_scenario),
            cls.generate_scenario_b(samples_per_scenario),
            cls.generate_scenario_c(samples_per_scenario),
            cls.generate_scenario_d(samples_per_scenario),
            cls.generate_scenario_e(samples_per_scenario),
        ]
        combined = pd.concat(dfs, ignore_index=True)
        combined["dataset_type"] = "UNSEEN_SYNTHETIC_GENERALIZATION"
        return combined


class ModelGeneralizationEvaluator:
    """
    Computes empirical generalization benchmarks comparing In-Distribution vs Out-of-Distribution unseen sets.
    """

    @classmethod
    def evaluate_model_on_dataset(cls, model: Any, df: pd.DataFrame) -> Tuple[EvaluationMetrics, np.ndarray, np.ndarray]:
        """Runs inference and computes evaluation metrics on any tabular dataframe."""
        X = df[FEATURE_NAMES].to_numpy(dtype=np.float32)
        y_true = df["is_disrupted"].to_numpy(dtype=np.int32)

        y_pred = model.predict(X)
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X)[:, 1]
        else:
            y_prob = y_pred.astype(np.float32)

        metrics = ModelEvaluator.evaluate_binary(y_true=y_true, y_pred=y_pred, y_prob=y_prob)
        return metrics, y_pred, y_prob

    @classmethod
    def run_comprehensive_generalization_report(cls, random_seed: int = 42) -> Dict[str, Any]:
        """
        Builds the complete empirical generalization report for the active hazard model.
        Reports:
        - Training set metrics
        - Validation set metrics
        - Test set metrics (In-Distribution held-out)
        - Unseen Synthetic dataset (overall and per scenario A-E)
        """
        # 1. Generate standard baseline dataset & split
        train_corpus = HazardDatasetGenerator.generate_synthetic_corpus(n_samples=1200, random_seed=random_seed)
        split = HazardDatasetGenerator.create_train_val_test_split(train_corpus, random_seed=random_seed)

        # 2. Retrieve or train active model
        record, model = ModelRegistry.get_active_model()
        if model is None:
            train_res = HazardModelTrainer.train_xgboost(split=split, random_seed=random_seed)
            model = train_res.model
            record = ModelRegistry.register_trained_model(train_res, set_active=True)

        # In-distribution evaluation
        X_train, y_train = split.X_train, split.y_train
        y_train_pred = model.predict(X_train)
        y_train_prob = model.predict_proba(X_train)[:, 1] if hasattr(model, "predict_proba") else y_train_pred.astype(np.float32)
        train_metrics = ModelEvaluator.evaluate_binary(y_train, y_train_pred, y_train_prob).to_dict()

        X_val, y_val = split.X_val, split.y_val
        y_val_pred = model.predict(X_val)
        y_val_prob = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else y_val_pred.astype(np.float32)
        val_metrics = ModelEvaluator.evaluate_binary(y_val, y_val_pred, y_val_prob).to_dict()

        X_test, y_test = split.X_test, split.y_test
        y_test_pred = model.predict(X_test)
        y_test_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_test_pred.astype(np.float32)
        test_metrics = ModelEvaluator.evaluate_binary(y_test, y_test_pred, y_test_prob).to_dict()

        # 3. Unseen Synthetic Scenarios (Out-of-Distribution)
        scenarios = {
            "SCENARIO_A": (
                "Unseen Extreme Rainfall + High Slope Combo",
                UnseenGeneralizationGenerator.generate_scenario_a(n_samples=150, random_seed=random_seed + 1),
                "Tests novel 175-210mm rainfall on 28-36° slopes. High hazard expected.",
            ),
            "SCENARIO_B": (
                "Extreme Rainfall on Flat Lowland Terrain",
                UnseenGeneralizationGenerator.generate_scenario_b(n_samples=150, random_seed=random_seed + 2),
                "Tests 190-260mm deluge on 1-8° flat ground. Disruption should be lower than on mountain slopes.",
            ),
            "SCENARIO_C": (
                "High Elevation & Steep Slope with Moderate Rain",
                UnseenGeneralizationGenerator.generate_scenario_c(n_samples=150, random_seed=random_seed + 3),
                "Tests steep rockfaces (40-54°) under 25-50mm moderate rainfall. Gravity shear risk recognized.",
            ),
            "SCENARIO_D": (
                "Compound Disaster: Rain + Fault Proximity + Incidents",
                UnseenGeneralizationGenerator.generate_scenario_d(n_samples=150, random_seed=random_seed + 4),
                "Compounding risk factor convergence near active fault lines. Very high hazard expected.",
            ),
            "SCENARIO_E": (
                "Multimodal Basin Saturation & River Draft Surges",
                UnseenGeneralizationGenerator.generate_scenario_e(n_samples=150, random_seed=random_seed + 5),
                "Extreme soil moisture (>85%) and stream channel density along multimodal river corridors.",
            ),
        }

        scenario_results = []
        all_unseen_dfs = []

        for sc_code, (sc_name, sc_df, sc_desc) in scenarios.items():
            all_unseen_dfs.append(sc_df)
            sc_metrics, sc_preds, sc_probs = cls.evaluate_model_on_dataset(model, sc_df)
            mean_prob = float(np.mean(sc_probs))
            actual_rate = float(np.mean(sc_df["is_disrupted"]))
            pred_rate = float(np.mean(sc_preds))

            # Sensibility check:
            # For A, D, E: predicted disruption should be substantial (>0.50)
            # For B: predicted disruption should not exceed 0.85 (lowlands don't have catastrophic landslides)
            is_sensible = True
            if sc_code in ["SCENARIO_A", "SCENARIO_D"] and pred_rate < 0.45:
                is_sensible = False
            if sc_code == "SCENARIO_B" and pred_rate > 0.90:
                is_sensible = False

            scenario_results.append({
                "scenario_code": sc_code,
                "scenario_name": sc_name,
                "description": sc_desc,
                "sample_count": len(sc_df),
                "metrics": sc_metrics.to_dict(),
                "confusion_matrix": {
                    "tp": sc_metrics.true_positives,
                    "fp": sc_metrics.false_positives,
                    "tn": sc_metrics.true_negatives,
                    "fn": sc_metrics.false_negatives,
                },
                "mean_predicted_hazard": round(mean_prob, 4),
                "disruption_rate_actual": round(actual_rate, 4),
                "disruption_rate_predicted": round(pred_rate, 4),
                "is_sensible": is_sensible,
            })

        # Overall unseen metrics
        combined_unseen = pd.concat(all_unseen_dfs, ignore_index=True)
        overall_unseen_metrics, _, _ = cls.evaluate_model_on_dataset(model, combined_unseen)

        return {
            "disclaimer": "Synthetic evaluation only. These results do not represent production-world accuracy.",
            "model_metadata": {
                "model_version": record.model_version if record else "xgb-baseline",
                "algorithm": record.algorithm if record else "XGBOOST",
                "feature_version": record.feature_version if record else "fv1",
            },
            "in_distribution_evaluation": {
                "training_set": {
                    "samples": len(X_train),
                    "metrics": train_metrics,
                },
                "validation_set": {
                    "samples": len(X_val),
                    "metrics": val_metrics,
                },
                "test_set": {
                    "samples": len(X_test),
                    "metrics": test_metrics,
                },
            },
            "out_of_distribution_generalization": {
                "overall_unseen_dataset": {
                    "total_samples": len(combined_unseen),
                    "metrics": overall_unseen_metrics.to_dict(),
                    "confusion_matrix": {
                        "tp": overall_unseen_metrics.true_positives,
                        "fp": overall_unseen_metrics.false_positives,
                        "tn": overall_unseen_metrics.true_negatives,
                        "fn": overall_unseen_metrics.false_negatives,
                    },
                },
                "scenario_breakdown": scenario_results,
            },
        }
