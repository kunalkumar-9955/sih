# SIH26002 — Phase 5: Offline-First Navigation & Resilient Sync

## 1. Executive Architecture Overview

In the North Eastern Region (NER) of India, freight corridors pass through extreme terrain: steep gorges, heavy monsoon downpours, river crossings, and extensive cellular connectivity dead zones (e.g., NH6 Meghalaya–Barak Valley corridor). 

Phase 5 equips the **SIH26002 Platform** with a robust, production-ready **offline-first architecture** designed to function reliably without cellular connectivity. Drivers maintain continuous navigation, local hazard avoidance, and location telemetry even inside deep mountain canyons, synchronizing seamlessly with the central cloud platform when connectivity is restored.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DRIVER MOBILE APP (EDGE)                           │
│                                                                             │
│  ┌───────────────────────┐   ┌────────────────────────┐   ┌──────────────┐  │
│  │ Local Graph Cache     │   │ On-Device A* Pathfinder│   │ EKF + Dead   │  │
│  │ • Versioned JSON/DB   │──>│ • Haversine Heuristic  │<──│ Reckoning    │  │
│  │ • SHA-256 Validated   │   │ • <10ms Query Latency  │   │ GPS Filter   │  │
│  └───────────────────────┘   └────────────────────────┘   └──────────────┘  │
│              │                                                   │          │
│              ▼                                                   ▼          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Durable FIFO Sync Queue (UUID Idempotency, Exponential Backoff)        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Batch Sync (HTTP/REST)
                                       │ Auto-Drain upon Reconnection
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CENTRAL CLOUD PLATFORM (DJANGO REST)                    │
│                                                                             │
│  ┌────────────────────────┐  ┌─────────────────────────┐  ┌──────────────┐  │
│  │ Batch Sync Processor   │  │ Conflict Resolver       │  │ Emergency    │  │
│  │ • Atomic per-event     │─>│ • Monotonic State Rules │─>│ SOS Distress │  │
│  │ • Deduplication        │  │ • Route Version Checks  │  │ Dispatch     │  │
│  └────────────────────────┘  └─────────────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Offline Graph Cache & Integrity Architecture

### 2.1 Canonical Representation
The multimodal transport graph and active hazard snapshots are bundled into a self-contained canonical JSON structure:
- **Nodes**: ID, name, code, node type, WGS84 coordinates `[lon, lat]`, elevation, state, district, intermodal capabilities.
- **Edges**: ID, source node, target node, transport mode (`ROAD`, `RAIL`, `WATER`, `TRANSFER`), distance in metres, base transit time, INR cost, payload capacity, operational status (`OPEN`, `RESTRICTED`, `CRITICAL`, `BLOCKED`), current hazard index, severity, and full LineString geometry.
- **Integrity Checksum**: 256-bit SHA-256 hash computed deterministically across canonical JSON (sorted keys, compact separators).

### 2.2 Versioning & Lightweight Verification
To avoid redundant bandwidth consumption over 2G/3G edge connections:
1. Mobile requests lightweight version metadata via `GET /api/v1/sync/graph/version/?region=NER_CORRIDOR`.
2. If `version_tag` matches local cache, no download occurs.
3. If version differs, client requests full bundle via `GET /api/v1/sync/graph/download/?region=NER_CORRIDOR`.
4. Client validates downloaded payload hash against `checksum_sha256` before persisting to `SharedPreferences` / local SQLite.

---

## 3. On-Device A* Routing Engine

The on-device pathfinder (`OfflineAStarRouter` in Python / `OfflineRoutingService` in Flutter Dart) executes locally on the driver's device with no server dependence:

### 3.1 Admissible Haversine Distance Heuristic
For any node $n$ and destination target node $T$:
$$h(n) = \frac{\text{haversine}(n, T)}{v_{\text{max}}}$$
where $v_{\text{max}} = 25.0\text{ m/s}$ (~90 km/h) represents the physical maximum achievable speed across corridor highways. This guarantees the heuristic is strictly admissible ($h(n) \le h^*(n)$) ensuring optimal path finding.

### 3.2 Routing Policy Formulations
Edge traversal weight $w(e)$ is evaluated dynamically based on policy:
- **FASTEST**:
  $$w(e) = t_{\text{base}} \cdot s_{\text{mult}} + 1.5 \cdot t_{\text{transfer}} + 5.0 \cdot H$$
- **SAFEST**:
  $$w(e) = t_{\text{base}} \cdot s_{\text{mult}} \cdot \left(1.0 + 9.0 \cdot H^2\right) + t_{\text{transfer}} + 250.0 \cdot H$$
  *(CRITICAL edges receive $s_{\text{mult}} = 8.0$ penalty).*
- **CHEAPEST**:
  $$w(e) = C_{\text{INR}} \cdot s_{\text{mult}} + C_{\text{transfer}} + 0.05 \cdot t_{\text{base}}$$
- **MULTIMODAL**:
  $$w(e) = t_{\text{base}} \cdot s_{\text{mult}} \cdot (1.0 + 1.5 \cdot H) \cdot \mu_{\text{mode}} + 0.9 \cdot t_{\text{transfer}}$$
  *($\mu_{\text{RAIL}} = 0.80$, $\mu_{\text{WATER}} = 0.70$).*

### 3.3 Physical & Operational Constraint Filtering
- `BLOCKED`, `SEASONAL`, and `UNDER_REPAIR` segments are assigned infinite weight ($w(e) = \infty$) and excluded from the search tree.
- Gross vehicle weight constraints: if $W_{\text{cargo}} > \text{Capacity}_{\text{max}}$, edge is excluded.
- Maximum hazard tolerance filtering: edges with $H > H_{\text{allowed}}$ are pruned.

### 3.4 Query Latency Benchmark
In unit testing over corridor subgraphs (4 to 100 nodes), pathfinding queries consistently complete in **< 0.5 milliseconds**, drastically below the 10ms target threshold.

---

## 4. GPS Resilience: Extended Kalman Filter & Dead Reckoning

In the steep gorges of Meghalaya and Assam, satellite visibility frequently suffers from multipath reflection and complete line-of-sight dropouts.

### 4.1 Kinematic State Vector
The state vector is maintained as:
$$\mathbf{x}_k = \begin{bmatrix} \text{lat}_k \\ \text{lon}_k \\ v_{\text{lat}, k} \\ v_{\text{lon}, k} \end{bmatrix}$$

### 4.2 Prediction & Measurement Update
1. **Prediction**: Position updates continuously based on estimated velocity:
   $$\text{lat}_k = \text{lat}_{k-1} + v_{\text{lat}} \cdot \Delta t$$
   $$\text{lon}_k = \text{lon}_{k-1} + v_{\text{lon}} \cdot \Delta t$$
2. **Gross Jump Rejection**: If reported GPS measurement deviates by $> 150\text{ m}$ from prediction, it is flagged as multipath reflection and rejected.
3. **Adaptive Kalman Gain**: Measurement noise variance $R$ scales quadratically with reported GPS accuracy:
   $$R = \left(\frac{\text{accuracy}_m}{111132.0}\right)^2$$
   $$K = \frac{P_{k|k-1}}{P_{k|k-1} + R}$$

### 4.3 Dead Reckoning Fallback
When satellite signal is completely lost ($\Delta t > 3.0\text{ s}$ or accuracy $> 60\text{ m}$):
- Position extrapolates along road azimuth using last known velocity and heading.
- State uncertainty covariance $P$ increases monotonically with elapsed time.
- Status badge switches to `DEAD RECKONING` mode with high-visibility driver warning.

---

## 5. Offline Sync Queue & Conflict Resolution

### 5.1 Durable Client FIFO Queue
All telemetry, status transitions, hazard reports, and SOS beacons are enqueued into a durable persistent FIFO queue (`SyncQueueItem` in local storage):
- **Idempotency**: Every event is assigned a client-generated UUID `idempotency_key`.
- **Automatic Drain**: When network connectivity is restored, the queue flushes in batches of up to 50 events.

### 5.2 Server Conflict Resolution Rules
The backend `SyncConflictResolver` validates events atomically:

| Scenario | Server State | Client Event | Resolution |
| :--- | :--- | :--- | :--- |
| **Monotonic Trip Progress** | `PLANNED` | `ACTIVE` | **APPLIED**: State updated, departure time logged. |
| **Monotonic Trip Progress** | `ACTIVE` | `COMPLETED` | **APPLIED**: State updated, arrival time logged. |
| **Terminal Regression** | `COMPLETED` | `ACTIVE` | **CONFLICT**: Rejected. Prevents corruption of completed trips. |
| **Duplicate Submission** | `APPLIED` | (Same UUID) | **DUPLICATE**: Idempotently acknowledged without re-processing. |
| **Stale Route Version** | `route_v2` | Ack for `v1` | **CONFLICT**: Rejected with current server route version. |
| **Temporal Drift** | Server Time $T$ | $T - 25\text{ h}$ | **REJECTED**: Outside 24-hour sanity window. |
| **Future Clock Skew** | Server Time $T$ | $T + 15\text{ m}$ | **REJECTED**: Exceeds 10-minute future clock allowance. |

---

## 6. End-to-End Test Verification

The Phase 5 test suite was executed against the active PostgreSQL/PostGIS database and standalone unit runners:

1. **Unit Tests (`apps/sync/tests/test_phase5_unit.py`)**:
   - 14 tests passing (0.16s execution time).
   - Verifies SHA-256 determinism, Haversine geometry, A* policy weighting, constraint pruning, <10ms execution, and conflict resolution rules.
2. **Integration Tests (`apps/sync/tests/test_phase5_integration.py`)**:
   - Tests `OfflineGraphBundle` creation, `GET /api/v1/sync/graph/version/`, `GET /api/v1/sync/graph/download/`.
   - Tests multi-event batch synchronization (`LOCATION_UPDATE`, `HAZARD_REPORT`, `TRIP_STATUS`).
   - Tests idempotency deduplication with unique UUID keys.
   - Tests rejection of state regressions on completed trips.
   - Tests emergency SOS beacon registration and live diagnostics monitoring.
