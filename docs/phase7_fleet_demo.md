# SIH26002 Phase 7: Fleet Intelligence & Emergency Operations Demonstration Guide

**Project:** SIH26002 — AI-Based Smart Logistics & Accessibility Intelligence Platform for North Eastern Region (NER)  
**Corridor:** Guwahati – Shillong – Silchar (Assam / Meghalaya)  
**Objective:** End-to-end, 20-step reproducible evaluation walkthrough demonstrating fleet availability, multi-factor load matching with mathematical explanations, dynamic landslide-triggered rerouting, deadline risk intelligence, SOS triage dispatch, disaster fleet response mode, and offline-resilient sync.

---

## Prerequisites & Setup

Ensure the backend and frontend are running:
```bash
# Terminal 1: Backend
cd backend
python manage.py runserver 127.0.0.1:8000

# Terminal 2: Web Dashboard
cd frontend/web
npm run dev
# Dashboard accessible at: http://localhost:3000/fleet
```

Default Admin Credentials:
- **Username / Email:** `admin@sih.gov.in`
- **Password:** `Admin@12345`
- **Auth Token:** Generated via `/api/v1/auth/token/` or Django session.

---

## 20-Step Live Demonstration Walkthrough

### STEP 1: Register 3 Fleet Vehicles with Diverse Capacities & Hubs
Create three distinct fleet vehicles representing varied modal and payload characteristics:
1. **AS-01-EV-4010 (Tata Prima Heavy):** 16,000 kg / 45 m³, Heavy Diesel, stationed at Guwahati Multimodal Hub.
2. **ML-05-TR-2201 (Mahindra Bolero Pickup):** 2,500 kg / 12 m³, High-agility 4WD, stationed at Shillong Bypass Depot.
3. **AS-11-IC-9088 (Ashok Leyland Reefer):** 8,000 kg / 25 m³, Refrigerated Cold-Chain, stationed at Silchar Terminal.

```bash
# Register vehicles via Django Shell or Fleet API:
python backend/manage.py shell -c "
from apps.vehicles.models import Vehicle, VehicleType, VehicleStatus
v1, _ = Vehicle.objects.get_or_create(
    registration_number='AS-01-EV-4010',
    defaults=dict(vehicle_type=VehicleType.HEAVY_TRUCK, capacity_kg=16000, capacity_volume_cbm=45.0, status=VehicleStatus.AVAILABLE, fuel_efficiency_kmpl=3.8, operating_region='Assam-Meghalaya-Barak')
)
v2, _ = Vehicle.objects.get_or_create(
    registration_number='ML-05-TR-2201',
    defaults=dict(vehicle_type=VehicleType.MEDIUM_TRUCK, capacity_kg=2500, capacity_volume_cbm=12.0, status=VehicleStatus.AVAILABLE, fuel_efficiency_kmpl=8.5, operating_region='Meghalaya Hills')
)
v3, _ = Vehicle.objects.get_or_create(
    registration_number='AS-11-IC-9088',
    defaults=dict(vehicle_type=VehicleType.MEDIUM_TRUCK, capacity_kg=8000, capacity_volume_cbm=25.0, status=VehicleStatus.AVAILABLE, fuel_efficiency_kmpl=5.2, operating_region='Barak Valley')
)
print('Step 1 Complete: 3 Vehicles created with verified capacities.')
"
```

---

### STEP 2: Create 3 Freight Loads (Normal, Perishable, Emergency)
Create distinct freight shipments with different cargo requirements and urgency levels:
1. **Cement Construction Slabs (Normal):** 12,000 kg dry bulk from Guwahati to Silchar.
2. **Assam Organic Strawberry Crates (Perishable):** 1,800 kg reefer cargo requiring <4°C cold chain, delivery within 8 hours.
3. **Disaster Medical Kits & Blood Units (Emergency):** 350 kg critical supplies to Shillong Civil Hospital with urgent 2-hour window.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/fleet/loads/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Medical Emergency Relief Pack - Blood & Trauma Kits",
    "shipper_name": "NEIGRIHMS Emergency Relief",
    "origin_name": "Guwahati Central Depot",
    "destination_name": "Shillong Civil Hospital Hub",
    "cargo_type": "MEDICAL",
    "weight_kg": 350.0,
    "volume_cbm": 2.5,
    "priority": "EMERGENCY",
    "is_perishable": true,
    "required_delivery_time": "2026-09-10T18:00:00Z"
  }'
```

---

### STEP 3: Automated Load-to-Vehicle Matching Engine
Request automated matching recommendations for the emergency cargo:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/fleet/loads/1/candidates/"
```
The matching engine evaluates all registered vehicles using the 7-factor scoring rubric:
- Physical payload & volume capacity fit
- Euclidean & network proximity to pickup origin
- Availability status & active trip commitments
- Corridor route hazard index (landslide & flood risk)
- Estimated fuel & operational cost
- Delivery deadline slack time and ETA confidence
- Cargo-type compatibility (e.g. reefer vs dry bulk vs general)

---

### STEP 4: Inspect Transparent Matching Explanations
Examine the returned scoring JSON. The platform exposes full explainability for government oversight:
```json
{
  "load_id": 1,
  "candidates": [
    {
      "vehicle_registration": "ML-05-TR-2201",
      "final_score": 92.4,
      "breakdown": {
        "capacity_score": 98.0,
        "distance_score": 90.0,
        "availability_score": 100.0,
        "safety_score": 94.0,
        "cost_score": 88.0,
        "deadline_score": 96.0,
        "compatibility_score": 100.0
      },
      "explanation": "High agility vehicle stationed near Guwahati corridor. Ample capacity (350kg/2500kg). Excellent deadline buffer (slack: 3.2 hrs)."
    }
  ]
}
```

---

### STEP 5: Assign Best Recommended Vehicle (or Manual Override)
Commit the assignment through the dashboard or API:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/fleet/loads/1/match/" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id": 2}'
```
*Verification:* Vehicle status updates to `ASSIGNED` and a `LoadAssignment` record is created.

---

### STEP 6: Initiate Trip Execution
The driver starts the trip from the mobile app or operator console:
```bash
# Trip status moves to IN_TRANSIT, vehicle status moves to ON_TRIP
```

---

### STEP 7: Activate Landslide Scenario on NH-6 Corridor
Trigger the preconfigured real-world geohazard scenario:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/scenarios/landslide/activate/
```
*Effect:* Edge `NH6_SONAPUR_TUNNEL` risk score escalates from 0.12 to 0.94 (CRITICAL status).

---

### STEP 8: Observe Route Risk Escalation
The fleet monitoring engine flags the active trip corridor. The route safety score drops precipitously and the trip enters `HAZARD_ALERT` state.

---

### STEP 9: System Dynamically Recalculates Safe Route
The Dynamic Rerouting Engine computes an alternate bypass via NH-27 / Umroi Road avoiding the Sonapur landslide bottleneck:
- Generates a formal `RerouteEvent`
- Compares original route (132 km, CRITICAL) vs new detour (148 km, SAFE)
- Sends route update notification to the driver's device.

---

### STEP 10: Delivery Deadline Risk Updates to `AT_RISK`
Due to the 42-minute detour delay caused by the landslide bypass, the Deadline Intelligence Engine re-evaluates the load:
- Original Slack Time: +65 minutes
- New Estimated Delay: +42 minutes
- New Slack Time: +23 minutes
- **Deadline Risk Status:** Moves from `ON_TIME` $\to$ `AT_RISK`.
- Operator dashboard updates with a warning banner indicating tight delivery window.

---

### STEP 11: Driver Triggers SOS in Remote High-Risk Zone
Vehicle experiences road slippage or mechanical emergency near Meghalaya border. The driver taps the prominent red SOS button on the Flutter mobile app:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/sync/sos/ \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": 1,
    "trip_id": 1,
    "latitude": 25.6842,
    "longitude": 91.9125,
    "emergency_type": "LANDSLIDE_STRANDED",
    "description": "Mudslide blocked road ahead. Vehicle immobilized safely on shoulder."
  }'
```

---

### STEP 12: Emergency Alert Appears in Operator Rescue Console
On the web dashboard at `http://localhost:3000/fleet`:
- An audio-visual alarm flashes in the **Rescue & SOS Operations** panel.
- Shows SOS ID, Driver name, GPS coordinates, nearest logistics hub (Nongpoh Hub at 8.4 km), and trip context.

---

### STEP 13: Operator Acknowledges and Dispatches Rescue Unit
The dispatcher clicks **Acknowledge & Dispatch Rescue**:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/fleet/emergencies/1/action/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "acknowledge",
    "notes": "Contacted Meghalaya SDRF and Nongpoh Recovery Unit."
  }'

curl -X POST http://127.0.0.1:8000/api/v1/fleet/emergencies/1/action/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "dispatch",
    "notes": "Emergency recovery tow truck dispatched from Nongpoh Hub."
  }'
```
*Audit Log:* Maintains operator timestamp, identity, and action sequence.

---

### STEP 14: Activate Corridor DISASTER_RESPONSE Fleet Mode
Due to multiple concurrent landslides, MDoNER/State Command escalates the network operational state:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/fleet/disaster-mode/ \
  -H "Content-Type: application/json" \
  -d '{
    "activated_by": "State Emergency Control Officer",
    "reason": "Severe flash floods and rockfalls across East Khasi Hills NH-6 sector"
  }'
```
The dashboard switches to an amber **CRITICAL DISASTER RESPONSE ACTIVE** banner.

---

### STEP 15: Verify Priority Scoring Escalation for Relief Loads
With Disaster Mode active, the Deterministic Priority Engine re-scores all pending freight:
- Medical and relief freight automatically escalate to score **100 (EMERGENCY)**.
- Commercial loads are paused or deprioritized.
- Rerouting algorithm applies 500% penalty on high-risk mountain roads, favoring inland waterways (NW-2 Brahmaputra barges) and rail links.

---

### STEP 16: Mobile Driver App Operates in Offline Dead Zone
Simulate complete internet loss (airplane mode / tunnel entry).
The driver arrives at the transfer node and taps **Confirm Pickup**:
- Status update is persisted locally to Flutter SQLite Outbox.
- Idempotency key `uuidv4` generated.
- Mobile UI shows *"Update Queued (Offline Sync Active)"*.

---

### STEP 17: Network Connectivity Restored
The mobile driver device reconnects to 4G/WiFi:
- Flutter background sync service wakes up.
- Flushes the queued `load_status_update` payload to `/api/v1/sync/batch/`.

---

### STEP 18: Backend Idempotent Sync Processing
The backend receives the batched sync payload:
- Verifies idempotency key against `SyncMutationRecord`.
- Applies the status change (`PICKED_UP`) without duplicate processing.
- Logs a successful sync confirmation back to the mobile client.

---

### STEP 19: Emergency Resolved & Relief Cargo Delivered
Rescue team clears vehicle; tow assistance reaches destination safely.
Dispatcher marks the SOS as resolved:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/fleet/emergencies/1/action/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "resolve",
    "notes": "Relief cargo safely transferred and delivered to Shillong Civil Hospital."
  }'
```
Load status transitions to `DELIVERED`.

---

### STEP 20: Return Network to NORMAL_OPERATIONS Mode
Once weather conditions stabilize and all SOS events are cleared, the operator de-escalates the fleet:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/fleet/disaster-mode/reset/ \
  -H "Content-Type: application/json" \
  -d '{"reset_by": "Control Room Lead"}'
```
- Network returns to `NORMAL_OPERATIONS`.
- Commercial freight dispatch resumes standard balancing.
- Complete audit trail of the incident is archived.

---

## Verification & Summary
This 20-step walkthrough verifies the complete Phase 7 fleet optimization, real-time safety rerouting, transparent load matching, emergency rescue lifecycle, and offline synchronization loop.
