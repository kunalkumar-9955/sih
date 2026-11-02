"""
SIH26002 — Evaluate Hazard Model Management Command.

Evaluates registered active or specified model against test partition,
displays confusion matrix, false negative breakdown, and ROC/PR AUC curves.
"""
from django.core.management.base import BaseCommand

from apps.hazards.ml.dataset import HazardDatasetGenerator
from apps.hazards.ml.evaluate import ModelEvaluator
from apps.hazards.ml.model_registry import ModelRegistry
from apps.hazards.models import HazardModelRecord


class Command(BaseCommand):
    help = "Evaluates active or specific hazard model against test data partition"

    def add_arguments(self, parser):
        parser.add_argument(
            "--version",
            type=str,
            default=None,
            help="Specific model_version to evaluate (default: active model)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for test split generation",
        )

    def handle(self, *args, **options):
        version = options["version"]
        seed = options["seed"]

        if version:
            record = HazardModelRecord.objects.filter(model_version=version).first()
            if not record:
                self.stdout.write(self.style.ERROR(f"Model version {version} not found."))
                return
            estimator = ModelRegistry.load_model_artifact(record.artifact_path)
        else:
            record, estimator = ModelRegistry.get_active_model()

        if not record or estimator is None:
            self.stdout.write(self.style.ERROR("No model available to evaluate. Run 'python manage.py train_hazard_model' first."))
            return

        self.stdout.write(self.style.NOTICE(f"Evaluating Model: {record.model_version} ({record.algorithm})..."))

        df = HazardDatasetGenerator.generate_synthetic_corpus(n_samples=1200, random_seed=seed)
        split = HazardDatasetGenerator.create_train_val_test_split(df, random_seed=seed)

        y_pred = estimator.predict(split.X_test)
        y_prob = estimator.predict_proba(split.X_test)[:, 1]

        metrics = ModelEvaluator.evaluate_binary(
            y_true=split.y_test,
            y_pred=y_pred,
            y_prob=y_prob,
        )

        res = metrics.to_dict()
        self.stdout.write("EVALUATION RESULTS ON TEST SPLIT:")
        self.stdout.write("-" * 50)
        self.stdout.write(f"Total Test Records:     {res['total_test_samples']}")
        self.stdout.write(f"Accuracy:               {res['accuracy']:.4f}")
        self.stdout.write(f"Precision:              {res['precision']:.4f}")
        self.stdout.write(f"Recall:                 {res['recall']:.4f}")
        self.stdout.write(f"F1-Score:               {res['f1']:.4f}")
        self.stdout.write(f"ROC-AUC:                {res['roc_auc']:.4f}")
        self.stdout.write(f"PR-AUC:                 {res['pr_auc']:.4f}")
        self.stdout.write("-" * 50)
        self.stdout.write("CONFUSION MATRIX:")
        self.stdout.write(f"  True Positives (TP):  {res['true_positives']}")
        self.stdout.write(f"  False Positives (FP): {res['false_positives']}")
        self.stdout.write(f"  True Negatives (TN):  {res['true_negatives']}")
        self.stdout.write(f"  False Negatives (FN): {res['false_negatives']} (Missed Hazard Rate: {res['false_negative_rate']:.4f})")
        self.stdout.write("-" * 50)
        self.stdout.write(self.style.WARNING("DATASET_TYPE = SYNTHETIC_DEMO. Actual measured test metrics."))
