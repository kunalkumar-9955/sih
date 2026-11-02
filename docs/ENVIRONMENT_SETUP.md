# SIH26002 — Local Environment Setup Guide (Windows Host)

**Project:** SIH26002 — AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Host Architecture:** Windows 10/11 (Native, Non-Docker Execution)  
**Target Runtimes:** Python 3.11–3.14, Node.js 18–20, PostgreSQL 16 with PostGIS 3.4  

---

## 1. Prerequisites Overview

| Component | Minimum Version | Recommended Installation Method on Windows |
| :--- | :--- | :--- |
| **Python** | 3.11+ (tested on 3.14.5) | [python.org](https://www.python.org/downloads/) (Ensure "Add python.exe to PATH" is checked) |
| **PostgreSQL** | 16.x | [EnterpriseDB PostgreSQL Installer](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads) |
| **PostGIS Extension** | 3.4.x | Installed via Stack Builder during PostgreSQL installation |
| **Node.js & npm** | Node v18+ / npm v9+ | [nodejs.org](https://nodejs.org/) LTS Windows Installer |
| **Git** (Optional) | 2.40+ | [git-scm.com](https://git-scm.com/) Windows Installer |
| **Flutter SDK** (Optional) | 3.19+ | [flutter.dev](https://docs.flutter.dev/get-started/install/windows) for mobile driver APK |

> [!NOTE]
> **Docker is NOT used:** In strict accordance with competition rules and local host constraints, this platform runs directly on the Windows operating system without container overhead or virtualization dependencies.

---

## 2. PostgreSQL & PostGIS Spatial Database Setup

### Step 2.1: Verify PostgreSQL Service
Open Windows PowerShell (Run as Administrator if needed):
```powershell
# Verify PostgreSQL service is active
Get-Service -Name postgresql*
```

### Step 2.2: Create Database and User
Open `psql` command prompt or pgAdmin:
```sql
-- Create dedicated application user
CREATE USER sih_user WITH PASSWORD 'sih_pass';

-- Create database
CREATE DATABASE sih_db OWNER sih_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sih_db TO sih_user;

-- Connect to sih_db and enable PostGIS extension
\c sih_db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Verify PostGIS version
SELECT PostGIS_Full_Version();
```

---

## 3. Python Backend Environment Setup

### Step 3.1: Navigate to Backend Directory
```powershell
cd "c:\Users\Kunal Kumar\Desktop\SIH\backend"
```

### Step 3.2: Install Python Dependencies
```powershell
pip install -r requirements.txt
```
*Core dependencies:* Django 6.0+, djangorestframework, psycopg 3.x, numpy, scipy, scikit-learn, joblib, drf-spectacular, corsheaders.

### Step 3.3: Configure Environment Variables
Copy `.env.example` in the project root to `.env` (or rely on development defaults in `backend/config/settings/development.py`):
```powershell
Copy-Item ..\.env.example ..\.env
```
Default database connection string: `postgis://sih_user:sih_pass@localhost:5432/sih_db`

### Step 3.4: Apply Migrations
```powershell
python manage.py migrate
```

### Step 3.5: Run Django Integrity Check
```powershell
python manage.py check
```
*Expected Output:* `System check identified no issues (0 silenced).`

---

## 4. Deterministic Demo Initialization

Initialize the baseline North Eastern Region multimodal graph, hazard models, fleet vehicles, and freight shipments using random seed `42`:
```powershell
# From the project root or backend directory:
python manage.py phase10_demo --seed 42
```
Or execute the automated helper:
```powershell
powershell -ExecutionPolicy Bypass -File ..\scripts\setup_demo.ps1
```
*This populates 26 transport nodes, 54 multimodal edges, and 3 multimodal terminals across Assam, Meghalaya, Tripura, and Mizoram.*

---

## 5. Starting the Backend Server

Start the Django REST Framework API server on port 8000:
```powershell
# Option A: Helper script
powershell -ExecutionPolicy Bypass -File ..\scripts\start_backend.ps1

# Option B: Direct command
python manage.py runserver 8000
```
- API Base: `http://localhost:8000/api/v1/`
- Interactive Swagger UI: `http://localhost:8000/api/docs/`
- Demo Readiness Endpoint: `http://localhost:8000/api/v1/demo/readiness/`

---

## 6. Starting the Web Frontend (Next.js 14)

### Step 6.1: Navigate to Frontend Web Directory
Open a new PowerShell terminal:
```powershell
cd "c:\Users\Kunal Kumar\Desktop\SIH\frontend\web"
```

### Step 6.2: Install npm Packages (First-time only)
```powershell
npm install
```

### Step 6.3: Start Web Development Server
```powershell
# Option A: Helper script
powershell -ExecutionPolicy Bypass -File ..\..\scripts\start_web.ps1

# Option B: Direct command
npm run dev
```
- Command Center Dashboard: `http://localhost:3000/command-center`
- Multimodal Network Topology: `http://localhost:3000/graph`
- Routing & Detour Engine: `http://localhost:3000/routes`
- Disruption Sandbox: `http://localhost:3000/simulations`
- Fleet Optimization: `http://localhost:3000/fleet`

---

## 7. Mobile Driver Application (Flutter)

The mobile client is located at `frontend/mobile/`. If Flutter SDK is installed:

### Step 7.1: Verify Flutter Installation
```powershell
flutter doctor
```

### Step 7.2: Run Mobile Analyzer and Tests
```powershell
cd "c:\Users\Kunal Kumar\Desktop\SIH\frontend\mobile"
flutter pub get
flutter analyze
flutter test
```

### Step 7.3: Build Debug Android APK
```powershell
flutter build apk --debug
```
*Output artifact:* `frontend/mobile/build/app/outputs/flutter-apk/app-debug.apk`

*(If Flutter SDK is not installed on the evaluation machine, the mobile client can be evaluated via static code inspection of the offline synchronization queue in `frontend/mobile/lib/services/sync_queue_service.dart` and the offline routing engine in `offline_routing_service.dart`.)*

---

## 8. Verification & Pre-Flight Smoke Test

Run the full automated test suite to confirm zero regressions:
```powershell
cd "c:\Users\Kunal Kumar\Desktop\SIH\backend"
python -m pytest -q
```
*Expected Result:* **201 passed in ~55s (100% pass rate).**
