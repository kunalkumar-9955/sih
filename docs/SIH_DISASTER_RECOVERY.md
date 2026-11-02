# SIH26002: DISASTER RECOVERY & CONTINGENCY PLAN
## Emergency Operational Playbook for Live Demo Failures
**Project: AI-Based Smart Logistics & Accessibility Intelligence Platform for North Eastern Region (NER)**

---

### Overview
During a live hackathon evaluation or high-stakes presentation, unforeseen technical failures can occur. This document outlines deterministic, step-by-step recovery procedures for nine failure modes, utilizing existing repository scripts, fallback flags, and local architectural resilience.

---

### Failure Scenario A: Backend Server Crash or Process Exit
**Symptoms:** Command Center displays network disconnect banner; API calls return `502 Bad Gateway` or `Connection Refused`.
**Recovery Procedure:**
1. Check Terminal 1 to identify crash trace.
2. In PowerShell, restart Django server immediately:
   ```powershell
   cd "c:\Users\Kunal Kumar\Desktop\SIH\backend"
   python manage.py runserver 127.0.0.1:8000
   ```
3. If port 8000 is orphaned/stuck:
   ```powershell
   Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
   python manage.py runserver 127.0.0.1:8000
   ```
4. Verify recovery at `http://127.0.0.1:8000/api/v1/demo/readiness/`.

---

### Failure Scenario B: Frontend Web App Crash or Freeze
**Symptoms:** Browser tab unresponsive, Next.js hot reload error, blank white page.
**Recovery Procedure:**
1. Hard refresh browser: `Ctrl + Shift + R` (bypasses service worker cache).
2. If Next.js terminal crashed, restart dev server:
   ```powershell
   cd "c:\Users\Kunal Kumar\Desktop\SIH\frontend\web"
   npm run dev
   ```
3. If dev server fails to compile, run pre-built production server:
   ```powershell
   npm run start
   ```

---

### Failure Scenario C: PostgreSQL Database Service Stop / Disconnect
**Symptoms:** Backend logs `OperationalError: could not connect to server: Connection refused`.
**Recovery Procedure:**
1. Verify PostgreSQL service status in PowerShell:
   ```powershell
   Get-Service -Name "postgresql*"
   ```
2. Restart PostgreSQL Windows service:
   ```powershell
   Restart-Service -Name "postgresql*"
   ```
3. Test database connectivity:
   ```powershell
   python manage.py check --database default
   ```

---

### Failure Scenario D: AI Model Artifact Missing or Deserialization Failure
**Symptoms:** Hazard prediction endpoint throws `ModelLoadError` or `FileNotFoundError` for `.joblib` files.
**Recovery Procedure:**
1. The platform incorporates a built-in deterministic heuristic fallback:
   - If `hazard_xgboost.joblib` fails to load, `apps/hazards/services/hazard_classifier.py` automatically falls back to the calibrated heuristic rule engine (`HeuristicHazardEstimator`) without raising an unhandled 500 error.
2. To regenerate model artifacts immediately:
   ```powershell
   cd backend
   python manage.py train_hazard_model --synthetic --save
   ```

---

### Failure Scenario E: Total Venue Internet Outage
**Symptoms:** External Wi-Fi drops completely; venue displays connection lost.
**Recovery Procedure:**
- **Zero Impact on Core Platform:** The entire SIH26002 system operates on native `localhost` (Django on 8000, Next.js on 3000, PostgreSQL on 5432).
- Leaflet map tiles for NER key corridors are locally cached in the browser storage.
- Explain to judges: *"This actually demonstrates our core value proposition—the platform is designed for zero-connectivity NER conditions and functions completely offline."*

---

### Failure Scenario F: External Government API Timeout (IMD / ULIP / FOIS)
**Symptoms:** Upstream weather or railway status sync times out.
**Recovery Procedure:**
1. The backend ingestion layer operates with built-in circuit breakers and simulation fallbacks (`USE_MOCK_INGESTION=True` in settings).
2. If an external API stalls, the ingestion service automatically serves the latest cached or simulated telemetry packet without blocking user threads.
3. No manual intervention required; fallback logging confirms simulation mode active.

---

### Failure Scenario G: Demo Data Inconsistent or Corrupted During Live Testing
**Symptoms:** Corridors display unintended test hazard states or duplicate active trips from previous clicks.
**Recovery Procedure:**
1. Execute the deterministic demo reset command:
   ```powershell
   cd backend
   python manage.py phase10_demo --seed 42
   ```
2. This resets database tables, re-populates pristine NER corridors, and initializes the standard baseline state in less than 4 seconds.
3. Refresh the Command Center browser page.

---

### Failure Scenario H: Browser WebGL or Leaflet Map Render Glitch
**Symptoms:** Map canvas appears greyed out or tiles do not snap properly.
**Recovery Procedure:**
1. Trigger browser window resize: press `F11` twice (toggles full-screen mode, forcing Leaflet `map.invalidateSize()`).
2. Alternatively, switch to the dedicated Corridor Table View at `/routes` which renders complete tabular metrics without canvas dependencies.

---

### Failure Scenario I: Flutter / Mobile Device Projection Failure
**Symptoms:** Mobile screen mirroring (Scrcpy/AirPlay) disconnects or mobile emulator freezes.
**Recovery Procedure:**
1. Do not halt the presentation.
2. Transition smoothly to the Web Command Center's **Driver Emulation & Sync Audit Panel** at `http://localhost:3000/offline-sync`.
3. Explain to judges: *"While our driver uses the Flutter mobile app, the central command center provides real-time audit logs of the driver's offline queue, vector clocks, and dead-reckoning coordinate stream."*
4. Show the code implementation in `mobile/lib/services/offline_routing_service.dart` to defend the mobile architecture.
