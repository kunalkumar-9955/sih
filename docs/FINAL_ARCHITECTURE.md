# SIH26002 — Final System Architecture

**Project:** SIH26002 — AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Document Type:** Implemented System Architecture & Subsystem Specification  
**Architecture Paradigm:** Service-Oriented Monolith with Spatial PostGIS Engine & Decoupled Offline Mobile Client  
**Execution Environment:** Windows Host (Native Python 3.14 + Node.js 20 + PostgreSQL 16 / PostGIS 3.4)  

---

## 1. High-Level Architectural Topology

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 PRESENTATION LAYER                     │
                  │                                                        │
                  │   Next.js 14 Web Command Center     Flutter Mobile     │
                  │   (Port 3000 / React / TS)          Driver Client      │
                  └──────────────────┬───────────────────────┬─────────────┘
                                     │                       │
                                     │ REST / JSON (JWT)     │ Batch Sync / Offline Bundle
                                     ▼                       ▼
                  ┌────────────────────────────────────────────────────────┐
                  │               API & ORCHESTRATION LAYER                │
                  │                                                        │
                  │                 Django 6.0+ / DRF                      │
                  │   - Role-Based Access Control (RBAC)                   │
                  │   - Request Correlation Middleware (X-Correlation-ID)  │
                  │   - OpenAPI 3.0 Auto-Documentation (drf-spectacular)   │
                  │   - Demo Readiness & Safe Reset Engine                 │
                  └──────────┬───────────────────────┬─────────────────────┘
                             │                       │
            ┌────────────────┴────────┐    ┌─────────┴─────────────────────┐
            │   AI & ANALYTICS LAYER  │    │      LOGISTICS CORE           │
            │                         │    │                               │
            │ • Hazard Predictor (ML) │    │ • Multi-Modal Router          │
            │ • OOD Generalization    │    │ • Fleet Dispatch Optimizer    │
            │ • Mountain Delay Model  │    │ • Dynamic Load Consolidator   │
            │ • Disruption Sandbox    │    │ • Freight Marketplace Matcher │
            │ • Explainability Engine │    │ • Offline Sync & Conflict Res │
            └────────────────┬────────┘    └─────────┬─────────────────────┘
                             │                       │
                             ▼                       ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                  PERSISTENCE LAYER                     │
                  │                                                        │
                  │          PostgreSQL 16 + PostGIS 3.4 Spatial           │
                  │  - Transport Nodes (Point) & Edges (LineString)        │
                  │  - Multi-Modal Network Topology (Road / Rail / Water)  │
                  │  - Auditable Decision Logs & Sync Event Streams        │
                  └────────────────────────────────────────────────────────┘
```

---

## 2. Implemented Subsystems & Module Breakdown

### 2.1 Spatial Transport Network (`apps.transport_graph`)
- **Entities:** `TransportNode`, `TransportEdge`, `MultimodalTerminal`.
- **Geometries:** PostGIS `Point` (WGS84 EPSG:4326) for terminals and junctions; `LineString` for road segments, rail corridors, and river waterways.
- **Modes Supported:**
  - `ROAD`: National Highways (NH-27, NH-06), State Highways, and rural hill corridors.
  - `RAIL`: Broad-gauge freight rail network connecting Guwahati and Lumding.
  - `WATERWAY`: National Waterway 2 (Brahmaputra River) connecting Pandu Port and Dhubri.
  - `TRANSFER`: Virtual zero-distance intermodal transfer links accounting for transfer time buffers and handling tariffs.
- **Topology Queries:** Native PostGIS spatial queries (`ST_Distance`, `ST_DWithin`, coordinate normalization within NER bounds $[88^\circ\text{E} - 98^\circ\text{E}, 21^\circ\text{N} - 30^\circ\text{N}]$).

### 2.2 Geohazard Inference Engine (`apps.hazards`)
- **Components:** `HazardPredictionService`, `HazardFeatureExtractor`, `ModelRegistry`, `UnseenGeneralizationEngine`.
- **Inference Pipeline:**
  $$\text{Features} = [\text{Rainfall 24h}, \text{Rainfall 1h}, \text{Slope Gradient}, \text{Elevation}, \text{Soil Pore Saturation}, \text{Fault Line Distance}, \text{Historical Washouts}]$$
  $$\text{Hazard Index} \in [0.0, 1.0] \quad \longrightarrow \quad \text{Severity} \in \{\text{LOW}, \text{MEDIUM}, \text{HIGH}, \text{CRITICAL}\}$$
- **Domain Providers:** Decoupled `WeatherProvider` and `TerrainProvider` with local seasonal fallbacks for guaranteed offline/demo reliability.
- **Out-of-Distribution (OOD) Testing:** Synthetic evaluation across 5 distinct stress envelopes (Scenarios A through E).

### 2.3 Hardened Multi-Modal Routing Engine (`apps.routing`)
- **Core Engine:** `RoutingEngine` implementing modified Dijkstra algorithm with dynamic edge weighting.
- **Cost Function:**
  $$C(e) = T_{\text{base}}(e) \times \left(1 + \alpha \times H(e)\right) + P_{\text{mode\_transfer}}(e)$$
  where $\alpha \in [1.0, 2.5]$ is the hazard sensitivity parameter and $P$ is the intermodal penalty (default 30 min, ₹4,200 handling fee).
- **Routing Policies:**
  - `FASTEST`: Minimizes transit time over primary arterial corridors.
  - `SAFEST`: Maximizes travel along low-hazard monitored segments; bypasses vulnerable mountain roads via rail/waterway.
  - `CHEAPEST`: Leverages inland river transit tariffs along NW-2.
  - `MULTIMODAL`: Balances transit speed, tonnage capacity, and transfer buffers.
- **Explainability:** Automatic contextual natural-language justification dynamically assembled from traversal segments.

### 2.4 Predictive ETA Intelligence (`apps.routing.services.eta_intelligence`)
- **Model:** `MountainCorridorDelayModel`.
- **Delay Decomposition:**
  $$\text{ETA} = T_{\text{base}} + \Delta T_{\text{monsoon\_crawl}} + \Delta T_{\text{geohazard\_caution}} + \Delta T_{\text{intermodal\_transfer}} + \Delta T_{\text{chokepoint}}$$
- **Confidence Scoring:** Decays linearly if weather telemetry exceeds validity window ($> 6\text{ hours}$).

### 2.5 Multi-Depot Fleet Optimization (`apps.fleet`)
- **Optimizer:** `MultiDepotFleetOptimizer` implementing Clarke-Wright Savings heuristic with vehicle capacity, cargo hazardous/perishable constraints, and depot positioning.
- **Dynamic Consolidation:** `DynamicLoadConsolidationService` clusters Less-Than-Truckload (LTL) shipments within a 45 km radius, raising vehicle utilization from $\approx 40\%$ to $> 85\%$.
- **Infeasibility Diagnostics:** Gracefully reports `INFEASIBLE` with root cause (e.g. `NO_AVAILABLE_VEHICLES` or `CAPACITY_EXCEEDED`) rather than generating phantom assignments.

### 2.6 Offline Synchronization & Mobile Architecture (`apps.sync`, `frontend/mobile`)
- **Offline Graph Bundles:** Cryptographically verified (SHA-256) SQLite/JSON graph payloads downloaded prior to mountain journeys.
- **Mobile Engine:** On-device Dijkstra router (`offline_routing_service.dart`) executing locally during cellular dropouts.
- **Idempotency & Timestamp Ordering:** Sync events tagged with client UUIDs (`idempotency_key`) and millisecond timestamps; duplicates return `ALREADY_APPLIED` without duplicate record generation.

### 2.7 Disruption Sandbox Simulator (`apps.incidents`)
- **Sandbox Engine:** `DisruptionSimulationEngine` simulates catastrophic rainfall, landslides, and bridge washouts without mutating live operational tables.
- **Resilience Deltas:** Computes pre-disruption vs post-disruption Accessibility Indices across the 8 NER states.

### 2.8 Command Center Operations Dashboard (`apps.analytics`, `frontend/web`)
- **Operational Feed:** `NetworkOperationalSummaryView` aggregating real-time severity states (`NORMAL`, `WATCH`, `WARNING`, `CRITICAL`), active trips, blocked edges, and fleet telemetry.
- **Explainable AI Layer:** `DecisionRecommendation` logging ranked interventions (e.g. "Divert Guwahati-Shillong convoy to Rail Freight Depot") with confidence intervals.
- **Demo Readiness:** Visual badge probing 15 subsystems, safe demo reset modal, and 24-step live audit timeline.

---

## 3. Data Integrity & Security Architecture

1. **Authentication:** JWT (JSON Web Tokens) with short-lived access tokens (60 min) and rotating refresh tokens (7 days).
2. **Role-Based Access Control:** 4 distinct operational roles:
   - `ADMIN`: Full administrative control, graph maintenance, demo reset.
   - `DISPATCHER`: Fleet management, simulation execution, command center analytics.
   - `DRIVER`: Route querying, trip status updates, offline event synchronization, SOS dispatch.
   - `SHIPPER`: Freight demand creation, marketplace bids, tracking telemetry.
3. **Audit Middleware:** Every mutating request logged with actor ID, IP address, timestamp, and unique `X-Correlation-ID` header.
