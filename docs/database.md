# SIH26002 — Spatial Database & PostGIS Schema

## Overview
The platform uses **PostgreSQL 15+** with **PostGIS 3.3+** for high-performance spatial querying, spatial indexing (GIST), topological validation, and geographic distance calculations across the North Eastern Region.

---

## Spatial Models & Schema

### 1. `TransportNode` (`apps.transport_graph.models.TransportNode`)
Represents logistic hubs, road intersections, railway yards, and river ports.

| Field | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique identifier |
| `name` | CharField(150) | Node descriptive name |
| `short_code` | CharField(20) | Unique hub reference code |
| `geometry` | PointField(srid=4326) | Longitude / Latitude coordinates |
| `node_type` | CharField(30) | Hub type (`ROAD_INTERSECTION`, `CHECKPOST`, `LOCAL_HUB`, `LOGISTICS_HUB`, `MULTIMODAL_HUB`, `WAREHOUSE`, `RAIL_YARD`, `RAIL_SIDING`, `PORT`, `WATERWAY_TERMINAL`, `RIVER_JETTY`) |
| `elevation_m` | FloatField | Terrain elevation in meters |
| `state` / `district` | CharField | Administrative boundary location |
| `is_active` | BooleanField | Operational status toggle |

### 2. `TransportEdge` (`apps.transport_graph.models.TransportEdge`)
Represents physical transport corridors and intermodal transfers.

| Field | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Unique identifier |
| `source_node` | ForeignKey | Origin node |
| `target_node` | ForeignKey | Destination node |
| `mode` | CharField(20) | `ROAD`, `RAIL`, `WATER`, `TRANSFER` |
| `status` | CharField(20) | `OPEN`, `RESTRICTED`, `CRITICAL`, `BLOCKED`, `SEASONAL`, `UNDER_REPAIR` |
| `distance_m` | FloatField | Path length in meters |
| `base_transit_time_min` | FloatField | Nominal travel time in minutes |
| `cost_inr` | DecimalField | Freight tariff in INR |
| `hazard_score` | FloatField | Baseline geohazard score $[0.0, 1.0]$ |
| `capacity_kg` / `max_payload_tons` | DecimalField | Structural bridge/road weight limit |
| `water_level_m` | FloatField | Dynamic waterway depth (meters) |
| `min_required_depth_m` | FloatField | Channel minimum clearance (meters) |
| `draft_requirement_m` | FloatField | Minimum vessel draft requirement |
| `transfer_time_min` | FloatField | Transshipment handling time |
| `geometry` | LineStringField(srid=4326) | Polyline route trajectory |

---

## Spatial Query Utilities (`apps.transport_graph.spatial`)

- `find_nearest_node(lat, lon, max_distance_km)`: PostGIS `ST_DistanceSphere` query returning the closest active transport hub.
- `find_nearest_edge(lat, lon, max_distance_km)`: PostGIS `ST_Distance` query to snap a GPS coordinate to the road/rail network.
- `find_nearby_hubs(lat, lon, radius_km)`: Bounding radius retrieval for regional routing hubs.
- `get_corridor_subgraph_edges(min_lat, min_lon, max_lat, max_lon)`: Subgraph extraction within arbitrary geographical bounding boxes.

---

## Spatial Integrity Validation (`apps.transport_graph.validation`)

The `TransportGraphValidator` performs automated checks:
1. **Spatial Bounding**: Ensures all nodes fall within North Eastern Region bounds ($87.0^\circ\text{E}$ to $98.5^\circ\text{E}$, $20.0^\circ\text{N}$ to $30.5^\circ\text{N}$).
2. **Topological Connectivity**: Identifies isolated nodes with no incoming/outgoing edges.
3. **Geometry Endpoints**: Validates that edge LineString coordinates match source and target node positions.
4. **Mode Compatibility**: Asserts that only valid hub types connect to specific transport modes (e.g. railway edges connect to `RAIL_YARD` or `MULTIMODAL_HUB`).
