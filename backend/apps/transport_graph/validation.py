"""
SIH26002 — GIS & Transport Graph Quality Validation Utilities.

Enforces topological integrity, spatial consistency, mode compatibility,
and attribute bounds across the multimodal network.

Follows the strict rule:
Do not automatically 'fix' bad GIS data without logging it.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode

logger = logging.getLogger("sih.transport_graph.validation")

# Bounding box covering North Eastern Region (NER) + buffer
# Longitude: ~88.0°E to ~98.0°E, Latitude: ~21.0°N to ~30.0°N
NER_BBOX = {
    "min_lon": 87.0,
    "max_lon": 98.5,
    "min_lat": 20.0,
    "max_lat": 30.5,
}

# Node types authorized to anchor specific modal edges
MODE_COMPATIBLE_NODE_TYPES = {
    TransportMode.ROAD: {
        NodeType.ROAD_INTERSECTION,
        NodeType.CHECKPOST,
        NodeType.LOCAL_HUB,
        NodeType.LOGISTICS_HUB,
        NodeType.MULTIMODAL_HUB,
        NodeType.WAREHOUSE,
        NodeType.PORT,
    },
    TransportMode.RAIL: {
        NodeType.RAIL_YARD,
        NodeType.RAIL_SIDING,
        NodeType.MULTIMODAL_HUB,
        NodeType.LOGISTICS_HUB,
        NodeType.PORT,
    },
    TransportMode.WATER: {
        NodeType.WATERWAY_TERMINAL,
        NodeType.RIVER_JETTY,
        NodeType.MULTIMODAL_HUB,
        NodeType.LOGISTICS_HUB,
        NodeType.PORT,
    },
    TransportMode.WATERWAY: {
        NodeType.WATERWAY_TERMINAL,
        NodeType.RIVER_JETTY,
        NodeType.MULTIMODAL_HUB,
        NodeType.LOGISTICS_HUB,
        NodeType.PORT,
    },
    TransportMode.TRANSFER: {
        NodeType.MULTIMODAL_HUB,
        NodeType.LOGISTICS_HUB,
        NodeType.LOCAL_HUB,
        NodeType.RAIL_YARD,
        NodeType.WATERWAY_TERMINAL,
        NodeType.RIVER_JETTY,
        NodeType.PORT,
        NodeType.WAREHOUSE,
        NodeType.ROAD_INTERSECTION,
    },
}


@dataclass
class GraphValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
        }


class TransportGraphValidator:
    """
    Validates multimodal graph topology, spatial geometries,
    and operational attributes.
    """

    def validate_node(self, node: TransportNode) -> List[str]:
        """Validates single node attributes and geometry."""
        issues = []
        if not node.name or not node.name.strip():
            issues.append(f"Node [{node.id}]: Name cannot be empty.")

        if node.node_type not in NodeType.values:
            issues.append(f"Node [{node.id} '{node.name}']: Invalid node_type '{node.node_type}'.")

        if not node.geometry:
            issues.append(f"Node [{node.id} '{node.name}']: Missing spatial Point geometry.")
        else:
            lon = node.geometry.x
            lat = node.geometry.y

            if not (-180.0 <= lon <= 180.0):
                issues.append(f"Node [{node.id} '{node.name}']: Invalid longitude {lon}.")
            if not (-90.0 <= lat <= 90.0):
                issues.append(f"Node [{node.id} '{node.name}']: Invalid latitude {lat}.")

            # Check if within plausible North Eastern Region bounds
            if not (NER_BBOX["min_lon"] <= lon <= NER_BBOX["max_lon"] and
                    NER_BBOX["min_lat"] <= lat <= NER_BBOX["max_lat"]):
                issues.append(
                    f"Node [{node.id} '{node.name}']: Coordinates ({lon:.4f}, {lat:.4f}) "
                    f"fall outside standard NER bounding box."
                )

        if node.elevation_m is not None and node.elevation_m < -100.0:
            issues.append(f"Node [{node.id} '{node.name}']: Elevation {node.elevation_m}m is physically implausible.")

        return issues

    def validate_edge(self, edge: TransportEdge) -> List[str]:
        """Validates single edge attributes, connections, and LineString geometry."""
        issues = []

        if not edge.source_node_id or not edge.target_node_id:
            issues.append(f"Edge [{edge.id}]: Missing source or target node reference.")
            return issues

        if edge.source_node_id == edge.target_node_id:
            issues.append(f"Edge [{edge.id}]: Self-loop detected on node {edge.source_node_id}.")

        norm_mode = TransportMode.normalize(edge.mode)
        if norm_mode not in (TransportMode.ROAD, TransportMode.RAIL, TransportMode.WATER, TransportMode.TRANSFER):
            issues.append(f"Edge [{edge.id}]: Invalid mode '{edge.mode}'.")

        if edge.distance_m <= 0.0:
            issues.append(f"Edge [{edge.id}]: Non-positive distance {edge.distance_m}m.")

        if edge.base_transit_time_min <= 0.0:
            issues.append(f"Edge [{edge.id}]: Non-positive base transit time {edge.base_transit_time_min}min.")

        if edge.cost_inr is not None and edge.cost_inr < 0:
            issues.append(f"Edge [{edge.id}]: Negative freight cost {edge.cost_inr} INR.")

        if not (0.0 <= edge.hazard_score <= 1.0):
            issues.append(f"Edge [{edge.id}]: Hazard score {edge.hazard_score} out of bounds [0.0, 1.0].")

        # Geometry checks
        if edge.geometry is None:
            issues.append(f"Edge [{edge.id}]: Missing spatial LineString geometry.")
        else:
            coords = list(edge.geometry.coords)
            if len(coords) < 2:
                issues.append(f"Edge [{edge.id}]: LineString must have at least 2 coordinate points.")
            else:
                # Check start/end endpoints match source/target coordinates (tolerance ~ 0.02 deg ~ 2 km)
                src_pt = edge.source_node.geometry
                tgt_pt = edge.target_node.geometry
                if src_pt and tgt_pt:
                    start_dist = abs(coords[0][0] - src_pt.x) + abs(coords[0][1] - src_pt.y)
                    end_dist = abs(coords[-1][0] - tgt_pt.x) + abs(coords[-1][1] - tgt_pt.y)
                    if start_dist > 0.05 or end_dist > 0.05:
                        logger.warning(
                            f"Edge [{edge.id}]: Geometry endpoints deviate from node positions "
                            f"(start_diff={start_dist:.4f}, end_diff={end_dist:.4f})."
                        )

        # Mode compatibility with connecting nodes
        allowed_src_types = MODE_COMPATIBLE_NODE_TYPES.get(edge.mode, set())
        if allowed_src_types:
            if edge.source_node.node_type not in allowed_src_types:
                issues.append(
                    f"Edge [{edge.id} {edge.mode}]: Source node '{edge.source_node.name}' "
                    f"({edge.source_node.node_type}) cannot originate {edge.mode} traffic."
                )
            if edge.target_node.node_type not in allowed_src_types:
                issues.append(
                    f"Edge [{edge.id} {edge.mode}]: Target node '{edge.target_node.name}' "
                    f"({edge.target_node.node_type}) cannot terminate {edge.mode} traffic."
                )

        # Transfer edge specifics
        if edge.is_transfer:
            if edge.transfer_time_min is None or edge.transfer_time_min < 0:
                issues.append(f"Transfer Edge [{edge.id}]: Missing or negative transfer_time_min.")

        # Waterway specifics
        if edge.is_waterway:
            if edge.min_required_depth_m is not None and edge.water_level_m is not None:
                if edge.water_level_m < 0.0:
                    issues.append(f"Water Edge [{edge.id}]: Negative water level {edge.water_level_m}m.")

        return issues

    def validate(
        self,
        nodes: Optional[List[TransportNode]] = None,
        edges: Optional[List[TransportEdge]] = None,
    ) -> GraphValidationResult:
        """Convenience alias for validate_full_graph."""
        return self.validate_full_graph(nodes=nodes, edges=edges)

    def validate_full_graph(
        self,
        nodes: Optional[List[TransportNode]] = None,
        edges: Optional[List[TransportEdge]] = None,
    ) -> GraphValidationResult:
        """
        Performs comprehensive topological and attribute validation on the active graph.
        """
        all_nodes = list(nodes) if nodes is not None else list(TransportNode.objects.all())
        all_edges = list(edges) if edges is not None else list(
            TransportEdge.objects.select_related("source_node", "target_node").all()
        )

        errors: List[str] = []
        warnings: List[str] = []

        node_map = {n.id: n for n in all_nodes}
        connected_node_ids: Set[Any] = set()

        # 1. Validate all nodes
        for node in all_nodes:
            node_issues = self.validate_node(node)
            errors.extend(node_issues)

        # 2. Validate all edges
        for edge in all_edges:
            edge_issues = self.validate_edge(edge)
            errors.extend(edge_issues)

            connected_node_ids.add(edge.source_node_id)
            connected_node_ids.add(edge.target_node_id)

        # 3. Check for isolated nodes
        for node in all_nodes:
            if node.id not in connected_node_ids and node.is_active:
                warnings.append(
                    f"Isolated Node: '{node.name}' [{node.short_code or str(node.id)}] "
                    f"has no connected incoming or outgoing edges."
                )

        # 4. Check for multimodal transfer integrity
        modes_present = set(e.normalized_mode for e in all_edges)
        has_transfer = TransportMode.TRANSFER in set(e.mode for e in all_edges)
        if len(modes_present - {TransportMode.TRANSFER}) > 1 and not has_transfer:
            warnings.append(
                "Multimodal Graph contains multiple modes but no TRANSFER edges to bridge them."
            )

        stats = {
            "total_nodes": len(all_nodes),
            "active_nodes": sum(1 for n in all_nodes if n.is_active),
            "total_edges": len(all_edges),
            "open_edges": sum(1 for e in all_edges if e.status == EdgeStatus.OPEN),
            "restricted_edges": sum(1 for e in all_edges if e.status == EdgeStatus.RESTRICTED),
            "blocked_edges": sum(1 for e in all_edges if e.status == EdgeStatus.BLOCKED),
            "critical_edges": sum(1 for e in all_edges if e.status == EdgeStatus.CRITICAL),
            "modes_present": list(modes_present),
            "isolated_nodes_count": len(all_nodes) - len(connected_node_ids),
        }

        is_valid = len(errors) == 0

        if not is_valid:
            logger.error(f"Graph validation failed with {len(errors)} errors: {errors[:5]}")
        else:
            logger.info("Graph validation passed with 0 errors.")

        return GraphValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )
