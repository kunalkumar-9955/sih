# SIH26002 — Comprehensive REST API Reference

**Base URL:** `http://localhost:8000/api/v1/`  
**Authentication Scheme:** `Bearer <jwt-access-token>` via `Authorization` header  
**Content-Type:** `application/json`  
**OpenAPI Swagger Documentation:** `http://localhost:8000/api/docs/`  

---

## 1. Authentication & User Management

### 1.1 Obtain JWT Token Pair
- **Endpoint:** `POST /api/v1/auth/token/`
- **Auth:** Anonymous
- **Request:**
  ```json
  {
    "email": "dispatcher@sih26002.in",
    "password": "SecurePassword123!"
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "c3b8893d-3b55-46b7-84bc-5b94f1c10714",
      "email": "dispatcher@sih26002.in",
      "role": "DISPATCHER"
    }
  }
  ```

### 1.2 Refresh JWT Access Token
- **Endpoint:** `POST /api/v1/auth/token/refresh/`
- **Auth:** Anonymous
- **Request:** `{"refresh": "<refresh-token>"}`
- **Response (HTTP 200 OK):** `{"access": "<new-access-token>"}`

---

## 2. Multi-Modal Routing Engine (`/api/v1/routes/`)

### 2.1 Compute Multi-Modal Route
- **Endpoint:** `POST /api/v1/routes/calculate/`
- **Auth:** Authenticated (`DRIVER`, `DISPATCHER`, `SHIPPER`, `ADMIN`)
- **Request:**
  ```json
  {
    "origin_node_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "destination_node_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
    "policy": "SAFEST",
    "vehicle_context": {
      "vehicle_type": "TRUCK_MEDIUM",
      "gross_weight_kg": 12000,
      "max_draft_m": 0.0
    },
    "hazard_avoidance": true
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "success": true,
    "route": {
      "id": "e4d9b2a1-...",
      "origin": "Guwahati Logistics Hub",
      "destination": "Shillong Distribution Center",
      "policy": "SAFEST",
      "total_distance_km": 102.4,
      "total_time_min": 185.0,
      "total_cost_inr": 4850.0,
      "hazard_penalty_score": 0.18,
      "modes_used": ["ROAD"],
      "transfer_count": 0,
      "explanation": "Recommended SAFEST path: Bypasses hazardous hill road corridors via monitored lower-elevation bypass."
    }
  }
  ```

### 2.2 Calculate Predictive Route ETA
- **Endpoint:** `POST /api/v1/routes/{id}/predictive-eta/`
- **Auth:** Authenticated
- **Response (HTTP 200 OK):**
  ```json
  {
    "route_id": "e4d9b2a1-...",
    "base_transit_time_min": 185.0,
    "total_delay_min": 45.0,
    "predictive_eta_min": 230.0,
    "delay_breakdown": {
      "weather_delay_min": 25.0,
      "hazard_delay_min": 20.0,
      "intermodal_delay_min": 0.0
    },
    "model_version": "ner-mountain-eta-v2.1",
    "confidence": 0.88
  }
  ```

---

## 3. Geohazard Intelligence (`/api/v1/hazards/`)

### 3.1 Get Edge Hazard Score
- **Endpoint:** `GET /api/v1/hazards/edge/{edge_id}/`
- **Auth:** Authenticated
- **Response (HTTP 200 OK):**
  ```json
  {
    "edge_id": "a1b2c3d4-...",
    "hazard_index": 0.38,
    "severity": "MEDIUM",
    "confidence": 0.85,
    "contributing_factors": {
      "monsoon_rainfall": "Moderate 24h precipitation (42.5 mm)",
      "terrain_steepness": "Moderate gradient (18.2° slope)"
    },
    "is_stale": false
  }
  ```

### 3.2 List Active Regional Hazard Incidents
- **Endpoint:** `GET /api/v1/hazards/incidents/`
- **Query Params:** `severity=HIGH`, `status=ACTIVE`
- **Response (HTTP 200 OK):** Standard paginated list of active washout, landslide, and road disruption records.

---

## 4. Multi-Depot Fleet Optimization (`/api/v1/optimization/`)

### 4.1 Trigger Fleet Dispatch Optimization
- **Endpoint:** `POST /api/v1/optimization/run/`
- **Auth:** `DISPATCHER`, `ADMIN`
- **Request:**
  ```json
  {
    "depot_ids": [],
    "load_ids": [],
    "enable_consolidation": true,
    "is_simulation": false
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "run_id": "7f8a9b0c-...",
    "status": "COMPLETED",
    "total_loads_evaluated": 5,
    "assigned_loads_count": 5,
    "vehicles_dispatched": 2,
    "estimated_cost_inr": 18450.0,
    "fuel_savings_estimate_pct": 14.2,
    "assignments": [
      {
        "vehicle_id": "v-101",
        "vehicle_plate": "AS-01-GC-4412",
        "loads": ["L-01", "L-03"],
        "total_payload_kg": 9800.0,
        "capacity_utilization_pct": 81.7
      }
    ]
  }
  ```

---

## 5. Dynamic Load Consolidation (`/api/v1/fleet/consolidation/`)

### 5.1 Generate LTL Consolidation Bundles
- **Endpoint:** `POST /api/v1/fleet/consolidation/recommendations/`
- **Auth:** `DISPATCHER`, `ADMIN`
- **Request:** `{"max_cluster_radius_km": 45.0, "persist": false}`
- **Response (HTTP 200 OK):**
  ```json
  {
    "success": true,
    "bundles_count": 1,
    "bundles": [
      {
        "bundle_id": "b-201",
        "load_count": 2,
        "total_weight_kg": 6400.0,
        "origin_hub": "Guwahati ICD",
        "destination_hub": "Silchar Logistics Park",
        "compatibility": "COMPATIBLE_GENERAL_CARGO"
      }
    ]
  }
  ```

---

## 6. Offline-First Mobile Synchronization (`/api/v1/sync/`)

### 6.1 Download Cryptographic Offline Graph Bundle
- **Endpoint:** `GET /api/v1/sync/graph-bundle/active/`
- **Auth:** `DRIVER`, `DISPATCHER`, `ADMIN`
- **Response (HTTP 200 OK):**
  ```json
  {
    "version_tag": "ner-graph-v1.0.4",
    "region": "NER_PRIMARY",
    "node_count": 26,
    "edge_count": 54,
    "checksum_sha256": "4a7d1ed849b38f87023e3e06180554c9ef8979313b28b6d369f0b2f6efcb5bc6",
    "payload": { ... }
  }
  ```

### 6.2 Submit Mobile Driver Event Batch
- **Endpoint:** `POST /api/v1/sync/events/batch/`
- **Auth:** `DRIVER`
- **Request:**
  ```json
  {
    "events": [
      {
        "idempotency_key": "94b9148d-6a56-42d8-9121-ea1c6db9dc18",
        "event_type": "TRIP_STATUS",
        "client_timestamp": "2026-09-11T14:30:00Z",
        "payload": {
          "trip_id": "trip-301",
          "status": "COMPLETED",
          "current_node_id": "node-12"
        }
      }
    ]
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "batch_size": 1,
    "applied_count": 1,
    "duplicate_count": 0,
    "conflict_count": 0,
    "rejected_count": 0
  }
  ```

---

## 7. Disruption Sandbox Simulator (`/api/v1/simulations/`)

### 7.1 Run Disruption Scenario
- **Endpoint:** `POST /api/v1/simulations/`
- **Auth:** `DISPATCHER`, `ADMIN`
- **Request:**
  ```json
  {
    "scenario_type": "HEAVY_RAINFALL",
    "target_corridor": "NH-27 / Guwahati Corridor",
    "target_state": "AS",
    "parameters": { "rainfall_mm": 135.0 }
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "scenario_name": "HEAVY_RAINFALL_NH-27",
    "affected_edges_count": 2,
    "impacted_shipments_count": 4,
    "pre_disruption_accessibility_score": 0.88,
    "post_disruption_accessibility_score": 0.58,
    "accessibility_delta_pct": -34.1,
    "is_simulation": true
  }
  ```

---

## 8. Command Center Operational Intelligence (`/api/v1/intelligence/`)

### 8.1 Network Operational Summary
- **Endpoint:** `GET /api/v1/intelligence/network/`
- **Auth:** `DISPATCHER`, `ADMIN`
- **Response (HTTP 200 OK):**
  ```json
  {
    "severity_state": "NORMAL",
    "metrics": {
      "active_trips": 4,
      "delayed_shipments": 0,
      "active_hazards_count": 0,
      "critical_corridors_count": 0,
      "fleet_utilization_pct": 66.7,
      "overall_accessibility_score": 0.88
    },
    "data_source": "CONFIGURED_TELEMETRY"
  }
  ```

### 8.2 Explainable AI Operator Recommendations
- **Endpoint:** `GET /api/v1/intelligence/recommendations/`
- **Auth:** `DISPATCHER`, `ADMIN`
- **Response (HTTP 200 OK):** List of ranked tactical interventions with confidence ratings and factor breakdowns.

---

## 9. Demo Readiness & Orchestration (`/api/v1/demo/`)

### 9.1 System Readiness Health Check
- **Endpoint:** `GET /api/v1/demo/readiness/`
- **Auth:** AllowAny / Authenticated
- **Response (HTTP 200 OK):**
  ```json
  {
    "status": "READY",
    "environment": "HOST_WINDOWS_DEV",
    "timestamp": "2026-09-11T19:30:26Z",
    "checks": {
      "database": "PASS",
      "postgis": "PASS",
      "migrations": "PASS",
      "transport_graph": "PASS",
      "hazards": "PASS",
      "routing": "PASS",
      "fleet": "PASS",
      "freight": "PASS",
      "marketplace": "PASS",
      "tracking": "PASS",
      "accessibility": "PASS",
      "optimization": "PASS",
      "simulation": "PASS",
      "ai_models": "PASS",
      "offline_bundle": "PASS"
    }
  }
  ```

### 9.2 Safe Demo Reset
- **Endpoint:** `POST /api/v1/demo/reset/`
- **Auth:** AllowAny / Authenticated
- **Request:**
  ```json
  {
    "confirm_demo_reset": true,
    "mode": "DEMO"
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "success": true,
    "message": "Demo state reset successfully. Production tables untouched.",
    "mode": "DEMO",
    "cleaned": {
      "simulation_hazards": 3,
      "disruption_runs": 1,
      "demo_scenarios": 2,
      "recommendations": 4
    },
    "demo_baseline_active": true
  }
  ```

### 9.3 Out-of-Distribution Generalization Benchmark
- **Endpoint:** `GET /api/v1/demo/generalization-report/`
- **Response (HTTP 200 OK):** Evaluation results across Scenarios A through E with mandatory synthetic evaluation disclosures.
