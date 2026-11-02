# RouteIQ (SIH26002) â€” UI/UX, Role Separation & Branding Specification

**Product Name:** RouteIQ  
**Subtitle:** AI-Powered Resilient Logistics Intelligence for Northeast India  
**Technical/Problem Identifier:** SIH26002  
**Date:** September 2026  
**Status:** COMPLETE & PRODUCTION-READY  

---

## 1. Executive Summary

This phase delivers a complete overhaul of the human-computer interface and access boundary for **RouteIQ** (SIH26002). The platform now enforces strict role-based presentation and data access separation between **Admin/Operations Users** and **Field Logistics Drivers**, provides real local multi-language switching across 6 Northeast languages, implements an instantaneous high-contrast Light/Dark theme system with storage persistence, and solidifies professional product branding.

---

## 2. Product Identity & Branding

- **Selected Brand Name:** **RouteIQ**
- **Brand Subtitle:** AI-Powered Resilient Logistics Intelligence for Northeast India
- **Technical Reference:** SIH26002 preserved across all technical endpoints, headers, footers, and system documentation.
- **Brand Mark:** Modern SVG icon combining the Brahmaputra logistics corridor, interconnected multimodal network nodes, and resilient navigation vectors.
- **Color System:**
  - *Primary Teal / Emerald:* `#0d9488` (Light) / `#14b8a6` (Dark)
  - *Accent Cyan:* `#06b6d4` / `#38bdf8`
  - *Critical Alert:* `#ef4444` / `#f87171`
  - *Warning Orange:* `#f59e0b` / `#fbbf24`
  - *Dark Canvas:* `#0a0f1d`, Surface `#111927`, Border `#1f2937`
  - *Light Canvas:* `#f8fafc`, Surface `#ffffff`, Border `#e2e8f0`

---

## 3. Role-Based Routing & Dashboard Separation

### 3.1 Role Architecture
RouteIQ reuses the canonical backend RBAC roles without creating artificial or duplicated accounts:
- `SUPER_ADMIN` / `MINISTRY_ADMIN` / `OPERATIONS`: Directed to **Operational Command Center** (`/command-center` or `/`).
- `DRIVER`: Directed to **Driver Console** (`/driver`).
- `FLEET_MANAGER`: Directed to `/fleet`.
- `DISPATCHER` / `LOGISTICS_MANAGER`: Directed to `/marketplace` / `/trips`.

### 3.2 Security Enforcement
- **Frontend Guard (`ProtectedRoute.tsx`):**
  - Drivers attempting to navigate to `/command-center`, `/routes`, `/simulation`, `/fleet`, or `/marketplace` are automatically intercepted and redirected to `/driver` or rendered an explicit HTTP 403 Access Denied screen.
- **Backend Guard (`IsAdminLevel` & Queryset Scoping):**
  - Backend endpoints strictly block unauthorized calls. For example, `GET /api/v1/simulations/` returns `HTTP 403 Forbidden` for driver tokens.
  - Driver endpoints (`/api/v1/driver/*`) strictly scope results to `request.user.driver_profile`.

---

## 4. Driver Experience ("What Do I Need To Do Right Now?")

### 4.1 Driver Dashboard (`/driver`)
- **Cab Header:** Warm personalized greeting, driver name, vehicle registration (`AS-01-GB-4819`), live GPS badge, real-time connectivity status (`ONLINE` / `OFFLINE`), and sync status indicator.
- **Hero Card â€” Current Trip:**
  - Route: Guwahati Hub (ISBT) â†’ Silchar Terminal via NH-27 / NH-06.
  - Live progress meter, ETA, remaining distance (312 km), road safety score (`94% - PASSABLE`), and primary action button `"Continue Trip"` + `"View Route Details"`.
- **Active Shipment Manifest:**
  - Cargo: Assam Orthodox Tea (Grade A), 14.5 MT.
  - Consignee: Silchar Tea Auction Warehousing.
  - Cold-Chain IoT status (+4.2Â°C, compliant).
- **Route Hazard Alert:**
  - Shows *only* hazards intersecting the driver's active path (e.g., NH-06 Sonapur Landslide risk).
  - One-click trigger for `"Review Reroute"` modal with comparative detour metrics (time, distance, safety score).
- **Quick Action Grid:**
  - My Trip (`/driver/trip`)
  - Navigation Map (`/driver/map`)
  - Digital Manifest (`/driver/shipment`)
  - Route Alerts (`/driver/alerts`)
  - Offline Sync / Cache Manager
  - Emergency SOS (One-touch broadcast to State Disaster Control)

### 4.2 Driver Trip View (`/driver/trip`)
- Step-by-step corridor progress:
  1. Origin: Guwahati ISBT (Completed)
  2. Current Waypoint: Shillong Bypass (Passed)
  3. Next Waypoint: Jowai Pass (Live - ETA 42 min)
  4. Destination: Silchar Multimodal Hub (Pending)
- In-cab reroute prompt with side-by-side alternative analysis (`Accept Detour` / `Keep Current Route`).

### 4.3 Driver Offline Mode
- Visible toggle and automatic offline detection.
- Offline banner informing driver: *"Offline mode active â€” navigation and cached manifest operating via local SQLite/IndexedDB store"*.
- Queued telemetry and SOS actions stored locally and auto-dispatched on reconnection.

---

## 5. Admin / Operations Command Center

The Admin experience remains the comprehensive operational brain of Northeast logistics:
- **Network Health:** Total corridor segments (24 active), disruption count, risk corridors.
- **Live Operations:** Active fleet vehicles, delayed consignments, multimodal switches.
- **Multimodal Transport Graph:** Interactive Leaflet GIS mapping with road (NH-27/NH-06), rail (NF Railway), and inland waterways (NW-2 Brahmaputra).
- **Simulation Suite:** Monte-Carlo rainfall and landslide impact modeling with scenario injection.
- **System Health:** Telemetry ingestion latency, DB pool status, cache hit rates, offline bundle freshness.

---

## 6. Real Multi-Language Localization System

### 6.1 Supported Languages
1. **English (en)**
2. **Hindi (hi)** â€” à¤¹à¤¿à¤¨à¥à¤¦à¥€
3. **Assamese (as)** â€” à¦…à¦¸à¦®à§€à¦¯à¦¼à¦¾
4. **Bengali (bn)** â€” à¦¬à¦¾à¦‚à¦²à¦¾
5. **Manipuri (mni)** â€” à¦®à§ˆà¦¤à§ˆà¦²à§‹à¦¨à§
6. **Khasi (kha)** â€” Ka Ktien Khasi

### 6.2 Architecture
- Centralized static dictionary mapping in `src/locales/{en,hi,as,bn,mni,kha}.ts`.
- `LanguageContext.tsx` providing `locale`, `setLocale()`, and `t(key)` helper.
- **Zero API lag:** Translations switch instantaneously in the DOM without external service round-trips.
- **Persistence:** Saved in `localStorage.getItem('RouteIQ_language')` and re-hydrated on boot.

---

## 7. Dual Dark/Light Theme System

### 7.1 Tokens & Styles
- Integrated CSS custom properties in `src/styles/globals.css`:
  - `--bg-primary`, `--bg-secondary`, `--bg-card`
  - `--text-primary`, `--text-secondary`, `--text-muted`
  - `--border-color`, `--accent-primary`
- Controlled via root attribute `document.documentElement.setAttribute('data-theme', theme)`.
- Real Sun/Moon toggle in the persistent navigation header.
- **Persistence:** Stored in `localStorage.getItem('RouteIQ_theme')`.

---

## 8. Verification & Quality Gate Results

- **Django System Check:** Clean (0 issues).
- **Django Migrations:** No pending migrations (`makemigrations --check` passed).
- **Backend Tests:** 6/6 tests passed in `apps/drivers/tests.py` verifying profile auto-creation, profile editing, driver dashboard data isolation, driver 403 on simulation runs, admin permission on simulations, and driver SOS dispatch.
- **Next.js Production Build:** 18/18 static pages successfully compiled with TypeScript validation.

