"""
SIH26002 — Hazard Intelligence Celery Background Tasks.

Scheduled pipelines for periodic weather ingestion, ML risk recalculation,
and stale score detection.
"""
import logging
from celery import shared_task
from django.utils import timezone

from apps.hazards.services.prediction_service import HazardPredictionService
from apps.transport_graph.models import TransportEdge

logger = logging.getLogger("sih.hazards.tasks")


@shared_task(name="apps.hazards.tasks.refresh_corridor_hazards")
def refresh_corridor_hazards():
    """
    Periodic task: re-evaluates meteorological features and generates fresh
    hazard scores for all active transport edges.
    """
    logger.info("Starting scheduled corridor hazard refresh...")
    edges = list(TransportEdge.objects.filter(is_available=True))
    if not edges:
        logger.info("No active transport edges found.")
        return {"status": "no_edges"}

    service = HazardPredictionService()
    results = service.bulk_predict_edges(edges, persist_scores=True)

    # Synchronize score to TransportEdge models
    for e, res in zip(edges, results):
        e.hazard_score = res.hazard_index
        e.save(update_fields=["hazard_score"])

    logger.info(f"Refreshed hazard predictions for {len(results)} edges.")
    return {
        "status": "success",
        "edges_updated": len(results),
        "timestamp": timezone.now().isoformat(),
    }
