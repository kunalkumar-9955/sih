# SIH26002: Jury & Live Demonstration Script

**Platform:** AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Corridor:** Guwahati (Assam) \u2194 Nongpoh \u2194 Shillong (Meghalaya) \u2194 Silchar (Assam)  
**Target Duration:** 8–10 minutes  

---

### Prerequisites
1. **Backend Server Running:**
   ```powershell
   cd backend
   python manage.py runserver 8000
   ```
2. **Web Portal Running:**
   ```powershell
   cd frontend/web
   npm run dev
   # Opens at http://localhost:3000
   ```
3. **Driver Mobile App:**
   - Run on Android emulator or physical device via Flutter, or view web driver simulator view.

---

### Step-by-Step Live Demonstration Flow

#### STEP 1: Route Planning & Cargo Constraints
- Open Web Portal at `http://localhost:3000/routes`.
- Select Origin: **Guwahati Multimodal Hub (Assam)**.
- Select Destination: **Shillong Logistics Depot (Meghalaya)**.
- Cargo Type: Select **Perishable / Critical Goods** (Weight: 14 Tons, Height: 3.8m).

#### STEP 2: Multimodal Route Comparison
- Click **"Calculate Optimal Routes"**.
- The engine presents four distinct routing alternatives:
  - **FASTEST:** Direct NH-6 via Nongpoh (Estimated: 2h 15m).
  - **SAFEST:** Weather-resilient alignment with lower landslide exposure.
  - **CHEAPEST:** Optimized for fuel efficiency and toll bypass.
  - **MULTIMODAL:** Road freight to Pandu Port, Brahmaputra NW-2 barge, intermodal transfer to Azara rail.

#### STEP 3: Operational Dashboard & Hazard Map
- Navigate to `http://localhost:3000/trips`.
- Observe the **Live Network Map** displaying active corridor edges in green (`OPEN`).
- Review the **Accessibility Intelligence Card**:
  - Current Accessibility Score: **85 / 100** (`HIGH ACCESSIBILITY`).
  - Factor Breakdown: Connectivity Density (92%), Geohazard Safety (88%), Multimodal Redundancy (75%).

#### STEP 4: Trigger Controlled Simulation Scenario (DEMO LANDSLIDE)
- In the **"Controlled Scenario Simulation"** panel on `/trips`, click the red button:
  - **"Landslide Blockage"** (`LANDSLIDE`).
- Note the amber simulation badge: `[DEMO SIMULATION ACTIVE]`.
- API Call executed: `POST /api/v1/ingestion/scenarios/activate/` with `{"scenario_name": "LANDSLIDE"}`.

#### STEP 5: Real-Time Hazard Propagation
- The system updates the hazard index of the critical mountain pass segment `EDGE-NGP-SHL` to **0.95**.
- Status transitions automatically from `OPEN` $\to$ `BLOCKED`.
- Incident report created: *"Heavy slope failure near Nongpoh bypass (NH-6)"*.

#### STEP 6: Route Risk Degradation Detection
- The backend `HazardChangeDetector` detects that the active trip's current route traverses a `BLOCKED` edge.
- Route risk score increases past critical threshold ($> 0.70$).
- System generates `RerouteEvent(priority="CRITICAL", trigger_reason="BLOCKED_EDGE")`.

#### STEP 7: Autonomous Alternative Route Calculation
- The dynamic rerouting engine recalculates a detour route bypassing Nongpoh via the Eastern ridge detour.
- Path clearance verified; weight constraints re-checked.

#### STEP 8: Driver Receives Critical Advisory
- On the Driver Application / Mobile Interface:
  - High-priority audible alert and visual banner appear:
  - *"CRITICAL: Hazard detected on NH-6 ahead. Landslide blockage confirmed. Alternative route available (-18 min delay)."*

#### STEP 9: Driver Acknowledges & Accepts Reroute
- Driver taps **"Accept Detour"** on the mobile navigation screen.
- Navigation seamlessly switches active polyline to the alternative corridor.
- Dashboard updates trip status to `REROUTED`.

#### STEP 10: Offline Resilience Demonstration
- Simulate mountain pass cellular blackout by toggling offline mode (airplane mode or network disconnect).
- Driver app status indicator switches to: `[OFFLINE MODE]`.

#### STEP 11: Local A* Routing from Cached Graph
- Request route recalculation while fully disconnected.
- The client-side embedded A* engine calculates the optimal path locally in **< 8ms** using the cached PostGIS topology bundle.

#### STEP 12: Offline Hazard Observation Reporting
- While offline, driver submits a hazard observation:
  - Type: *Rockfall debris on shoulder*.
  - Location: GPS lat/long captured locally.
- App stores event in the **Durable Sync Queue** (`pending_sync_count: 1`).

#### STEP 13: Reconnect Network
- Restore network connectivity.
- Mobile background sync worker detects internet availability.

#### STEP 14: Batch Sync Execution
- App submits the queued events via `POST /api/v1/sync/batch/`.
- Monotonic timestamp verification and conflict resolution engine process the batch with 0 conflicts.

#### STEP 15: Web Dashboard Synchronization
- In the Web Portal, observe the real-time refresh:
  - Driver's offline-reported rockfall appears on the live map with a timestamp and driver provenance.

#### STEP 16: Emergency SOS Demonstration
- Press and hold the red **"SOS EMERGENCY"** button on the driver app.
- System broadcasts high-priority distress coordinates to the dispatch console.
- Web dashboard immediately sounds dispatch alert and highlights driver coordinates on the map.

#### RESET TO BASELINE:
- In the web scenario controller, click **"Reset Baseline"** (`NORMAL`).
- All network edges return to `OPEN`, hazard scores return to normal, and the demo is instantly ready for another run.
