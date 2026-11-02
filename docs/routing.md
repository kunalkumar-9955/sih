# SIH26002 — GIS & Multimodal Routing Engine Documentation

## Overview
The **AI-Based Smart Multi-Modal Logistics & Risk Intelligence Platform for the North Eastern Region (NER)** implements a hardened, GIS-aware multimodal routing engine designed to overcome the critical freight transportation bottlenecks of North East India.

---

## Routing Policies Formulation

All routing strategies are centralized in `apps.routing.policies` and evaluated over the multimodal transport graph:

### 1. FASTEST Policy
Prioritizes throughput and minimal transit time along high-speed corridors:
$$\text{Cost} = T_{\text{transit}} \times M_{\text{status}} + 1.5 \times T_{\text{transfer}} + 5.0 \times H$$
Where:
- $T_{\text{transit}}$ is base transit time in minutes.
- $M_{\text{status}}$ is edge operational status multiplier (`OPEN`: 1.0, `RESTRICTED`: 1.35, `CRITICAL`: 3.5).
- $T_{\text{transfer}}$ is intermodal transfer time.
- $H$ is geohazard score $[0.0, 1.0]$.

### 2. SAFEST Policy
Avoids active landslide, flood, and steep gradient risk zones using power-law hazard penalties:
$$\text{Cost} = T_{\text{transit}} \times M_{\text{status}} \times (1.0 + 4.5 \times H^{2.2}) + 30.0 \times T_{\text{transfer\_penalty}}$$

### 3. CHEAPEST Policy
Optimizes financial freight tariffs and encourages fuel-efficient rail and green inland waterways:
$$\text{Cost} = C_{\text{INR}} \times M_{\text{status}} + C_{\text{transfer}} + 0.05 \times T_{\text{transit}}$$

### 4. MULTIMODAL Policy
Balances transit time, freight cost tariffs, geohazard safety, and transfer overheads:
$$\text{Cost} = 0.40 \times (T_{\text{transit}} \times M_{\text{status}}) + 0.35 \times \left(\frac{C_{\text{INR}}}{25}\right) + 0.25 \times (H \times 100) + 1.2 \times T_{\text{transfer}}$$

---

## Constraint Evaluation Engine

The `ConstraintChecker` evaluates every candidate edge before traversal:
1. **Vehicle Cargo Capacity**: Rejects edges where `cargo_weight_kg > edge.capacity_kg`.
2. **Waterway Navigation Depth**: Rejects shallow waterways where vessel draft exceeds `min_required_depth_m` or `water_level_m`.
3. **Seasonal Windows**: Validates operational months against departure schedule.
4. **Mode Avoidance**: Respects user-defined mode exclusions (`avoid_modes`).
5. **Multimodal Switch**: Restricts to pure road transport when `allow_multimodal=False`.

---

## Decoupled Hazard Provider Interface

The routing engine consumes hazard data via the `HazardProvider` abstract base class returning `HazardScoreData`:
- `StaticHazardProvider`: Reads spatial geohazard baseline from the `TransportEdge` records.
- `MockHazardProvider`: Supports test simulation and scenario analysis.
- Future AI Integration: Spatial GCN and XGBoost hazard prediction models drop into the `HazardProvider` interface without modifying the core Dijkstra routing engine.

---

## Seed Corridor: Guwahati – Shillong – Silchar

The corridor integrates 26 nodes and 38 multimodal edges across Assam and Meghalaya:
- **Road (NH-6 & NH-27)**: High-throughput mountain highways connecting Guwahati, Shillong, Jowai, Ladrymbai, Sonapur, and Silchar.
- **Rail (NF Railway)**: Lumding–Badarpur mountain railway avoiding fragile road landslide corridors.
- **Inland Waterways (NW-2 & NW-16)**: Pandu Port on the Brahmaputra River and Silchar Jetty on the Barak River.
- **Intermodal Freight Transfers**: Seamless transitions between Road, Rail, and River terminals with realistic transshipment handling times.

---

## API Endpoints

### 1. Plan Route (`POST /api/v1/routes/plan/`)
Request:
```json
{
  "origin_node_id": "00000000-0000-0000-0000-000000000001",
  "destination_node_id": "00000000-0000-0000-0000-000000000006",
  "routing_policy": "SAFEST",
  "cargo_weight_tons": 12.5,
  "allow_multimodal": true
}
```

Response:
```json
{
  "routes": [
    {
      "route_id": "9a6e138a-...",
      "origin": "Guwahati Inland Port (Pandu)",
      "destination": "Silchar Logistics Park",
      "routing_policy": "SAFEST",
      "route_type_display": "Safest Route",
      "total_distance": 312500.0,
      "total_time": 420.0,
      "total_cost": 4650.0,
      "risk_score": 0.08,
      "modes_used": ["ROAD", "RAIL", "TRANSFER"],
      "transfer_count": 2,
      "explanation": "Recommended SAFEST path: Bypasses hazardous hill road corridors (overall risk index 0.08) by transferring to the heavy rail network at an intermodal freight terminal.",
      "geometry_coordinates": [[91.7362, 26.1445], [91.8830, 25.5788], ...],
      "segments": [...]
    }
  ]
}
```

### 2. Legacy Compute Route (`POST /api/v1/routes/compute/`)
Backward-compatible endpoint returning a list of route options for multi-policy evaluation.
