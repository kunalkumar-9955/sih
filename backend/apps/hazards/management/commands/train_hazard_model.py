"""
SIH26002 — Train Hazard Model Management Command.

Executes baseline XGBoost or Random Forest model training on the reproducible
development dataset, measures actual test metrics, and registers the artifact.
"""
from django.core.management.base import BaseCommand

from apps.hazards.ml.dataset import HazardDatasetGenerator
from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.ml.train import HazardModelTrainer


class Command(BaseCommand):
    help = "Trains and registers baseline hazard prediction ML model (XGBoost / Random Forest)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--algorithm",
            type=str,
            default="XGBOOST",
            choices=["XGBOOST", "RANDOM_FOREST"],
            help="Algorithm baseline to train (default: XGBOOST)",
        )
        parser.add_argument(
            "--n_samples",
            type=int,
            default=1200,
            help="Number of synthetic development training samples (default: 1200)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic generation and splitting",
        )

    def handle(self, *args, **options):
        algo = options["algorithm"].upper()
        n_samples = options["n_samples"]
        seed = options["seed"]

        self.stdout.write(self.style.NOTICE(f"Generating synthetic development dataset (n={n_samples}, seed={seed})..."))
        df = HazardDatasetGenerator.generate_synthetic_corpus(n_samples=n_samples, random_seed=seed)
        split = HazardDatasetGenerator.create_train_val_test_split(df, random_seed=seed)

        self.stdout.write(f"Dataset split: Train={len(split.X_train)}, Val={len(split.X_val)}, Test={len(split.X_test)}")
        self.stdout.write(self.style.NOTICE(f"Training {algo} model..."))

        if algo == "RANDOM_FOREST":
            res = HazardModelTrainer.train_random_forest(split=split, random_seed=seed)
        else:
            res = HazardModelTrainer.train_xgboost(split=split, random_seed=seed)

        # Register in ModelRegistry
        record = ModelRegistry.register_trained_model(res, set_active=True)

        self.stdout.write(self.style.SUCCESS(f"\nModel Training Complete: {res.model_version}"))
        self.stdout.write(f"Algorithm:           {res.algorithm}")
        self.stdout.write(f"Artifact Path:       {res.artifact_path}")
        self.stdout.write(f"Training Samples:    {res.training_samples}")
        self.stdout.write(f"Test Samples:        {res.metrics.get('total_test_samples')}")
        self.stdout.write("-" * 50)
        self.stdout.write("ACTUAL TEST EVALUATION METRICS (Measured, not fabricated):")
        self.stdout.write(f"  Accuracy:          {res.metrics.get('accuracy'):.4f}")
        self.stdout.write(f"  Precision:         {res.metrics.get('precision'):.4f}")
        self.stdout.write(f"  Recall:            {res.metrics.get('recall'):.4f}")
        self.stdout.write(f"  F1-Score:          {res.metrics.get('f1'):.4f}")
        self.stdout.write(f"  ROC-AUC:           {res.metrics.get('roc_auc'):.4f}")
        self.stdout.write(f"  PR-AUC:            {res.metrics.get('pr_auc'):.4f}")
        self.stdout.write(f"  False Negatives:   {res.metrics.get('false_negatives')} (Rate: {res.metrics.get('false_negative_rate'):.4f})")
        self.stdout.write("-" * 50)
        self.stdout.write("TOP 5 CONTRIBUTING FEATURES:")
        for idx, (fname, fimp) in enumerate(list(res.feature_importances.items())[:5], 1):
            self.stdout.write(f"  {idx}. {fname}: {fimp:.4f}")

        self.stdout.write(self.style.WARNING("\nDISCLAIMER:"))
        self.stdout.write(
            "DATASET_TYPE = SYNTHETIC_DEMO. The metrics above were measured on a procedurally generated "
            "development dataset. They confirm end-to-end pipeline integrity but must NOT be claimed as representative "
            "of real-world operational accuracy without real geological validation."
        )
