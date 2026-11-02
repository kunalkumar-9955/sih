# SIH26002: FINAL SCREENSHOT CAPTURE CHECKLIST
## Official Visual Evidence & UI Capture Protocol
**Project: AI-Based Smart Logistics & Accessibility Intelligence Platform for North Eastern Region (NER)**

---

### Purpose
This checklist details the 14 essential UI screenshots required for project documentation, judge portfolios, technical defense attachments, and submission portals. 

> **Important Rule:** Only capture actual, live UI screens rendered from the running Next.js Command Center (`http://localhost:3000`) and Django REST Framework API (`http://127.0.0.1:8000`). Never fabricate or alter mockups.

---

### Checklist of 14 Key Screenshots

| # | Screen Name | Route / URL | Key Elements to Capture |
|---|-------------|-------------|-------------------------|
| 1 | **User Authentication & RBAC** | `http://localhost:3000/login` | Persona selector (Logistics Admin, Dispatcher, Driver, Relief Authority), JWT token handling indicator. |
| 2 | **Command Center Overview** | `http://localhost:3000/` | Full-screen dashboard, KPI metrics (Active Trips, Monitored Corridors, Hazard Alerts), high-level map. |
| 3 | **NER Multimodal Network Graph** | `http://localhost:3000/network` | Leaflet map displaying layered Road (NH-6, GS Road), Rail (NFR), and Inland Waterway (NW-2 Brahmaputra). |
| 4 | **Multimodal Route Comparison** | `http://localhost:3000/routes` | Side-by-side modal showing Direct Road vs Multimodal (Road+Rail+Waterway) with distance, time, and risk trade-offs. |
| 5 | **AI Geohazard Intelligence** | `http://localhost:3000/hazards` | Active hazard cards, XGBoost hazard probability gauge (e.g. 0.88 CRITICAL), rainfall/slope feature contributions. |
| 6 | **Dynamic Reroute Alert Modal** | `http://localhost:3000/routes?alert=active` | Prominent alert banner: "Landslide Risk Detected on NH-6 - Automatic Multimodal Bypass Recommended". |
| 7 | **Fleet & Depot Optimization** | `http://localhost:3000/fleet-optimization` | Multi-depot assignment table, capacity utilization bar charts, before-and-after deadhead mile savings. |
| 8 | **Freight Marketplace & Matching** | `http://localhost:3000/marketplace` | Shipper cargo listings, carrier vehicle bids, load compatibility badges (Perishable, Medical, Hazardous). |
| 9 | **Live Shipment Tracking** | `http://localhost:3000/tracking/TRK-2026-001` | Waypoint milestone progress, ML-calculated ETA countdown, current telemetry status, driver details. |
| 10 | **Regional Accessibility Index** | `http://localhost:3000/accessibility` | Heatmap / choropleth map of NER districts colored by vulnerability index (0 to 100), isolated district warnings. |
| 11 | **Disruption Simulation Studio** | `http://localhost:3000/simulation` | Interactive disaster injection slider (Rainfall: 150mm, Landslide trigger), cascading corridor failure visualization. |
| 12 | **Offline Driver Sync Audit** | `http://localhost:3000/offline-sync` | Visual sync queue showing buffered transactions, vector clock counters, and reconciliation status indicators. |
| 13 | **System Demo Readiness Report** | `http://127.0.0.1:8000/api/v1/demo/readiness/` | Browser tab displaying raw JSON payload: `15/15 PASS`, `ALL_SYSTEMS_GO`. |
| 14 | **Swagger / OpenAPI Documentation** | `http://127.0.0.1:8000/api/docs/` | Interactive API documentation showing endpoints for routing, hazards, optimization, and telemetry. |

---

### Standard Operating Procedure for Image Capture
1. **Resolution:** Capture at 1920×1080 (1080p) or 1440p using lossless PNG format.
2. **Browser State:** Set browser to 100% zoom with DevTools closed (clean viewport).
3. **Data State:** Seed database with `python manage.py phase10_demo --seed 42` before capturing to ensure consistent and coherent sample data.
4. **Storage Directory:** Save images to `docs/screenshots/` using standard filenames (e.g., `01_login_rbac.png`, `02_command_center.png`, ...).
