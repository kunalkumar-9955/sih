# RouteIQ: Smart Multi-Modal Logistics & Risk Intelligence Platform

> **SIH Problem Statement:** SIH26002 by Ministry of Development of North Eastern Region (MDoNER)

[![Django](https://img.shields.io/badge/Django-6.0+-0C4B33?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgis.net/)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-205%20Passed-brightgreen?style=for-the-badge)]()
[![SIH Status](https://img.shields.io/badge/SIH26002-Demo%20Ready%20(Phase%2011)-success?style=for-the-badge)]()

> **Platform Status:** Production-Hardenable, Empirically Benchmarked & SIH Demonstration Ready  

---

## 1. Project Overview

**RouteIQ** is an **AI-powered, climate-resilient, multimodal logistics and risk intelligence platform** engineered specifically for the extreme geography of India's North Eastern Region (Assam, Meghalaya, Tripura, Mizoram, Manipur, Nagaland, Arunachal Pradesh, and Sikkim).

**SIH Problem Statement:** SIH26002 (Ministry of Development of North Eastern Region — MDoNER)

The platform bridges chronic logistics bottlenecks by unifying Road, Broad-Gauge Rail, and Inland Waterways into a single intelligent transport graph. It actively incorporates environmental geohazard prediction, predictive transit delay models, multi-depot fleet dispatch optimization, dynamic Less-Than-Truckload (LTL) consolidation, and cryptographic offline-first driver navigation.

---

## 2. The Core Problem in the North Eastern Region

- **Extreme Himalayan Vulnerability:** Over 70% of freight transit depends on fragile mountain corridors (NH-27, NH-06, NH-10) prone to annual monsoon washouts and slope failures.
- **Economic Severance:** A single roadblock at Khetri or Meghalaya borders halts food, medical, and petroleum supplies to Barak Valley, Tripura, and Mizoram for days.
- **High Logistics Costs:** Severe terrain friction, unpaved hill roads, and empty return hauls (45–60%) lead to elevated freight tariffs across the region.
- **Cellular Dead Zones:** Deep mountain valleys have zero cellular coverage, blinding drivers and dispatchers during emergencies.

---

## 3. Why the North Eastern Region is Different

Standard logistics platforms assume flat, static, continuous highway networks. In the Northeast:
1. **Infrastructure is Dynamic:** Roads literally wash away during the monsoon; alternative detours must be calculated proactively.
2. **Waterways are Natural Highways:** National Waterway 2 (Brahmaputra River) runs parallel to saturated road corridors and can carry heavy container barges.
3. **Connectivity is Intermittent:** Offline functionality cannot be an afterthought—it must be a foundational architectural requirement.

---

## 4. Key Capabilities & Implemented Solutions

1. **Multimodal Routing Engine:** Modified Dijkstra algorithm with dynamic geohazard cost penalties ($\alpha$-weighting), road bridge limits, and intermodal transfer buffers (Road $\leftrightarrow$ Rail $\leftrightarrow$ Water).
2. **Predictive Geohazard Intelligence:** 7-dimensional feature extraction (rainfall, slope gradient, soil moisture, fault proximity) powering explainable risk scoring and severity classification.
3. **Predictive Mountain ETA:** Calibrated non-linear delay model decomposing ETAs into base transit time, monsoon crawl, slope caution, and intermodal buffers.
4. **Multi-Depot Fleet Optimization (MDCVRPTW):** Clarke-Wright savings heuristic solving multi-depot vehicle routing under strict payload limits with transparent infeasibility diagnostics.
5. **Dynamic Load Consolidation:** Spatial clustering grouping LTL shipments within a 45 km radius, raising vehicle utilization from $\approx 42\%$ to $> 85\%$.
6. **Offline-First Driver Navigation:** Cryptographically verified (SHA-256) graph bundles enabling local on-device Dijkstra routing and queued batch synchronization with UUID idempotency keys.
7. **Disruption Sandbox Simulator:** Isolated what-if scenario testing evaluating network resilience deltas across all 8 NER states.
8. **MDoNER Command Center:** Single-pane operational dashboard with live network severity states (`NORMAL`, `WATCH`, `WARNING`, `CRITICAL`), accessibility indices, and tactical AI intervention cards.
9. **Demo Readiness & Safe Reset:** Live 15-subsystem health diagnostics probe (`/api/v1/demo/readiness/`) and safe non-destructive demo reset.

---

## 5. System Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 PRESENTATION LAYER                     │
                  │   Next.js 14 Web Command Center     Flutter Mobile     │
                  │   (Port 3000 / React / TS)          Driver Client      │
                  └──────────────────┬───────────────────────┬─────────────┘
                                     │                       │
                                     │ REST / JSON (JWT)     │ Batch Sync / Offline Bundle
                                     ▼                       ▼
                  ┌────────────────────────────────────────────────────────┐
                  │               API & ORCHESTRATION LAYER                │
                  │                 Django 6.0+ / DRF                      │
                  │   - Role-Based Access Control (RBAC)                   │
                  │   - Request Correlation Middleware (X-Correlation-ID)  │
                  │   - OpenAPI 3.0 Auto-Documentation (drf-spectacular)   │
                  │   - Demo Readiness & Safe Reset Engine                 │
                  └──────────┬───────────────────────┬─────────────────────┘
                             │                       │
            ┌────────────────┴────────┐    ┌─────────┴─────────────────────┐
            │   AI & ANALYTICS LAYER  │    │      LOGISTICS CORE           │
            │ • Hazard Predictor (ML) │    │ • Multimodal Dijkstra Router  │
            │ • OOD Generalization    │    │ • Fleet Dispatch Optimizer    │
            │ • Mountain Delay Model  │    │ • Dynamic Load Consolidator   │
            │ • Disruption Sandbox    │    │ • Freight Marketplace Matcher │
            │ • Explainability Engine │    │ • Offline Sync & Conflict Res │
            └────────────────┬────────┘    └─────────┬─────────────────────┘
                             │                       │
                             ▼                       ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                  PERSISTENCE LAYER                     │
                  │          PostgreSQL 16 + PostGIS 3.4 Spatial           │
                  │  - Transport Nodes (Point) & Edges (LineString)        │
                  │  - Multi-Modal Network Topology (Road / Rail / Water)  │
                  │  - Auditable Decision Logs & Sync Event Streams        │
                  └────────────────────────────────────────────────────────┘
```

---

## 6. Technology Stack

| Layer | Technologies | Description |
| :--- | :--- | :--- |
| **Backend** | Python 3.11–3.14, Django 6.0+, Django REST Framework | Clean service-oriented modular monolith |
| **Spatial Database** | PostgreSQL 16 + PostGIS 3.4 | Native Point & LineString spatial indexing (WGS84 EPSG:4326) |
| **Web Frontend** | Next.js 14, React 18, TypeScript, TailwindCSS / Vanilla CSS | Responsive operational dashboard with Leaflet integration |
| **Mobile Client** | Flutter 3.x, Dart, SharedPreferences, SQLite | Offline-first driver navigation & sync queue |
| **Machine Learning** | Scikit-learn, NumPy, SciPy, Joblib | Gradient Boosting, Logistic Regression, XAI Factor Engine |
| **API & Security** | SimpleJWT, drf-spectacular (OpenAPI 3.0), bcrypt | RBAC (Admin, Dispatcher, Driver, Shipper), Correlation ID |
| **Deployment** | Native Windows / Linux Host (Zero Docker overhead) | Direct system execution on host environment |

---

## 7. Empirical Performance Benchmarks
*(Measured via microsecond-resolution hardware profiling on host Windows 11 environment; see [`docs/FINAL_PERFORMANCE_REPORT.md`](./docs/FINAL_PERFORMANCE_REPORT.md))*:

| Workload | Dataset Size | Mean Latency | Median Latency | P95 Latency |
| :--- | :--- | :---: | :---: | :---: |
| **Demo Readiness Check** | 15 Subsystem Health Probes | 78.39 ms | 33.05 ms | 271.00 ms |
| **Hazard Inference Engine** | 54 Active Network Edges | 3.02 ms | 2.69 ms | 4.46 ms |
| **Multi-Modal Dijkstra Routing** | 26 Nodes, 54 Edges Topology | 13.18 ms | 12.40 ms | 16.61 ms |
| **Predictive ETA Calculation** | 145 km Mountain Vector | 0.02 ms | 0.01 ms | 0.04 ms |
| **Dynamic Load Consolidation** | 5 LTL Freight Demands | 4.06 ms | 4.00 ms | 4.59 ms |
| **Multi-Depot Fleet Optimization** | 3 Vehicles, 5 Loads | 37.56 ms | 37.16 ms | 39.57 ms |
| **Disruption Scenario Simulator** | NH-27 Corridor Outage | 15.49 ms | 15.50 ms | 16.19 ms |
| **Accessibility Index Calculation** | All 54 Network Edges | 5.63 ms | 5.56 ms | 6.01 ms |
| **Command-Center Intelligence API** | Full Telemetry Aggregation | 0.23 ms | 0.12 ms | 0.65 ms |

---

## 8. Quick Start (Windows Local Host)

### Prerequisites
- Python 3.11+ (Tested on Python 3.14.5)
- PostgreSQL 16 with PostGIS 3.4
- Node.js v18+ & npm v9+

### 1. Database Setup
Ensure PostgreSQL is running on `localhost:5432`:
```sql
CREATE USER sih_user WITH PASSWORD 'sih_pass';
CREATE DATABASE sih_db OWNER sih_user;
\c sih_db
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Configure Environment
```powershell
Copy-Item .env.example .env
```

### 3. Initialize & Seed Demo Topology
```powershell
cd backend
python manage.py migrate
python manage.py phase10_demo --seed 42
```
*Or execute the automated helper script:*
```powershell
powershell -ExecutionPolicy Bypass -File ..\scripts\setup_demo.ps1
```

### 4. Start Backend Server
```powershell
# In backend directory:
python manage.py runserver 8000
# Or via helper script:
powershell -ExecutionPolicy Bypass -File ..\scripts\start_backend.ps1
```
- API Base: `http://localhost:8000/api/v1/`
- Interactive Swagger UI: `http://localhost:8000/api/docs/`
- Demo Readiness Probe: `http://localhost:8000/api/v1/demo/readiness/`

### 5. Start Web Frontend
In a new terminal:
```powershell
cd frontend\web
npm install
npm run dev
# Or via helper script:
powershell -ExecutionPolicy Bypass -File ..\..\scripts\start_web.ps1
```
Open browser to: `http://localhost:3000/command-center`

---

## 9. Automated Testing & Verification

Run the full automated test regression suite:
```powershell
cd backend
python -m pytest -q
```
**Output:** `201 passed, 14 warnings in 56.97s (100% pass rate).`

Run system integrity checks:
```powershell
python manage.py check
python manage.py makemigrations --check
```
**Output:** `System check identified no issues (0 silenced).`

Compile Next.js production build:
```powershell
cd frontend\web
npm run build
```
**Output:** `✓ Generating static pages (13/13) (0 errors).`

---

## 10. Data Source & Implementation Classification

In strict adherence to competition rules and engineering honesty:

- **REAL (True Implementation):** PostgreSQL 16 + PostGIS 3.4 spatial indices, JWT authentication, RBAC authorization, Dijkstra multi-modal pathfinding, transaction-safe offline sync idempotency.
- **CONFIGURED (Domain-Calibrated):** NER road and rail corridors (NH-27, NH-06, Lumding junction, Pandu Port), mountain transit delay equations, truck fuel consumption tariffs.
- **SIMULATION (Sandbox Environment):** Disruption scenario simulation engine, pre/post accessibility scoring.
- **SYNTHETIC (Evaluation Dataset):** Landslide hazard training vectors and Out-of-Distribution benchmark sets (Scenarios A through E).
- **GOVERNMENT INTEGRATIONS (IMD, Bhuvan, Sentinel, Gati Shakti, FOIS, IWAI):** Transparently audited as `CONFIGURED` / `SIMULATION` with local domain fallbacks; no unverified live external credentials claimed.

---

## 11. Complete Documentation Index

| Document Path | Description |
| :--- | :--- |
| [`docs/FINAL_ARCHITECTURE.md`](./docs/FINAL_ARCHITECTURE.md) | Comprehensive implemented architecture specification |
| [`docs/FINAL_FEATURE_MATRIX.md`](./docs/FINAL_FEATURE_MATRIX.md) | 56-feature matrix with status and data classifications |
| [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md) | Exhaustive REST API reference across all 24 URL routers |
| [`docs/DATABASE_REFERENCE.md`](./docs/DATABASE_REFERENCE.md) | Database models, spatial geometries, and relationships |
| [`docs/FINAL_PERFORMANCE_REPORT.md`](./docs/FINAL_PERFORMANCE_REPORT.md) | Microsecond-resolution empirical benchmark results |
| [`docs/FINAL_AI_ML_REPORT.md`](./docs/FINAL_AI_ML_REPORT.md) | ML model architectures, OOD generalization, and disclosures |
| [`docs/DEPLOYMENT_READINESS.md`](./docs/DEPLOYMENT_READINESS.md) | Gap analysis comparing Dev vs Staging vs Enterprise Production |
| [`docs/SIH_FINAL_DEMO_SCRIPT.md`](./docs/SIH_FINAL_DEMO_SCRIPT.md) | 5–10 minute minute-by-minute judge presentation script |
| [`docs/SIH_BACKUP_DEMO_SCRIPT.md`](./docs/SIH_BACKUP_DEMO_SCRIPT.md) | Zero-internet / standalone CLI contingency presentation flow |
| [`docs/SIH_PRESENTATION_CONTENT.md`](./docs/SIH_PRESENTATION_CONTENT.md) | 15-slide pitch presentation deck outline |
| [`docs/SIH_JUDGE_QA.md`](./docs/SIH_JUDGE_QA.md) | 25 detailed evaluator questions and technical answers |
| [`docs/SIH_TECHNICAL_DEFENSE.md`](./docs/SIH_TECHNICAL_DEFENSE.md) | Deep technical defense addressing edge-case criticisms |
| [`docs/ENVIRONMENT_SETUP.md`](./docs/ENVIRONMENT_SETUP.md) | Windows-friendly local host environment setup guide |
| [`docs/FINAL_DEMO_SETUP.md`](./docs/FINAL_DEMO_SETUP.md) | Pre-demo setup, deterministic seeding, and reset protocol |
| [`docs/architecture/`](./docs/architecture/) | 8 Mermaid diagrams covering architecture, flows, and pipelines |

---

## 12. Known Limitations & Production Roadmap

1. **Synthetic Machine Learning Vectors:** Landslide risk models are trained on domain-synthesized environmental physics. Field deployment requires integration with live ground-truth inventory data from the Geological Survey of India (GSI).
2. **Inland Waterway Seasonality:** National Waterway 2 river barging along the Brahmaputra is draft-restricted during dry pre-monsoon months (January–April).
3. **Telecom Infrastructure:** Production nationwide rollout requires direct integration with CDAC SMS and telecom USSD gateways for non-smartphone drivers.

---

## 13. License & Authorship

- **Product Name:** RouteIQ
- **Description:** Smart Multi-Modal Logistics & Risk Intelligence Platform
- **SIH Problem Statement:** SIH26002 by Ministry of Development of North Eastern Region (MDoNER)
- **Developed By:** RouteIQ Developer Team
- **License:** Proprietary / Hackathon Evaluation Rights Reserved
