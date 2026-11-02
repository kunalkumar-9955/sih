# SIH26002: VIDEO DEMONSTRATION RECORDING SCRIPT
## 5-to-8 Minute Video Recording Guide with Exact Screen Cues & Spoken Narration
**Project: AI-Based Smart Logistics & Accessibility Intelligence Platform for North Eastern Region (NER)**

---

### Video Overview
- **Total Duration:** 6 minutes 30 seconds (Target range: 5 to 8 minutes).
- **Target Audience:** SIH Jury, Ministry Evaluators, and Technical Assessors.
- **Recording Tools:** OBS Studio / Screen Studio recording at 1080p 60fps, crisp microphone audio.
- **Visuals:** Full-screen browser (`http://localhost:3000`), terminal output, and presentation architecture slides.

---

### Sequence & Script Breakdown

#### Scene 1: Introduction & The NER Problem (0:00 – 1:00)
- **Visual:** Title Slide of `SIH26002_Final_Presentation.pptx`, followed by NER Map showing the 22-km Siliguri Corridor.
- **Narration:**
  > "Respected judges, welcome to our presentation of SIH26002: an AI-based Smart Logistics and Accessibility Intelligence Platform specifically engineered for India's North Eastern Region.
  > The North East spans eight states connected to mainland India through a single, narrow 22-kilometer passage known as the Siliguri Corridor. Every year, intense monsoon rains trigger over 200 landslides, flash floods, and road washouts. High-altitude mountain passes are single-lane, and commercial drivers frequently travel through extended cellular dead zones with zero connectivity. When a road washes out, essential medical supplies and food grains are stranded for weeks.
  > Today, we demonstrate a working platform that solves this through predictive geohazard AI, dynamic multimodal rerouting across roads, railways, and the Brahmaputra inland waterway, and an offline-first mobile architecture."

---

#### Scene 2: Enterprise Command Center & Network Health (1:00 – 1:50)
- **Visual:** Switch to browser: `http://localhost:3000` (Command Center Dashboard). Hover over network status cards and regional accessibility index.
- **Narration:**
  > "Here is our enterprise Command Center. At a glance, regional logistics controllers and disaster relief authorities have complete situational awareness.
  > We see our active transport network across Assam, Meghalaya, Tripura, and Arunachal Pradesh. On the left, our Regional Accessibility Index monitors supply chain vulnerability across districts on a scale of 0 to 100.
  > Notice the key operational corridors currently monitored: the Guwahati to Shillong expressway, National Highway 6 into Silchar, and National Waterway 2 along the Brahmaputra river. All core corridors are currently in a NORMAL state with green status indicators."

---

#### Scene 3: Normal Route & Freight Dispatch (1:50 – 2:40)
- **Visual:** Navigate to Route Dispatch / Tracking view. Select an active consignment: 12 tons of emergency medical cargo originating in Guwahati destined for Silchar.
- **Narration:**
  > "Let us examine a critical consignment: 12 tons of temperature-sensitive medical supplies originating at Guwahati Central Medical Depot, destined for Silchar Civil Hospital.
  > Under normal conditions, our system dispatches a heavy commercial vehicle via National Highway 6 through Meghalaya. The primary road distance is 312 kilometers, with an estimated transit time of 8.5 hours.
  > The route is safe, our ML-augmented ETA predictor confirms clear roads, and the shipment is dispatched."

---

#### Scene 4: Extreme Monsoon Event & AI Hazard Detection (2:40 – 3:35)
- **Visual:** Open Disruption Simulation modal or trigger simulation step. Set rainfall intensity to 145mm/24hr over the East Jaintia Hills corridor.
- **Narration:**
  > "Now, a severe weather front hits the region. Heavy monsoon rainfall exceeding 140 millimeters batters the East Jaintia Hills.
  > Watch the Command Center as our XGBoost AI Geohazard Engine evaluates the incoming environmental telemetry. In 1.7 milliseconds, the model analyzes rainfall accumulation, 34-degree terrain slope angles, and soil saturation indices.
  > Instantly, the hazard score for the Sonapur tunnel sector on NH-6 spikes from 0.15 to 0.88, triggering a CRITICAL HAZARD alert with a high risk of active debris flow and mudslide.
  > Notice that our explainability module reveals the primary risk drivers: 68% rainfall saturation and 24% slope vulnerability."

---

#### Scene 5: Dynamic Multimodal Rerouting (3:35 – 4:40)
- **Visual:** The system automatically issues a reroute alert. The map renders the alternative multimodal path: Road to Guwahati Rail Yard → Northeast Frontier Railway freight rake to Badarpur Junction → Final road transfer to Silchar.
- **Narration:**
  > "Immediately, the platform's risk-weighted routing algorithm recalculates the journey. Instead of sending the driver into an imminent landslide trap, the system flags the corridor as impassable and evaluates alternative transport modes.
  > While road-only detours through alternate mountain passes would add 16 perilous hours, the engine detects available multimodal capacity:
  > The consignment is dynamically rerouted to the nearest multimodal terminal at Guwahati Rail Yard, loaded onto a Northeast Frontier Railway freight rake to Badarpur, followed by short-haul last-mile road transport into Silchar.
  > Risk drops from 0.88 to 0.12, saving the consignment from catastrophic stranding."

---

#### Scene 6: Multi-Depot Fleet Optimization (4:40 – 5:25)
- **Visual:** Navigate to `/fleet-optimization`. Click 'Optimize Fleet Distribution'. Show tabular before-and-after metrics.
- **Narration:**
  > "Simultaneously, dispatchers must optimize regional vehicle capacity during the emergency.
  > Our fleet optimization engine solves a multi-depot Capacitated Vehicle Routing Problem with time windows across 5 regional hubs. In 37.5 milliseconds, it groups 20 pending regional consignments, respects axle weight limits, and prioritizes perishable food and medicines.
  > The result is a 24% reduction in deadhead transit miles and 100% adherence to critical delivery deadlines."

---

#### Scene 7: Offline-First Field Architecture & Sync (5:25 – 6:05)
- **Visual:** Navigate to `/offline-sync` or toggle browser 'Offline' mode in DevTools Network tab. Show persistent queue accumulating local driver actions, then syncing upon reconnect.
- **Narration:**
  > "Now, what happens to the driver in the mountain valley where cellular signals drop completely?
  > The driver's mobile client operates on a resilient offline-first architecture. The local sub-graph and waypoints are pre-cached in SQLite. Using onboard accelerometer and gyro sensors with an Extended Kalman Filter, the driver retains navigation awareness even without satellite lock.
  > When the driver confirms cargo handover offline, the transaction is safely committed to a local sync queue. The moment connectivity is restored, the queue synchronizes with our PostGIS backend using vector clock reconciliation, guaranteeing zero data loss."

---

#### Scene 8: Conclusion & Technical Rigor (6:05 – 6:30)
- **Visual:** Return to Command Center showing 15/15 PASS readiness verdict, then return to final slide of presentation deck.
- **Narration:**
  > "To conclude, this is not a mock concept. Our platform backend is backed by 201 passing automated tests, sub-40 millisecond optimization benchmarks, and 15 out of 15 verified operational subsystems.
  > We provide the North Eastern Region with the predictive intelligence, multimodal resilience, and offline dependability necessary to keep vital lifelines open through any disaster.
  > Thank you, and we look forward to your questions."
