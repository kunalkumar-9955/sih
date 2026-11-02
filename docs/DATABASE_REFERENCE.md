# SIH26002 — Database Entity & Schema Reference

**Database Engine:** PostgreSQL 16  
**Spatial Extension:** PostGIS 3.4 (`django.contrib.gis.db.backends.postgis`)  
**Default Coordinate Reference System:** WGS84 (EPSG:4326)  

---

## 1. Core Transport Graph Models (`apps.transport_graph`)

### 1.1 `TransportNode`
Represents logistics hubs, checkposts, river ports, and rail junctions.
- `id` (UUID, Primary Key)
- `name` (CharField, max 255)
- `short_code` (CharField, max 20, unique)
- `node_type` (CharField, choices: `LOGISTICS_HUB`, `CHECKPOST`, `MULTIMODAL_HUB`, `DEPOT`, `RIVER_PORT`, `RAIL_YARD`)
- `location` (PointField, srid=4326, spatial_index=True)
- `elevation_m` (FloatField, null=True)
- `state` (CharField, max 50)
- `district` (CharField, max 100)
- `is_active` (BooleanField, default=True)

### 1.2 `TransportEdge`
Represents physical road, rail, and waterway transit segments connecting nodes.
- `id` (UUID, Primary Key)
- `source_node` (ForeignKey -> TransportNode, on_delete=CASCADE)
- `target_node` (ForeignKey -> TransportNode, on_delete=CASCADE)
- `mode` (CharField, choices: `ROAD`, `RAIL`, `WATERWAY`, `TRANSFER`)
- `status` (CharField, choices: `OPERATIONAL`, `CAUTION`, `CRITICAL`, `BLOCKED`)
- `distance_m` (FloatField)
- `base_transit_time_min` (FloatField)
- `cost_inr` (DecimalField, max_digits=10, decimal_places=2)
- `hazard_score` (FloatField, default=0.0)
- `geometry` (LineStringField, srid=4326, spatial_index=True)
- `capacity_kg` (FloatField, default=25000.0)
- `max_draft_m` (FloatField, default=0.0)
- `is_traversable` (BooleanField, default=True)

---

## 2. Geohazard Intelligence Models (`apps.hazards`)

### 2.1 `HazardScore`
Point-in-time composite hazard evaluation for transport edges.
- `id` (UUID, Primary Key)
- `edge` (ForeignKey -> TransportEdge, on_delete=CASCADE)
- `hazard_index` (FloatField, range 0.0 - 1.0)
- `severity` (CharField, choices: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `confidence` (FloatField, default=0.85)
- `contributing_factors` (JSONField, default=dict)
- `model_version` (CharField, max 50)
- `valid_until` (DateTimeField)
- `is_stale` (BooleanField, default=False)

### 2.2 `HazardIncident`
Active or historical physical disruption events (landslides, washouts).
- `id` (UUID, Primary Key)
- `edge` (ForeignKey -> TransportEdge, null=True)
- `incident_type` (CharField, choices: `LANDSLIDE`, `FLASH_FLOOD`, `BRIDGE_OUTAGE`, `ROAD_CRACK`)
- `source` (CharField, choices: `IMD_TELEMETRY`, `SATELLITE_INSAR`, `FIELD_REPORT`, `SYNTHETIC_DEMO`)
- `severity` (CharField)
- `reported_at` (DateTimeField)
- `is_resolved` (BooleanField, default=False)

---

## 3. Fleet & Load Optimization Models (`apps.fleet`, `apps.vehicles`)

### 3.1 `Vehicle`
Fleet assets positioned across regional depots.
- `id` (UUID, Primary Key)
- `registration_number` (CharField, max 30, unique)
- `vehicle_type` (CharField, choices: `TRUCK_LIGHT`, `TRUCK_MEDIUM`, `TRUCK_HEAVY`, `INLAND_BARGE`)
- `status` (CharField, choices: `AVAILABLE`, `ASSIGNED`, `ON_TRIP`, `MAINTENANCE`)
- `payload_capacity_kg` (FloatField)
- `volume_capacity_cbm` (FloatField)
- `fuel_rate_per_km` (FloatField, default=32.0)
- `current_depot` (ForeignKey -> TransportNode, null=True)
- `is_active` (BooleanField, default=True)

### 3.2 `FreightLoad`
Freight demands submitted by shippers or logistics operators.
- `id` (UUID, Primary Key)
- `cargo_type` (CharField, choices: `GENERAL`, `PERISHABLE`, `HAZARDOUS`, `EMERGENCY_RELIEF`)
- `weight_kg` (FloatField)
- `volume_cbm` (FloatField)
- `origin_node` (ForeignKey -> TransportNode)
- `destination_node` (ForeignKey -> TransportNode)
- `status` (CharField, choices: `CREATED`, `AVAILABLE`, `CONSOLIDATED`, `ASSIGNED`, `DELIVERED`)
- `priority` (CharField, choices: `STANDARD`, `EXPEDITED`, `DISASTER_CRITICAL`)

### 3.3 `OptimizationRun`
Audit record of multi-depot fleet dispatch executions.
- `id` (UUID, Primary Key)
- `executed_at` (DateTimeField, auto_now_add=True)
- `total_loads` (IntegerField)
- `assigned_loads` (IntegerField)
- `vehicles_used` (IntegerField)
- `total_cost_inr` (DecimalField)
- `is_simulation` (BooleanField, default=False)

---

## 4. Routing & Trip Execution Models (`apps.routing`, `apps.trips`)

### 4.1 `Route`
Calculated multimodal path traversing the transport graph.
- `id` (UUID, Primary Key)
- `origin_node` (ForeignKey -> TransportNode)
- `destination_node` (ForeignKey -> TransportNode)
- `route_type` (CharField, choices: `FASTEST`, `SAFEST`, `CHEAPEST`, `MULTIMODAL`, `BALANCED`)
- `total_distance_m` (FloatField)
- `total_time_min` (FloatField)
- `total_cost_inr` (DecimalField)
- `hazard_penalty_score` (FloatField)
- `transfer_count` (IntegerField, default=0)
- `route_geometry` (LineStringField, srid=4326, null=True)
- `explanation_text` (TextField)

### 4.2 `Trip`
Active transit execution assigned to a driver and vehicle.
- `id` (UUID, Primary Key)
- `route` (ForeignKey -> Route)
- `vehicle` (ForeignKey -> Vehicle)
- `driver` (ForeignKey -> User)
- `status` (CharField, choices: `PLANNED`, `ACTIVE`, `DIVERTED`, `COMPLETED`, `CANCELLED`)
- `start_time` (DateTimeField, null=True)
- `end_time` (DateTimeField, null=True)

---

## 5. Offline-First Synchronization Models (`apps.sync`)

### 5.1 `OfflineGraphBundle`
Cryptographic network snapshot distributed to mobile driver clients.
- `id` (UUID, Primary Key)
- `version_tag` (CharField, max 50, unique)
- `region` (CharField, default="NER_PRIMARY")
- `checksum_sha256` (CharField, max 64)
- `node_count` (IntegerField)
- `edge_count` (IntegerField)
- `payload` (JSONField)
- `is_active` (BooleanField, default=True)

### 5.2 `SyncQueueRecord`
Individual transaction ledger for offline event synchronization.
- `id` (UUID, Primary Key)
- `idempotency_key` (UUIDField, unique=True, db_index=True)
- `event_type` (CharField, choices: `TRIP_STATUS`, `GPS_BREADCRUMB`, `DELAY_ALERT`, `SOS`)
- `client_timestamp` (DateTimeField)
- `server_received_at` (DateTimeField, auto_now_add=True)
- `status` (CharField, choices: `APPLIED`, `DUPLICATE`, `CONFLICT`, `REJECTED`)
- `payload` (JSONField)

---

## 6. Disruption Sandbox & Intelligence Models (`apps.incidents`, `apps.analytics`)

### 6.1 `DisruptionSimulationRun`
Isolated simulation run evaluating regional resilience.
- `id` (UUID, Primary Key)
- `scenario_name` (CharField, max 255)
- `scenario_type` (CharField, choices: `HEAVY_RAINFALL`, `LANDSLIDE_CLUSTER`, `BRIDGE_COLLAPSE`)
- `affected_edges_count` (IntegerField)
- `pre_disruption_accessibility_score` (FloatField)
- `post_disruption_accessibility_score` (FloatField)
- `accessibility_delta_pct` (FloatField)
- `is_simulation` (BooleanField, default=True)

### 6.2 `DecisionRecommendation`
Explainable tactical AI intervention for command center operators.
- `id` (UUID, Primary Key)
- `title` (CharField, max 255)
- `decision_type` (CharField, choices: `REROUTE`, `CONSOLIDATE`, `MODAL_SHIFT`, `DISASTER_EXPEDITE`)
- `confidence` (FloatField)
- `primary_factors` (JSONField)
- `is_dismissed` (BooleanField, default=False)
