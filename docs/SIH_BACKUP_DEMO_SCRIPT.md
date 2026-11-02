# SIH26002 — Backup & Contingency Demonstration Script

**Project:** SIH26002 — AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Target Scenario:** Demonstrating platform capabilities when external networks, live cloud endpoints, or web interfaces experience catastrophic failure during judging.  
**Guiding Principle:** **Full transparency. Clearly display `DEMO / SIMULATION MODE`. Never disguise fallback data as live telemetry.**  

---

## 1. Contingency Scenarios & Immediate Redirection Matrix

| Failure Mode Observed | Immediate Root Cause | Fallback Action & Command | Verbal Bridge for Evaluators |
| :--- | :--- | :--- | :--- |
| **Next.js Web Frontend Fails to Load** | Port conflict or browser shader crash | Switch to CLI Terminal and run: `python manage.py phase10_demo --seed 42` | *"Our backend orchestration runs headlessly over CLI and REST, ensuring mission-critical continuity even if UI rendering fails."* |
| **PostgreSQL Database Disconnect** | Service stopped or session lock | Run in Admin PowerShell: `net start postgresql-x64-16` then `curl http://localhost:8000/api/v1/demo/readiness/` | *"PostgreSQL service reconnected; PostGIS spatial indices and topology tables verified intact."* |
| **External Weather / InSAR Ingestion Timeout** | Network outage or API rate-limit | Automatic fallback: `MockWeatherProvider` and `MockTerrainProvider` | *"The platform uses local domain-calibrated regional fallbacks when satellite or meteorological feeds are unreachable."* |
| **ML Model Artifact Loading Error** | File lock or corrupt `.joblib` | Automatic fallback: Rule-based terrain heuristic engages | *"Our architecture implements fault-tolerant degradation: when statistical ML weights are inaccessible, physics heuristics maintain safe routing."* |
| **Zero Internet Connectivity** | Evaluation venue Wi-Fi failure | Zero impact: Platform is 100% locally hosted on `localhost` with offline graph cache | *"The entire platform operates on a self-contained local stack, mirroring the zero-connectivity operational reality of mountain corridors."* |

---

## 2. Standalone CLI-Only Backup Demonstration (5 Minutes)

If the web browser cannot be used at all, execute the complete presentation from Windows PowerShell:

### Step 1: Prove System Health & 15 Subsystems (Minute 1)
```powershell
cd "c:\Users\Kunal Kumar\Desktop\SIH\backend"
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development'); django.setup(); from apps.core.demo_views import DemoReadinessView; from django.test import RequestFactory; req = RequestFactory().get('/api/v1/demo/readiness/'); res = DemoReadinessView.as_view()(req); print('DEMO READINESS:', res.data['status']); print(res.data['checks'])"
```
*Expected Output:*
```
DEMO READINESS: READY
{'database': 'PASS', 'postgis': 'PASS', 'migrations': 'PASS', 'transport_graph': 'PASS', 'hazards': 'PASS', 'routing': 'PASS', 'fleet': 'PASS', 'freight': 'PASS', 'marketplace': 'PASS', 'tracking': 'PASS', 'accessibility': 'PASS', 'optimization': 'PASS', 'simulation': 'PASS', 'ai_models': 'PASS', 'offline_bundle': 'PASS'}
```

### Step 2: Execute Deterministic 24-Step Flow with Live Audit Output (Minutes 2–4)
```powershell
python manage.py phase10_demo --seed 42
```
*Explain to Judges as steps print to console:*
- **Steps 1–10:** Baseline state initialization (Guwahati–Shillong–Silchar topology, normal accessibility 0.88).
- **Steps 11–13:** Monsoon cloudburst injection along NH-27 (Risk jumps from 0.12 to 0.78, edge marked `BLOCKED`).
- **Steps 14–16:** Automated Dijkstra rerouting selects SAFEST road detour, then switches containerized freight to Pandu Port river barge along NW-2.
- **Steps 17–18:** Dynamic LTL load consolidation merges 2 partial shipments into 1 medium truck, raising utilization to 87%.
- **Steps 19–20:** Predictive ETA engine decomposes delays into rainfall crawl and geohazard caution.
- **Steps 21–24:** Command center logs tactical recommendations; road clearance restores network accessibility.

### Step 3: Demonstrate Out-of-Distribution ML Generalization (Minute 5)
```powershell
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development'); django.setup(); from apps.hazards.ml.unseen_generalization import run_unseen_generalization_evaluation; rep = run_unseen_generalization_evaluation(seed=42); print(rep['notice']); print('Scenarios Tested:', list(rep['scenarios'].keys()))"
```
*Expected Output:*
```
Synthetic evaluation only. These results do not represent production-world accuracy.
Scenarios Tested: ['scenario_a', 'scenario_b', 'scenario_c', 'scenario_d', 'scenario_e']
```

---

## 3. UI Standalone Fallback Screens

If the web UI is active but external map tiles fail to load:
1. Navigate directly to **Command Center Table View** (`http://localhost:3000/command-center`).
2. Show the **Subsystem Readiness Modal** displaying all 15 PASS statuses.
3. Show the **24-Step Audit Trail** rendered with green completion checkmarks.
4. Point out the clear UI label: `[DEMO / SIMULATION MODE]`.
