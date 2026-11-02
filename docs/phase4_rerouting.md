# SIH26002 — Phase 4: Dynamic Risk-Aware Routing & Active Trip Rerouting

## 1. Overview

Phase 4 of the **AI-Based Smart Multi-Modal Logistics & Risk Intelligence Platform for the North Eastern Region (NER)** introduces autonomous geohazard monitoring, topological disaster propagation, and active in-transit trip rerouting.

When landslides, flash floods, or road washouts alter corridor safety during transit, the platform:
1. Detects risk degradation along the active route.
2. Propagates geohazard shocks through connected network hops.
3. Computes viable multi-modal or highway bypass alternatives.
4. Generates an auditable `RerouteEvent` with safety improvement metrics.
5. Alerts dispatchers and drivers via Web and Mobile consoles for one-tap acknowledgement or autonomous enforcement.

---

## 2. Core Architecture & Services

```
                                 [ Geohazard Shocks / Landslide Alerts ]
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          apps.hazards.services.propagation                             │
│                              HazardPropagationService                                  │
│  - 1-hop neighbor decay (0.60)                                                         │
│  - 2-hop neighbor decay (0.25)                                                         │
│  - Never overwrites higher-confidence ML inference scores                              │
└──────────────────────────────────────────────────┬─────────────────────────────────────┘
                                                   │ Updates TransportEdge & HazardScore
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              apps.routing.services                                     │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐  │
│  │  RouteRiskEvaluator   │   │  HazardChangeDetector │   │ RouteCacheInvalidator    │  │
│  │  Live max & mean      │   │  Delta >= 0.15        │   │ Redis / LocMem           │  │
│  │  hazard scores        │   │  Critical >= 0.85     │   │ Key namespace flush      │  │
│  │  Risky / Critical     │   │  Closure / Blockage   │   │                          │  │
│  └───────────┬───────────┘   └───────────┬───────────┘   └──────────────────────────┘  │
│              │                           │                                             │
│              └───────────────┬───────────┘                                             │
│                              ▼                                                         │
│                ┌───────────────────────────┐                                           │
│                │  RerouteDecisionService   │                                           │
│                │  Idempotent calculation   │                                           │
│                │  Alternative comparison   │                                           │
│                │  >= 10% improvement rule  │                                           │
│                └─────────────┬─────────────┘                                           │
│                              │                                                         │
│                              ▼                                                         │
│                ┌───────────────────────────┐                                           │
│                │ RerouteNotificationService│                                           │
│                │ Multi-lingual alert       │                                           │
│                │ EN, AS, HI translations   │                                           │
│                └───────────────────────────┘                                           │
└──────────────────────────────────┬─────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   apps.trips                                           │
│  ┌────────────────────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │              Trip Model                │  │          RerouteEvent Model          │  │
│  │  - route_version (v1, v2, ...)         │  │  - trip, old_route, new_route        │  │
│  │  - route_assigned_at                   │  │  - trigger_reason, triggering_edges  │  │
│  │  - route_hazard_snapshot_at            │  │  - improvement_pct                   │  │
│  │  - route_snapshot (JSON)               │  │  - status (PENDING/APPLIED/DISMISSED)│  │
│  └────────────────────────────────────────┘  └──────────────────────────────────────┘  │
└──────────────────────────────────┬─────────────────────────────────────────────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
    [ Next.js Web Portal ]                  [ Flutter Driver App ]
  - Live risk badges                      - Corridor hazard alert bottom sheet
  - Reroute audit modal                   - 1-tap Accept bypass route
  - Dispatcher manual check               - Voice / Multilingual banner
```

---

## 3. Threshold Configuration (`SIH_SETTINGS`)

All reroute and propagation thresholds are fully configurable via environment variables in `backend/config/settings/base.py`:

| Parameter | Default | Environment Variable | Purpose |
| :--- | :--- | :--- | :--- |
| `REROUTE_HAZARD_DELTA_THRESHOLD` | `0.15` | `REROUTE_HAZARD_DELTA_THRESHOLD` | Minimum score increase required before evaluating route recalculation |
| `REROUTE_MIN_IMPROVEMENT_PCT` | `0.10` | `REROUTE_MIN_IMPROVEMENT_PCT` | Candidate route must be at least 10% safer to justify rerouting an active trip |
| `REROUTE_CRITICAL_THRESHOLD` | `0.85` | `REROUTE_CRITICAL_THRESHOLD` | Forces mandatory rerouting regardless of improvement if route reaches critical |
| `HAZARD_PROPAGATION_1HOP_DECAY` | `0.60` | `HAZARD_PROPAGATION_1HOP_DECAY` | Spatial decay multiplier for directly adjacent edges |
| `HAZARD_PROPAGATION_2HOP_DECAY` | `0.25` | `HAZARD_PROPAGATION_2HOP_DECAY` | Spatial decay multiplier for secondary network edges |

---

## 4. API Reference

All Phase 4 endpoints are authenticated via JWT Bearer tokens under `/api/v1/trips/`:

### 4.1. Live Route Risk Assessment
```http
GET /api/v1/trips/{trip_id}/route-risk/
```
**Response (200 OK):**
```json
{
  "route_id": "8f48de01-6bc4-462e-81f4-5cd806aed2a7",
  "trip_id": "1ce20391-5265-4b2f-b5f3-319bf043ae3f",
  "trip_status": "ACTIVE",
  "route_version": 1,
  "route_assigned_at": "2026-09-09T01:30:00Z",
  "evaluated_at": "2026-09-09T01:38:00Z",
  "edge_count": 2,
  "max_hazard_score": 0.45,
  "mean_hazard_score": 0.275,
  "risky_edge_count": 1,
  "critical_edge_count": 0,
  "blocked_edges": [],
  "safety_level": "MODERATE",
  "has_critical_or_blocked": false,
  "edge_evaluations": [
    {
      "edge_id": "e1-uuid",
      "source": "Guwahati Multimodal Hub",
      "target": "Nongpoh Checkpost",
      "status": "OPEN",
      "hazard_score": 0.10,
      "severity": "LOW",
      "is_blocked": false
    },
    {
      "edge_id": "e2-uuid",
      "source": "Nongpoh Checkpost",
      "target": "Shillong Logistics Hub",
      "status": "OPEN",
      "hazard_score": 0.45,
      "severity": "MODERATE",
      "is_blocked": false
    }
  ]
}
```

### 4.2. Recalculate Route & Reroute Evaluation
```http
POST /api/v1/trips/{trip_id}/recalculate-route/
Content-Type: application/json

{
  "force": false,
  "auto_apply": false
}
```
**Response (201 Created if rerouted, 200 OK if safe):**
```json
{
  "rerouted": true,
  "event_id": "7b0907fc-cb63-44c1-8418-47c0b05bfe34",
  "status": "PENDING",
  "applied": false,
  "is_mandatory": false,
  "improvement_pct": 0.65,
  "old_route_id": "8f48de01-6bc4-462e-81f4-5cd806aed2a7",
  "new_route_id": "93dbbf31-0164-4e78-9e66-419bba519658",
  "trigger_reason": "Hazard increased by +0.35 (baseline 0.10 → now 0.45)",
  "notification": {
    "title": "⚠️ Safer Route Available",
    "message": "Hazard increased on current corridor. A safer alternative reduces risk by 65% (15 min longer).",
    "urgency": "HIGH",
    "is_mandatory": false,
    "metrics": {
      "time_delta_min": 15.0,
      "distance_delta_km": 10.0,
      "old_max_hazard": 0.45,
      "new_max_hazard": 0.12
    }
  }
}
```

### 4.3. List Reroute Events
```http
GET /api/v1/trips/{trip_id}/reroute-events/
```
Returns paginated list of all auditable reroute events for the trip with status history.

### 4.4. Driver Acknowledge Reroute Event
```http
POST /api/v1/trips/{trip_id}/reroute-events/{event_id}/acknowledge/
Content-Type: application/json

{
  "action": "ACCEPT",
  "notes": "Switching to Byrnihat bypass corridor"
}
```
When `action="ACCEPT"`, the trip route is automatically transitioned to the new route, `trip.route_version` increments by 1, and the event status transitions to `APPLIED`.

---

## 5. Idempotency & Safety Guarantees

1. **No Alert Storms**: If an active reroute event with status `PENDING` or `SENT` already exists for a target corridor, duplicate recalculation calls return the existing event reference without creating duplicate database rows or push notifications.
2. **Mandatory Bypass Enforcement**: When a corridor experiences physical road closures (`status="BLOCKED"`, `is_available=False`) or hit `CRITICAL` geohazard threshold (`>= 0.85`), the reroute decision service marks the decision as `is_mandatory = True`. Drivers cannot decline a mandatory closure bypass.
3. **Non-Degrading Hop Propagation**: Spatial shock decay never reduces an existing edge's higher-confidence machine learning prediction or manual government road status override.
