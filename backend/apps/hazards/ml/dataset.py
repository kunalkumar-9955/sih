"""
SIH26002 — Reproducible Development Hazard Dataset Generator.

CRITICAL NOTICE:
DATASET_TYPE = "SYNTHETIC_DEMO"
This dataset contains procedurally generated training and evaluation records modeled
after physical geomorphological and monsoon rainfall conditions in the North Eastern Region.
It is explicitly labeled as synthetic development data for platform verification.
Metrics generated on this dataset must NOT be claimed as representative of real-world operational accuracy.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .features import FEATURE_NAMES, HazardFeatureExtractor

DATASET_TYPE = "SYNTHETIC_DEMO"


@dataclass
class DatasetSplit:
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    feature_names: List[str]
    metadata: Dict[str, str]


class HazardDatasetGenerator:
    """
    Generates deterministic, physically grounded synthetic datasets for training
    and evaluating baseline XGBoost and Random Forest models.
    """

    @classmethod
    def generate_synthetic_corpus(
        cls,
        n_samples: int = 1200,
        random_seed: int = 42,
    ) -> pd.DataFrame:
        """
        Synthesizes realistic multimodal logistics records for NER terrain sectors.
        """
        rng = np.random.default_rng(random_seed)

        records = []
        for i in range(n_samples):
            # Sector archetype: 0=Plain Valley (Assam Brahmaputra valley),
            # 1=Foothill/Rolling hills (Meghalaya Plateau transition),
            # 2=Steep Mountain Pass (Khasi/Jaintia hills / NH-6 Sonapur pass),
            # 3=Extreme Monsoon Landslide Corridor
            archetype = rng.choice([0, 1, 2, 3], p=[0.40, 0.25, 0.25, 0.10])

            if archetype == 0:  # Plains
                slope = rng.uniform(0.5, 6.0)
                elevation = rng.uniform(40.0, 150.0)
                elev_change = rng.uniform(2.0, 15.0)
                soil_sat = rng.uniform(0.15, 0.65)
                drainage = rng.uniform(0.4, 1.2)
                fault_dist = rng.uniform(20.0, 60.0)
                rain_24h = rng.exponential(scale=18.0)
                hist_incidents = rng.poisson(lam=0.3)
                recent_incidents = 1 if (hist_incidents > 0 and rng.random() < 0.2) else 0

            elif archetype == 1:  # Foothills
                slope = rng.uniform(6.0, 16.0)
                elevation = rng.uniform(150.0, 600.0)
                elev_change = rng.uniform(20.0, 120.0)
                soil_sat = rng.uniform(0.25, 0.75)
                drainage = rng.uniform(1.0, 2.2)
                fault_dist = rng.uniform(10.0, 35.0)
                rain_24h = rng.exponential(scale=35.0)
                hist_incidents = rng.poisson(lam=1.2)
                recent_incidents = rng.poisson(lam=0.4)

            elif archetype == 2:  # Steep Mountain Pass
                slope = rng.uniform(16.0, 38.0)
                elevation = rng.uniform(600.0, 1850.0)
                elev_change = rng.uniform(80.0, 450.0)
                soil_sat = rng.uniform(0.40, 0.90)
                drainage = rng.uniform(1.8, 3.8)
                fault_dist = rng.uniform(3.0, 18.0)
                rain_24h = rng.exponential(scale=65.0)
                hist_incidents = rng.poisson(lam=3.5)
                recent_incidents = rng.poisson(lam=1.1)

            else:  # Extreme active monsoon disaster scenario
                slope = rng.uniform(25.0, 52.0)
                elevation = rng.uniform(800.0, 2100.0)
                elev_change = rng.uniform(150.0, 650.0)
                soil_sat = rng.uniform(0.75, 0.98)
                drainage = rng.uniform(2.5, 4.5)
                fault_dist = rng.uniform(1.0, 8.0)
                rain_24h = rng.uniform(110.0, 280.0)  # Extreme cloudburst / torrential rain
                hist_incidents = rng.poisson(lam=6.0)
                recent_incidents = rng.poisson(lam=2.5)

            rain_6h = rain_24h * rng.uniform(0.25, 0.65)
            rain_1h = rain_6h * rng.uniform(0.20, 0.55)
            precip_prob = min(1.0, (rain_24h / 120.0) + 0.1)

            edge_length = rng.uniform(4.0, 35.0)

            raw_dict = HazardFeatureExtractor.extract_from_raw(
                terrain={
                    "slope_deg": slope,
                    "elevation_m": elevation,
                    "elevation_change_m": elev_change,
                    "soil_saturation": soil_sat,
                    "drainage_density": drainage,
                    "fault_line_distance_km": fault_dist,
                },
                weather={
                    "rainfall_1h_mm": rain_1h,
                    "rainfall_6h_mm": rain_6h,
                    "rainfall_24h_mm": rain_24h,
                    "precipitation_probability": precip_prob,
                },
                incident_stats={
                    "total_count": hist_incidents,
                    "recent_count": recent_incidents,
                },
                edge_stats={
                    "distance_m": edge_length * 1000.0,
                },
            )

            # Ground truth calculation using physically consistent landslide/washout hazard potential:
            # Hazard increases with slope gradient, soil moisture saturation, intense antecedent rainfall,
            # and historical instability, mitigated by fault distance.
            slope_factor = min(1.0, slope / 40.0) ** 1.5
            rain_factor = min(1.0, rain_24h / 150.0)
            intense_factor = min(1.0, rain_1h / 30.0)
            soil_factor = soil_sat ** 1.3
            history_factor = min(1.0, (hist_incidents * 0.15) + (recent_incidents * 0.25))
            fault_penalty = max(0.0, (25.0 - fault_dist) / 25.0)

            # Combined risk formula with small stochastic noise
            raw_risk = (
                0.28 * slope_factor +
                0.26 * rain_factor +
                0.16 * soil_factor +
                0.12 * intense_factor +
                0.12 * history_factor +
                0.06 * fault_penalty +
                rng.normal(0.0, 0.03)
            )
            hazard_score = float(np.clip(raw_risk, 0.01, 0.99))
            is_disrupted = 1 if hazard_score >= 0.55 else 0

            raw_dict["hazard_score"] = round(hazard_score, 4)
            raw_dict["is_disrupted"] = is_disrupted
            raw_dict["dataset_type"] = DATASET_TYPE
            records.append(raw_dict)

        return pd.DataFrame(records)

    @classmethod
    def create_train_val_test_split(
        cls,
        df: pd.DataFrame,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
    ) -> DatasetSplit:
        """
        Splits dataset deterministically into Train, Validation, and Test sets.
        """
        rng = np.random.default_rng(random_seed)
        shuffled_indices = rng.permutation(len(df))

        n_total = len(df)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)

        train_idx = shuffled_indices[:n_train]
        val_idx = shuffled_indices[n_train:n_train + n_val]
        test_idx = shuffled_indices[n_train + n_val:]

        features = FEATURE_NAMES
        X_train = df.iloc[train_idx][features].to_numpy(dtype=np.float32)
        y_train = df.iloc[train_idx]["is_disrupted"].to_numpy(dtype=np.int32)

        X_val = df.iloc[val_idx][features].to_numpy(dtype=np.float32)
        y_val = df.iloc[val_idx]["is_disrupted"].to_numpy(dtype=np.int32)

        X_test = df.iloc[test_idx][features].to_numpy(dtype=np.float32)
        y_test = df.iloc[test_idx]["is_disrupted"].to_numpy(dtype=np.int32)

        metadata = {
            "dataset_type": DATASET_TYPE,
            "total_samples": str(n_total),
            "train_samples": str(len(train_idx)),
            "val_samples": str(len(val_idx)),
            "test_samples": str(len(test_idx)),
            "disrupted_prevalence": f"{df['is_disrupted'].mean():.3f}",
        }

        return DatasetSplit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            y_test=y_test,
            feature_names=features,
            metadata=metadata,
        )
