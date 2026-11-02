"""
SIH26002 — Offline Graph Exporter Service.

Generates self-contained, canonical offline graph bundles for edge devices (Flutter mobile app).
Computes SHA-256 checksums to ensure graph cache integrity in disconnected environments.
"""
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.hazards.models import HazardScore
from apps.sync.models import OfflineGraphBundle
from apps.transport_graph.models import TransportEdge, TransportNode

logger = logging.getLogger(__name__)


class OfflineGraphExporterService:
    """
    Serializes multimodal transport graph and hazard snapshots into an offline bundle.
    """

    def __init__(self, region: str = "NER_CORRIDOR"):
        self.region = region

    def build_graph_bundle_dict(self) -> Dict[str, Any]:
        """
        Extracts all active nodes, edges, and recent hazard snapshots into a JSON-serializable dictionary.
        """
        # Fetch active nodes
        nodes_qs = TransportNode.objects.filter(is_active=True).order_by("id")
        nodes_list = []
        node_id_set = set()

        for node in nodes_qs:
            node_id_set.add(node.id)
            geom_coords = [node.longitude, node.latitude]
            nodes_list.append({
                "id": str(node.id),
                "name": node.name,
                "short_code": node.short_code or "",
                "node_type": node.node_type,
                "coordinates": geom_coords,
                "elevation_m": node.elevation_m or 0.0,
                "state": node.state or "",
                "district": node.district or "",
                "is_intermodal_hub": node.is_intermodal_hub,
            })

        # Fetch latest hazard scores mapped by edge_id
        latest_hazard_scores = {}
        for hs in HazardScore.objects.order_by("edge_id", "-created_at").distinct("edge_id"):
            latest_hazard_scores[hs.edge_id] = {
                "hazard_index": round(float(hs.hazard_index), 4),
                "severity": hs.severity,
                "confidence": round(float(hs.confidence), 4),
            }

        # Fetch edges between active nodes
        edges_qs = (
            TransportEdge.objects.filter(
                source_node_id__in=node_id_set,
                target_node_id__in=node_id_set,
            )
            .select_related("source_node", "target_node")
            .order_by("id")
        )

        edges_list = []
        for edge in edges_qs:
            coords = []
            if edge.geometry:
                coords = list(edge.geometry.coords)

            h_info = latest_hazard_scores.get(edge.id, {})
            current_hazard_score = h_info.get("hazard_index", round(float(edge.hazard_score or 0.0), 4))
            severity = h_info.get("severity", "LOW")

            edges_list.append({
                "id": str(edge.id),
                "source_node_id": str(edge.source_node_id),
                "target_node_id": str(edge.target_node_id),
                "mode": edge.mode,
                "road_name": edge.road_name or "",
                "distance_m": round(float(edge.distance_m), 2),
                "base_transit_time_min": round(float(edge.base_transit_time_min), 2),
                "cost_inr": round(float(edge.cost_inr or 0.0), 2),
                "capacity_kg": float(edge.capacity_kg) if edge.capacity_kg else None,
                "status": edge.status,
                "is_available": edge.is_available,
                "hazard_score": current_hazard_score,
                "hazard_severity": severity,
                "transfer_time_min": round(float(edge.transfer_time_min or 0.0), 2),
                "transfer_cost_inr": round(float(edge.transfer_cost_inr or 0.0), 2),
                "water_level_m": edge.water_level_m,
                "min_required_depth_m": edge.min_required_depth_m,
                "geometry": coords,
            })

        bundle_payload = {
            "region": self.region,
            "exported_at": timezone.now().isoformat(),
            "nodes_count": len(nodes_list),
            "edges_count": len(edges_list),
            "nodes": nodes_list,
            "edges": edges_list,
        }

        return bundle_payload

    @staticmethod
    def compute_checksum(bundle_dict: Dict[str, Any]) -> str:
        """
        Computes SHA-256 over deterministic JSON string representation.
        """
        canonical_json = json.dumps(bundle_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @transaction.atomic
    def export_and_save(self, version_tag: Optional[str] = None) -> OfflineGraphBundle:
        """
        Exports the current graph, generates checksum, deactivates older active bundles
        for this region, and persists the new bundle.
        """
        data = self.build_graph_bundle_dict()
        checksum = self.compute_checksum(data)

        if not version_tag:
            version_tag = f"{self.region}-v{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # Deactivate previous active bundles for this region
        OfflineGraphBundle.objects.filter(corridor_name=self.region, is_active=True).update(is_active=False)

        bundle = OfflineGraphBundle.objects.create(
            version=version_tag,
            corridor_name=self.region,
            checksum_sha256=checksum,
            node_count=data["nodes_count"],
            edge_count=data["edges_count"],
            payload=data,
            is_active=True,
        )

        logger.info(
            "Created OfflineGraphBundle %s (region=%s, nodes=%d, edges=%d, sha256=%s)",
            bundle.version_tag,
            bundle.region,
            bundle.node_count,
            bundle.edge_count,
            bundle.checksum_sha256[:12],
        )
        return bundle
