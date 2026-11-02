# SIH26002: DEMO DAY OPERATIONAL CHECKLIST
## Pre-Flight Verification & Live Presentation Readiness Guide
**Project: AI-Based Smart Logistics & Accessibility Intelligence Platform for North Eastern Region (NER)**

---

### Phase 1: The Day Before Demo Day (24 Hours Prior)

#### 1. Hardware & Environment
- [ ] Primary laptop plugged into reliable power source; power plan set to **High Performance** (disable sleep/hibernate).
- [ ] Backup laptop tested with identical repository clone, Python 3.14/Node 20 environment, and verified PostgreSQL instance.
- [ ] HDMI/Type-C display adapter tested with external monitors/projectors at 1080p (16:9 aspect ratio).
- [ ] Offline local presentation deck [`SIH26002_Final_Presentation.pptx`](file:///c:/Users/Kunal%20Kumar/Desktop/SIH/SIH26002_Final_Presentation.pptx) saved to Desktop and backed up on USB drive.
- [ ] PDF version of presentation exported as fallback: `SIH26002_Final_Presentation.pdf`.

#### 2. Database & Data Integrity
- [ ] PostgreSQL 16 service is active and running on `localhost:5432`.
- [ ] PostGIS 3.4 spatial extension confirmed enabled (`SELECT PostGIS_Version();`).
- [ ] Database migrations verified up to date:
  ```powershell
  cd backend
  python manage.py makemigrations --check
  python manage.py migrate
  ```
- [ ] Deterministic seed data loaded and verified:
  ```powershell
  python manage.py phase10_demo --seed 42
  ```

#### 3. Backend & AI Artifacts
- [ ] Python dependencies verified without conflicts.
- [ ] AI model artifacts confirmed present and readable:
  - `backend/models/hazard_xgboost.joblib`
  - `backend/models/eta_regressor.joblib`
- [ ] Backend test suite passes 100%:
  ```powershell
  python manage.py test
  # Confirm 201/201 tests passed
  ```

#### 4. Frontend & Command Center
- [ ] Next.js dependencies verified (`npm list --depth=0` in `frontend/web/`).
- [ ] Production build passes cleanly:
  ```powershell
  cd frontend/web
  npm run build
  ```
- [ ] Leaflet map tile caching verified for offline operation (in case of venue Wi-Fi failure).

---

### Phase 2: 30 Minutes Before Presentation

#### 1. Service Launch Sequence
- [ ] **Step 1: Start Backend Server**
  Open Terminal 1 (PowerShell):
  ```powershell
  cd "c:\Users\Kunal Kumar\Desktop\SIH\backend"
  python manage.py runserver 127.0.0.1:8000
  ```
  *Verify output shows Django development server running at `http://127.0.0.1:8000/`.*

- [ ] **Step 2: Start Frontend Web Server**
  Open Terminal 2 (PowerShell):
  ```powershell
  cd "c:\Users\Kunal Kumar\Desktop\SIH\frontend\web"
  npm run dev
  ```
  *Verify output shows Next.js dev server ready on `http://localhost:3000`.*

#### 2. Live Health & Readiness Verification
- [ ] In browser, navigate to: `http://127.0.0.1:8000/api/v1/demo/readiness/`
  *Verify JSON response contains:*
  ```json
  {
    "status": "READY",
    "checks_passed": 15,
    "checks_total": 15,
    "verdict": "ALL_SYSTEMS_GO"
  }
  ```
- [ ] In browser, navigate to Command Center: `http://localhost:3000`
  *Verify dashboard loads, map renders Guwahati, Silchar, and Brahmaputra river corridors.*

#### 3. Deterministic State Reset
- [ ] Execute clean demo reset so judges see fresh initial conditions:
  ```powershell
  cd backend
  python manage.py phase10_demo --seed 42
  ```
  *Verify console confirms `PASSED_24_OF_24`.*

---

### Phase 3: 5 Minutes Before Entering Presentation Room

#### 1. System Cleanup & Distraction Blocking
- [ ] Turn on Windows **Focus Assist / Do Not Disturb** (block notifications, Slack, WhatsApp, email popups).
- [ ] Close all non-essential browser windows, IDEs, and heavy background processes.
- [ ] Open exactly three clean browser tabs in Google Chrome/Brave:
  - Tab 1: `http://localhost:3000` (Command Center)
  - Tab 2: `http://localhost:3000/routes` or `/hazards` (Corridor View)
  - Tab 3: `http://127.0.0.1:8000/api/v1/demo/readiness/` (Technical proof tab)
- [ ] Open PowerPoint [`SIH26002_Final_Presentation.pptx`](file:///c:/Users/Kunal%20Kumar/Desktop/SIH/SIH26002_Final_Presentation.pptx) in Presenter View.
- [ ] Set browser zoom to 100% or 110% for crisp projector legibility.

#### 2. Team Role Assignment
- [ ] **Speaker 1 (Narrative Lead):** Delivers Problem, NER Geography, Architecture, and Impact.
- [ ] **Speaker 2 (Technical & Demo Lead):** Operates live Command Center UI, executes deterministic demo triggers, and explains routing/optimization math.
- [ ] **Speaker 3 (Defense & Q&A Lead):** Handles AI/ML validation, PostGIS spatial queries, and offline conflict resolution questions using the Cheat Sheet.
