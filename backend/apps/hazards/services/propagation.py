"""
SIH26002 — Hazard Propagation Service.

Propagates localized hazard shocks (e.g. landslides, flash floods, washouts)
across the transport network using spatial graph-hop distance decay.
"""
import logging
from typing import Any, Dict, List, Optional, Set
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.hazards.models import HazardScore, HazardSeverity
from apps.transport_graph.models import TransportEdge

logger = logging.getLogger("sih.hazards.propagation")


class HazardPropagationService:
    """
    Simulates physical propagation of disaster risks along connected road/rail
    corridors using network-topology hop decay.
    """

    def __init__(
        self,
        one_hop_decay: Optional[float] = None,
        two_hop_decay: Optional[float] = None,
    ):
        sih_settings = getattr(settings, "SIH_SETTINGS", {})
        self.one_hop_decay = (
            one_hop_decay
            if one_hop_decay is not None
            else sih_settings.get("HAZARD_PROPAGATION_1HOP_DECAY", 0.60)
        )
        self.two_hop_decay = (
            two_hop_decay
            if two_hop_decay is not None
            else sih_settings.get("HAZARD_PROPAGATION_2HOP_DECAY", 0.25)
        )

    def propagate_edge_hazard(
        self,
        source_edge: TransportEdge,
        source_hazard: Optional[float] = None,
        max_hops: int = 2,
        sync_edge_field: bool = True,
    ) -> Dict[str, Any]:
        """
        Propagates hazard from source_edge to 1-hop and 2-hop neighbor edges.

        Parameters
        ----------
        source_edge: TransportEdge
            The edge where the hazard originated or was detected.
        source_hazard: Optional[float]
            Hazard score to propagate. If None, uses source_edge.hazard_score.
        max_hops: int
            Maximum topological hops (default: 2).
        sync_edge_field: bool
            If True, directly updates TransportEdge.hazard_score field.
        """
        if source_hazard is None:
            source_hazard = float(source_edge.hazard_score or 0.0)

        source_hazard = max(0.0, min(1.0, float(source_hazard)))
        now = timezone.now()

        # Track visited edge IDs to prevent cycles and self-propagation
        visited_edge_ids: Set[str] = {str(source_edge.id)}
        affected_summary: Dict[str, List[Dict[str, Any]]] = {
            "1_hop": [],
            "2_hop": [],
        }

        # ── Find 1-Hop Neighbor Edges ─────────────────────────────────────────
        # Edges sharing either source_node or target_node with source_edge
        node_ids = [source_edge.source_node_id, source_edge.target_node_id]
        one_hop_edges = list(
            TransportEdge.objects.filter(is_available=True)
            .filter(source_node_id__in=node_ids)
            .exclude(id=source_edge.id)
            .select_related("source_node", "target_node")
        )
        # Also include incoming edges meeting at these nodes
        one_hop_incoming = list(
            TransportEdge.objects.filter(is_available=True)
            .filter(target_node_id__in=node_ids)
            .exclude(id=source_edge.id)
            .select_related("source_node", "target_node")
        )
        # Deduplicate 1-hop pool
        one_hop_pool: Dict[str, TransportEdge] = {}
        for e in one_hop_edges + one_hop_incoming:
            if str(e.id) not in visited_edge_ids:
                one_hop_pool[str(e.id)] = e
                visited_edge_ids.add(str(e.id))

        h1_score = round(source_hazard * self.one_hop_decay, 4)

        for edge_id, edge in one_hop_pool.items():
            updated = self._apply_propagated_score(
                edge=edge,
                propagated_score=h1_score,
                hop=1,
                decay=self.one_hop_decay,
                source_edge=source_edge,
                sync_edge_field=sync_edge_field,
                now=now,
            )
            affected_summary["1_hop"].append({
                "edge_id": str(edge.id),
                "corridor": f"{edge.source_node.name} → {edge.target_node.name}",
                "propagated_score": h1_score,
                "updated": updated,
            })

        # ── Find 2-Hop Neighbor Edges ─────────────────────────────────────────
        if max_hops >= 2 and one_hop_pool:
            two_hop_node_ids = set()
            for e in one_hop_pool.values():
                two_hop_node_ids.add(e.source_node_id)
                two_hop_node_ids.add(e.target_node_id)

            two_hop_edges = list(
                TransportEdge.objects.filter(is_available=True)
                .filter(source_node_id__in=two_hop_node_ids)
                .exclude(id__in=visited_edge_ids)
                .select_related("source_node", "target_node")
            )
            two_hop_incoming = list(
                TransportEdge.objects.filter(is_available=True)
                .filter(target_node_id__in=two_hop_node_ids)
                .exclude(id__in=visited_edge_ids)
                .select_related("source_node", "target_node")
            )

            two_hop_pool: Dict[str, TransportEdge] = {}
            for e in two_hop_edges + two_hop_incoming:
                if str(e.id) not in visited_edge_ids:
                    two_hop_pool[str(e.id)] = e
                    visited_edge_ids.add(str(e.id))

            h2_score = round(source_hazard * self.two_hop_decay, 4)

            for edge_id, edge in two_hop_pool.items():
                updated = self._apply_propagated_score(
                    edge=edge,
                    propagated_score=h2_score,
                    hop=2,
                    decay=self.two_hop_decay,
                    source_edge=source_edge,
                    sync_edge_field=sync_edge_field,
                    now=now,
                )
                affected_summary["2_hop"].append({
                    "edge_id": str(edge.id),
                    "corridor": f"{edge.source_node.name} → {edge.target_node.name}",
                    "propagated_score": h2_score,
                    "updated": updated,
                })

        return {
            "source_edge_id": str(source_edge.id),
            "source_hazard": source_hazard,
            "one_hop_count": len(affected_summary["1_hop"]),
            "two_hop_count": len(affected_summary["2_hop"]),
            "affected": affected_summary,
            "propagated_at": now.isoformat(),
        }

    def _apply_propagated_score(
        self,
        edge: TransportEdge,
        propagated_score: float,
        hop: int,
        decay: float,
        source_edge: TransportEdge,
        sync_edge_field: bool,
        now: Any,
    ) -> bool:
        """
        Applies propagated score only if it exceeds edge's current hazard score.
        Never downgrades existing ML inference or manual overrides.
        """
        current_score = float(edge.hazard_score or 0.0)
        if propagated_score <= current_score:
            # Existing score is already higher or equal; do not overwrite
            return False

        with transaction.atomic():
            # Mark previous active scores as superseded
            HazardScore.objects.filter(edge=edge, is_current=True).update(is_current=False)

            HazardScore.objects.create(
                edge=edge,
                hazard_index=propagated_score,
                confidence=0.70,
                severity=HazardSeverity.classify(propagated_score),
                model_version="propagation-v1",
                feature_version="prop_graph",
                predicted_at=now,
                source="weather_propagation",
                contributing_factors={
                    "propagation_source_edge_id": str(source_edge.id),
                    "hop": hop,
                    "decay": decay,
                    "source_score": float(source_edge.hazard_score or 0.0),
                },
                is_current=True,
            )

            if sync_edge_field:
                edge.hazard_score = propagated_score
                edge.save(update_fields=["hazard_score", "updated_at"])

        return True
