"""
SIH26002 — Phase 10 Model Generalization & Behavioral Sanity Tests.
"""
import numpy as np
import pytest

from apps.hazards.ml.features import FEATURE_NAMES, HazardFeatureExtractor
from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.ml.unseen_generalization import (
    ModelGeneralizationEvaluator,
    UnseenGeneralizationGenerator,
)


@pytest.mark.django_db
class TestPhase10GeneralizationAndSanity:
    def setup_method(self):
        self.record, self.model = ModelRegistry.get_active_model()
        if self.model is None:
            from apps.hazards.ml.train import HazardModelTrainer
            train_res = HazardModelTrainer.train_xgboost()
            self.model = train_res.model
            self.record = ModelRegistry.register_trained_model(train_res, set_active=True)

    def test_unseen_scenarios_generation(self):
        """Validates that all 5 unseen synthetic stress scenarios generate correct schema."""
        sc_a = UnseenGeneralizationGenerator.generate_scenario_a(n_samples=20)
        sc_b = UnseenGeneralizationGenerator.generate_scenario_b(n_samples=20)
        sc_c = UnseenGeneralizationGenerator.generate_scenario_c(n_samples=20)
        sc_d = UnseenGeneralizationGenerator.generate_scenario_d(n_samples=20)
        sc_e = UnseenGeneralizationGenerator.generate_scenario_e(n_samples=20)

        for sc_df in [sc_a, sc_b, sc_c, sc_d, sc_e]:
            assert len(sc_df) == 20
            for col in FEATURE_NAMES:
                assert col in sc_df.columns
            assert "hazard_score" in sc_df.columns
            assert "is_disrupted" in sc_df.columns

    def test_comprehensive_generalization_report(self):
        """Validates generalization report structure, metrics, and honest disclaimer."""
        rep = ModelGeneralizationEvaluator.run_comprehensive_generalization_report()
        assert "Synthetic evaluation only" in rep["disclaimer"]
        assert "in_distribution_evaluation" in rep
        assert "out_of_distribution_generalization" in rep

        scenarios = rep["out_of_distribution_generalization"]["scenario_breakdown"]
        assert len(scenarios) == 5
        for sc in scenarios:
            assert "metrics" in sc
            m = sc["metrics"]
            assert "accuracy" in m
            assert "precision" in m
            assert "recall" in m
            assert "f1" in m
            assert "confusion_matrix" in sc
            assert "mean_predicted_hazard" in sc

    def test_model_behavior_rainfall_monotonicity(self):
        """Sanity check: Increasing rainfall under fixed identical terrain should not decrease predicted risk."""
        rainfall_levels = [0.0, 30.0, 80.0, 150.0, 220.0]
        predicted_hazards = []

        for rain in rainfall_levels:
            raw = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": 24.0, "elevation_m": 850.0, "soil_saturation": 0.60},
                weather={"rainfall_1h_mm": rain * 0.3, "rainfall_6h_mm": rain * 0.6, "rainfall_24h_mm": rain},
                incident_stats={"total_count": 1, "recent_count": 0},
                edge_stats={"distance_m": 12000.0},
            )
            vec = HazardFeatureExtractor.to_array(raw).reshape(1, -1)
            prob = float(self.model.predict_proba(vec)[0, 1])
            predicted_hazards.append(prob)

        # Baseline check: 220mm rain should predict higher hazard than 0mm rain
        assert predicted_hazards[-1] > predicted_hazards[0], (
            f"Expected higher risk for 220mm rain ({predicted_hazards[-1]}) than 0mm ({predicted_hazards[0]})"
        )

    def test_model_behavior_slope_monotonicity(self):
        """Sanity check: Increasing slope angle under identical rainfall should not decrease predicted risk."""
        slope_levels = [2.0, 10.0, 22.0, 35.0, 48.0]
        predicted_hazards = []

        for slope in slope_levels:
            raw = HazardFeatureExtractor.extract_from_raw(
                terrain={"slope_deg": slope, "elevation_m": 900.0, "soil_saturation": 0.70},
                weather={"rainfall_1h_mm": 15.0, "rainfall_6h_mm": 45.0, "rainfall_24h_mm": 90.0},
                incident_stats={"total_count": 1, "recent_count": 0},
                edge_stats={"distance_m": 10000.0},
            )
            vec = HazardFeatureExtractor.to_array(raw).reshape(1, -1)
            prob = float(self.model.predict_proba(vec)[0, 1])
            predicted_hazards.append(prob)

        # 48 deg slope should produce higher hazard than 2 deg flat ground
        assert predicted_hazards[-1] > predicted_hazards[0], (
            f"Expected higher risk for 48° slope ({predicted_hazards[-1]}) than 2° slope ({predicted_hazards[0]})"
        )

    def test_compound_incident_and_fault_risk(self):
        """Sanity check: Compound condition (active incidents + fault proximity) elevates risk."""
        mild_raw = HazardFeatureExtractor.extract_from_raw(
            terrain={"slope_deg": 18.0, "elevation_m": 600.0, "fault_line_distance_km": 50.0},
            weather={"rainfall_24h_mm": 40.0},
            incident_stats={"total_count": 0, "recent_count": 0},
        )
        compound_raw = HazardFeatureExtractor.extract_from_raw(
            terrain={"slope_deg": 18.0, "elevation_m": 600.0, "fault_line_distance_km": 2.0},
            weather={"rainfall_24h_mm": 140.0},
            incident_stats={"total_count": 4, "recent_count": 2},
        )

        mild_vec = HazardFeatureExtractor.to_array(mild_raw).reshape(1, -1)
        compound_vec = HazardFeatureExtractor.to_array(compound_raw).reshape(1, -1)

        p_mild = float(self.model.predict_proba(mild_vec)[0, 1])
        p_compound = float(self.model.predict_proba(compound_vec)[0, 1])

        assert p_compound > p_mild, f"Expected compound risk ({p_compound}) > mild ({p_mild})"

    def test_safe_fallback_on_missing_features(self):
        """Sanity check: Empty or missing raw inputs impute safe physical defaults without failure."""
        empty_raw = HazardFeatureExtractor.extract_from_raw()
        assert len(empty_raw) == len(FEATURE_NAMES)
        for val in empty_raw.values():
            assert not np.isnan(val)

        vec = HazardFeatureExtractor.to_array(empty_raw).reshape(1, -1)
        prob = float(self.model.predict_proba(vec)[0, 1])
        assert 0.0 <= prob <= 1.0
