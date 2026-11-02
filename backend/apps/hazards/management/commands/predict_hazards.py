"""
SIH26002 — Predict Hazards Management Command.

Runs vectorized model inference across all active transport edges, computes
hazard index H, assigns severity, and persists versioned HazardScore records.
"""
from django.core.management.base import BaseCommand

from apps.hazards.models import HazardScore, HazardSeverity
from apps.hazards.services.prediction_service import HazardPredictionService
from apps.transport_graph.models import TransportEdge


class Command(BaseCommand):
    help = "Runs hazard inference across transport edges and updates operational risk scores"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync-edge-scores",
            action="store_true",
            default=True,
            help="Synchronize predicted hazard score directly into TransportEdge.hazard_score",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Running corridor hazard inference..."))

        edges = list(TransportEdge.objects.filter(is_available=True).select_related("source_node", "target_node"))
        if not edges:
            self.stdout.write(self.style.WARNING("No active edges found in database."))
            return

        service = HazardPredictionService()
        predictions = service.bulk_predict_edges(edges, persist_scores=True)

        counts = {
            HazardSeverity.LOW: 0,
            HazardSeverity.MODERATE: 0,
            HazardSeverity.HIGH: 0,
            HazardSeverity.CRITICAL: 0,
        }

        # Sync back to TransportEdge models so baseline queries also see latest score
        if options["sync_edge_scores"]:
            for e, pred in zip(edges, predictions):
                e.hazard_score = pred.hazard_index
                e.save(update_fields=["hazard_score"])
                counts[pred.severity] += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully generated predictions for {len(predictions)} edges."))
        self.stdout.write(f"  LOW Risk:      {counts[HazardSeverity.LOW]}")
        self.stdout.write(f"  MODERATE Risk: {counts[HazardSeverity.MODERATE]}")
        self.stdout.write(f"  HIGH Risk:     {counts[HazardSeverity.HIGH]}")
        self.stdout.write(f"  CRITICAL Risk: {counts[HazardSeverity.CRITICAL]}")
