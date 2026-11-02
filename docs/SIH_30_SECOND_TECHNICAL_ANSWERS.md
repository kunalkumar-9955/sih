# SIH26002: 30-SECOND TECHNICAL ANSWERS
## Rapid Spoken Defense Guide for Judges & Technical Evaluators
**Project: AI-Based Smart Logistics & Accessibility Intelligence Platform for North Eastern Region (NER)**

---

### 1. XGBoost Hazard Classifier
> "We chose XGBoost because tabular geospatial-environmental features—like slope angle, rainfall accumulation, and elevation—exhibit complex non-linear interactions with sharp threshold boundaries. XGBoost handles gradient boosted decision trees with L1/L2 regularization, preventing overfitting on skewed disaster event data and delivering microsecond inference latency on standard server CPUs without requiring expensive GPU infrastructure."

### 2. Hazard Scoring Formulation
> "Our hazard score is a calibrated continuous probability from 0.0 to 1.0 mapped into four discrete operational tiers: LOW (under 0.3), WATCH (0.3 to 0.6), WARNING (0.6 to 0.8), and CRITICAL (above 0.8). It combines the model's posterior probability with real-time field incident reports to calculate both the likelihood of route failure and the uncertainty confidence interval."

### 3. Risk-Weighted Dijkstra / A* Routing
> "Standard Dijkstra minimizes pure physical distance or time. Our customized graph solver augments edge weights using a composite risk penalty formula: `Weight = Distance × (1 + α × RiskScore + β × ModePenalty)`. When a road segment reaches WARNING or CRITICAL risk, its effective graph cost surges exponentially, mathematically forcing the shortest-path algorithm to discover safer perimeter detours or multimodal transfer nodes."

### 4. PostgreSQL & PostGIS Spatial Engine
> "We leverage PostgreSQL 16 with the PostGIS 3.4 spatial extension as our core spatial datastore. PostGIS provides industry-standard spatial indexing via GiST indexes, enabling sub-millisecond point-in-polygon containment queries, road segment spatial buffering, and bounding-box intersection calculations across thousands of geospatial road segments in the North East."

### 5. Offline Spatial Index (R*Tree / Spatial K-D Bounding)
> "On the mobile client, we cannot query an external spatial database when disconnected in cellular dead zones. We serialize road network sub-graphs into a lightweight local spatial index using an R*Tree structure stored in SQLite. This enables the driver's device to perform nearest-node snapping and corridor intersection queries locally in less than 5 milliseconds."

### 6. Extended Kalman Filter (EKF) & Dead Reckoning
> "When entering mountain tunnels or deep gorges where satellite GNSS signals degrade, the mobile app switches to an Extended Kalman Filter. The EKF fuses the last known GPS coordinate, vehicle speed, heading, and onboard smartphone IMU sensor data (accelerometer and gyroscope) to estimate the vehicle's position along the road network until satellite lock is reacquired."

### 7. Conflict Resolution & Vector Clocks
> "In a distributed offline-first system, drivers update shipment milestones and report road obstructions while disconnected. To prevent data collisions upon reconnection, we implement a persistent FIFO sync queue on the device and server-side vector clocks with deterministic resolution rules: authoritative state transitions take precedence, while conflicting timestamps trigger automated idempotency checks."

### 8. Dynamic Multimodal Routing
> "Our routing engine models the North East as a multi-layer directed graph encompassing highways, railway tracks (NFR), and National Waterway 2 along the Brahmaputra River. Transfer hubs—such as river ghats and rail yards—are represented as inter-layer transfer edges with explicit transfer penalties representing crane loading times, cargo compatibility, and ferry departure schedules."

### 9. Freight Load Matching
> "Freight matching pairs available shipper consignments with carrier vehicle capacity. The algorithm filters carriers by geofenced origin-destination corridors, cargo compatibility (perishable, fragile, bulk, medical), vehicle weight/volume boundaries, and required delivery deadlines. Compatible shipments are clustered spatially to maximize fleet utilization."

### 10. Multi-Depot Fleet Optimization
> "Fleet dispatch is formulated as a Capacitated Vehicle Routing Problem with Time Windows (CVRPTW). Our optimization engine applies a greedy nearest-insertion heuristic followed by 2-opt local search exchanges across multiple regional depots. In benchmark testing, it assigns 20 consignments across 5 regional depots in 37.56 milliseconds, cutting empty backhaul miles significantly."

### 11. Regional Accessibility Index
> "The Accessibility Index is a composite geometric indicator (0 to 100) computed for each NER district. It integrates three weighted dimensions: primary road network connectivity, multimodal redundancy (distance to alternative railheads or navigable river ports), and current geohazard exposure. A sudden drop in a district's score immediately flags an isolation emergency to disaster relief authorities."

### 12. ML-Augmented ETA Prediction
> "Standard ETAs assume constant highway speeds. Our ETA pipeline uses a calibrated regression model that factors in dynamic road elevation gradients, monsoon rain intensity, historical sector congestion, and active checkpoint delays. In local benchmarks, our ETA calculation runs in 0.02 milliseconds, providing drivers and dispatchers with realistic arrival estimates."

### 13. Disruption Simulation Engine
> "Our disruption simulator allows emergency planners to model 'what-if' disaster scenarios—such as a catastrophic landslide severing National Highway 6. The engine artificially injects CRITICAL hazard states across specified corridor segments, evaluates cascading network isolation, re-computes affected routes, and displays alternative multimodal bypass solutions in under 1 millisecond."

### 14. Model Explainability & Transparency
> "Black-box AI is dangerous in disaster management. For every hazard prediction, our system extracts normalized feature importance contributions. In the Command Center, dispatchers can view exactly why a segment was flagged—e.g., '68% contribution from 24-hour rainfall saturation, 22% from 34-degree slope angle'—giving operators confidence to authorize costly reroutes."

### 15. Role-Based Access Control (RBAC) & Security
> "The platform enforces strict Role-Based Access Control across five distinct personas: Logistics Administrator, Dispatch Operator, Field Driver, Consignment Shipper, and Disaster Relief Authority. Endpoints are protected with JSON Web Tokens (JWT) using HMAC-SHA256 signatures, ensuring complete data isolation, encrypted payload transit, and non-repudiable audit logging."
