# SIH26002 — Final Demo Setup & Safe Reset Guide

**Project:** SIH26002 — AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Target Environment:** Local Windows Demonstration Laptop / Evaluation Terminal  
**Audience:** Hackathon Presenters, Evaluators, and DevOps Engineers  

---

## 1. Quick 2-Minute Pre-Demo Initialization

To prepare the terminal before judges arrive:

```powershell
# Step 1: Open PowerShell and enter the backend directory
cd "c:\Users\Kunal Kumar\Desktop\SIH\backend"

# Step 2: Ensure database schema is migrated
python manage.py migrate --noinput

# Step 3: Seed deterministic baseline topology (Seed 42)
python manage.py phase10_demo --seed 42

# Step 4: Verify system health
python manage.py check
```

---

## 2. Live Demo Readiness Probe (`GET /api/v1/demo/readiness/`)

The platform includes a dedicated readiness probe validating 15 subsystems:

```powershell
# Probe system readiness via curl / PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/demo/readiness/" -Method Get
```

### Expected Response Payload:
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

*In the Next.js UI (`http://localhost:3000/command-center`), the top header displays a green badge: `DEMO READINESS: READY (15/15 PASS)`. Clicking it opens the real-time subsystem diagnostic modal.*

---

## 3. Safe Demo Reset Mechanism (`POST /api/v1/demo/reset/`)

Between judge presentations, the demonstration state should be reset to clear simulated mudslides, reroute history, and test orders without wiping real database users or base map infrastructure.

### Safety Guards Enforced:
1. **Explicit Confirmation Flag:** `confirm_demo_reset: true` required.
2. **Explicit Mode Tag:** `mode: "DEMO"` required.
3. **Selective Scoping:**
   - Deletes `HazardIncident.objects.filter(source=HazardIncident.IncidentSource.SYNTHETIC_DEMO)`
   - Deletes `DisruptionSimulationRun.objects.all()`
   - Deletes `DecisionRecommendation.objects.all()`
   - Deletes `OptimizationRun.objects.filter(is_simulation=True)`
4. **Zero Destruction of Production Data:** Real user accounts, genuine vehicle records, and baseline transport nodes/edges are strictly protected.

### Reset Execution via REST API:
```bash
curl -X POST http://localhost:8000/api/v1/demo/reset/ \
  -H "Content-Type: application/json" \
  -d '{"confirm_demo_reset": true, "mode": "DEMO"}'
```

### Reset Execution via Web UI:
1. Navigate to `http://localhost:3000/command-center`.
2. Click **Safe Demo Reset** in the top action bar.
3. Confirm the modal prompt.
4. The system purges simulation records and reactivates the baseline network in $< 50\text{ ms}$.

---

## 4. End-to-End Demo Trigger (`POST /api/v1/demo/orchestrate/`)

To run the complete 24-step demo flow automatically:

### Option A: Via Command Center UI
Click **Run Phase 10 Demo (24 Steps)**. The live audit card timeline renders each step with its execution status, timestamp, and details.

### Option B: Via Management Command
```powershell
python manage.py phase10_demo --seed 42
```
*Output: All 24 steps executed sequentially with zero errors (`PASSED_24_OF_24`).*

---

## 5. Contingency Fallback Plan (Zero-Internet Mode)

If internet access is unavailable or an external API times out during the judging session:
- **Map Tiles:** OpenStreetMap tiles fallback to vector topology rendering.
- **Weather Telemetry:** `MockWeatherProvider` in `apps/hazards/services/weather_service.py` provides cached seasonal monsoon data for Guwahati, Shillong, Silchar, and Agartala.
- **Terrain DEM:** `MockTerrainProvider` provides pre-calibrated slope and elevation gradients for hill corridors.
- **Visual Indicator:** The UI clearly displays `[CONFIGURED TELEMETRY]` or `[SIMULATION MODE]`—never claiming unverified live external feeds.
