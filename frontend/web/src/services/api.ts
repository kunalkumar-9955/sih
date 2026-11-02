/**
 * SIH26002 — Web Frontend API Client
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  preferred_language: string;
  is_verified: boolean;
}

export interface TransportNode {
  id: string;
  name: string;
  short_code: string;
  node_type: string;
  node_type_display: string;
  coordinates: { longitude: number; latitude: number } | null;
  elevation_m: number | null;
  state: string;
  district: string;
  is_active: boolean;
}

export interface TransportEdge {
  id: string;
  source_node: string;
  source_node_name: string;
  target_node: string;
  target_node_name: string;
  mode: string;
  mode_display: string;
  status: string;
  status_display: string;
  distance_m: number;
  base_transit_time_min: number;
  cost_inr: string | number;
  hazard_score: number;
  is_available: boolean;
  is_traversable: boolean;
  road_name: string;
  geometry_coordinates: [number, number][];
}

export interface RouteSegment {
  sequence?: number;
  edge_id: string;
  source_id?: string;
  source_name?: string;
  source_node?: string;
  target_id?: string;
  target_name?: string;
  target_node?: string;
  mode: string;
  distance_m: number;
  transit_time_min: number;
  cost_inr: number;
  hazard_score: number;
  road_name: string;
  status: string;
  transfer_time_min?: number;
  transfer_cost_inr?: number;
}

export interface RouteOption {
  id: string;
  route_id?: string;
  origin_node: string;
  origin_node_name: string;
  destination_node: string;
  destination_node_name: string;
  route_type: "SAFEST" | "FASTEST" | "CHEAPEST" | "MULTIMODAL";
  routing_policy?: string;
  route_type_display: string;
  total_distance_m: number;
  total_distance?: number;
  total_time_min: number;
  total_time?: number;
  total_cost_inr: number;
  total_cost?: number;
  hazard_penalty_score: number;
  risk_score?: number;
  modes_used?: string[];
  transfer_count?: number;
  explanation?: string;
  geometry_coordinates: [number, number][];
  segments: RouteSegment[];
  alpha_used: number;
  is_current: boolean;
}

export interface Trip {
  id: string;
  driver_name: string | null;
  vehicle_registration: string | null;
  origin_name: string;
  destination_name: string;
  status: "PLANNED" | "ACTIVE" | "PAUSED" | "COMPLETED" | "CANCELLED";
  status_display: string;
  planned_departure: string | null;
  actual_departure: string | null;
  actual_arrival: string | null;
  cargo_description: string;
  cargo_weight_kg: number;
  route_version?: number;
  route_assigned_at?: string | null;
  route_hazard_snapshot_at?: string | null;
  current_location_coords: { longitude: number; latitude: number } | null;
  created_at: string;
}

export interface RerouteEvent {
  id: string;
  trip: string;
  old_route: string | null;
  old_route_summary: {
    id: string;
    route_type: string;
    total_time_min: number;
    total_distance_km: number;
    max_hazard_score: number;
    safety_level: string;
  } | null;
  new_route: string | null;
  new_route_summary: {
    id: string;
    route_type: string;
    total_time_min: number;
    total_distance_km: number;
    max_hazard_score: number;
    safety_level: string;
  } | null;
  trigger_reason: string;
  triggering_edge_ids: string[];
  old_hazard_exposure: number;
  new_hazard_exposure: number;
  improvement_pct: number;
  trip_route_version: number;
  status: "PENDING" | "SENT" | "ACKNOWLEDGED" | "APPLIED" | "FAILED" | "DISMISSED";
  driver_acknowledged_at: string | null;
  notification_payload: {
    title: string;
    message: string;
    reason?: string;
    urgency: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
    is_mandatory: boolean;
    improvement_pct: number;
    metrics: {
      time_delta_min: number;
      distance_delta_km: number;
      old_time_min: number;
      new_time_min: number;
      old_distance_km: number;
      new_distance_km: number;
      old_max_hazard: number;
      new_max_hazard: number;
      new_policy?: string;
    };
    actions: { action: string; label: string; primary?: boolean }[];
  };
  created_at: string;
  updated_at: string;
}

export interface RouteRiskEvaluation {
  route_id: string;
  trip_id: string;
  trip_status: string;
  route_version: number;
  route_assigned_at: string | null;
  evaluated_at: string;
  edge_count: number;
  max_hazard_score: number;
  mean_hazard_score: number;
  risky_edge_count: number;
  critical_edge_count: number;
  blocked_edges: Array<{
    edge_id: string;
    source: string;
    target: string;
    status: string;
    hazard_score: number;
    reason: string;
  }>;
  safety_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  has_critical_or_blocked: boolean;
  edge_evaluations: Array<{
    edge_id: string;
    source: string;
    target: string;
    status: string;
    hazard_score: number;
    severity: string;
    is_blocked: boolean;
  }>;
}

class ApiService {
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("sih_access_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }
    return headers;
  }

  async login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || err.error?.message || "Invalid credentials");
    }
    return res.json();
  }

  async getMe(): Promise<{ data: User }> {
    const res = await fetch(`${API_BASE}/auth/me/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch user");
    return res.json();
  }

  // ── Driver-Scoped Operational APIs ───────────────────────────────────────
  async getDriverDashboard(): Promise<{ success: boolean; data: any }> {
    const res = await fetch(`${API_BASE}/driver/dashboard/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to load driver dashboard" }));
      throw new Error(err.detail || "Unable to fetch driver operational state.");
    }
    return res.json();
  }

  async getDriverTrip(): Promise<{ success: boolean; data: any }> {
    const res = await fetch(`${API_BASE}/driver/trip/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch driver trip");
    return res.json();
  }

  async getDriverShipments(): Promise<{ success: boolean; data: any[] }> {
    const res = await fetch(`${API_BASE}/driver/shipments/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch driver shipments");
    return res.json();
  }

  async getDriverAlerts(): Promise<{ success: boolean; data: any[] }> {
    const res = await fetch(`${API_BASE}/driver/alerts/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch driver alerts");
    return res.json();
  }

  async triggerDriverSOS(action: "TRIGGER" | "RESOLVE" = "TRIGGER", notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/driver/sos/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ action, notes: notes || "" }),
    });
    if (!res.ok) throw new Error("SOS beacon operation failed");
    return res.json();
  }

  async getNodes(): Promise<{ results: TransportNode[] }> {
    const res = await fetch(`${API_BASE}/transport/nodes/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch nodes");
    return res.json();
  }

  async getEdges(): Promise<{ results: TransportEdge[] }> {
    const res = await fetch(`${API_BASE}/transport/edges/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch edges");
    return res.json();
  }

  async getGraphDump(): Promise<{ nodes: TransportNode[]; edges: TransportEdge[] }> {
    const res = await fetch(`${API_BASE}/transport/graph/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load transport graph");
    return res.json();
  }

  async computeRoutes(
    originId: string,
    destinationId: string,
    routeTypes?: string[],
    options?: { cargoWeight?: number; allowMultimodal?: boolean }
  ): Promise<RouteOption[]> {
    const res = await fetch(`${API_BASE}/routes/plan/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        origin_node_id: originId,
        destination_node_id: destinationId,
        route_types: routeTypes || ["SAFEST", "FASTEST", "CHEAPEST", "MULTIMODAL"],
        cargo_weight: options?.cargoWeight,
        allow_multimodal: options?.allowMultimodal !== undefined ? options.allowMultimodal : true,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Route calculation failed" }));
      throw new Error(err.detail || err.error?.message || "Unable to compute route under requested constraints.");
    }
    const data = await res.json();
    return data.routes || data.data || data;
  }

  async getTrips(): Promise<{ results: Trip[] }> {
    const res = await fetch(`${API_BASE}/trips/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch trips");
    return res.json();
  }

  async getTripRouteRisk(tripId: string): Promise<RouteRiskEvaluation> {
    const res = await fetch(`${API_BASE}/trips/${tripId}/route-risk/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch route risk evaluation");
    return res.json();
  }

  async recalculateTripRoute(
    tripId: string,
    options?: { force?: boolean; auto_apply?: boolean }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/trips/${tripId}/recalculate-route/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        force: options?.force || false,
        auto_apply: options?.auto_apply || false,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Recalculation failed" }));
      throw new Error(err.detail || "Failed to recalculate route");
    }
    return res.json();
  }

  async getTripRerouteEvents(tripId: string): Promise<RerouteEvent[]> {
    const res = await fetch(`${API_BASE}/trips/${tripId}/reroute-events/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch reroute events");
    const data = await res.json();
    return data.results || data;
  }

  async acknowledgeRerouteEvent(
    tripId: string,
    eventId: string,
    action: "ACCEPT" | "DECLINE",
    notes?: string
  ): Promise<RerouteEvent> {
    const res = await fetch(`${API_BASE}/trips/${tripId}/reroute-events/${eventId}/acknowledge/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ action, notes: notes || "" }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Acknowledgement failed" }));
      throw new Error(err.detail || "Failed to acknowledge reroute event");
    }
    return res.json();
  }

  // ── Phase 5: Offline Sync & Graph Diagnostics ──────────────────────────────

  async getSyncDiagnostics(): Promise<SyncDiagnostics> {
    const res = await fetch(`${API_BASE}/sync/status/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch sync diagnostics");
    return res.json();
  }

  async getOfflineGraphVersion(region = "NER_CORRIDOR"): Promise<OfflineGraphVersion> {
    const res = await fetch(`${API_BASE}/sync/graph/version/?region=${region}`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch graph version");
    return res.json();
  }

  async getEmergencySosSignals(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/sync/sos/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch emergency SOS signals");
    return res.json();
  }

  // ── Phase 6: Ingestion, Scenarios & Accessibility Intelligence ─────────────

  async getDemoScenarios(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/ingestion/scenarios/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch demo scenarios");
    return res.json();
  }

  async activateDemoScenario(scenarioName: string): Promise<any> {
    const res = await fetch(`${API_BASE}/ingestion/scenarios/activate/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ scenario_name: scenarioName }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Failed to activate scenario" }));
      throw new Error(err.error || "Failed to activate scenario");
    }
    return res.json();
  }

  async resetDemoScenario(): Promise<any> {
    const res = await fetch(`${API_BASE}/ingestion/scenarios/reset/`, {
      method: "POST",
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to reset scenario");
    return res.json();
  }

  async getIngestionFreshness(): Promise<any> {
    const res = await fetch(`${API_BASE}/ingestion/freshness/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch freshness report");
    return res.json();
  }

  async getCorridorAccessibility(region = "NER_CORRIDOR"): Promise<any> {
    const res = await fetch(`${API_BASE}/transport/accessibility/?region=${region}`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch accessibility score");
    return res.json();
  }

  async getDetailedHealth(): Promise<any> {
    const res = await fetch(`${API_BASE}/health/detailed/`);
    if (!res.ok) throw new Error("Failed to fetch detailed system health");
    return res.json();
  }

  // ── Phase 7: Fleet Intelligence & Load Matching ───────────────────────────
  async getFleetOverview(): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/overview/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch fleet overview");
    return res.json();
  }

  async getFleetVehicles(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/fleet/vehicles/availability/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch vehicle availability");
    return res.json();
  }

  async getFreightLoads(statusFilter?: string, priorityFilter?: string): Promise<any[]> {
    let url = `${API_BASE}/fleet/loads/`;
    const params = new URLSearchParams();
    if (statusFilter) params.append("status", statusFilter);
    if (priorityFilter) params.append("priority", priorityFilter);
    if (params.toString()) url += `?${params.toString()}`;

    const res = await fetch(url, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch freight loads");
    return res.json();
  }

  async createFreightLoad(data: any): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/loads/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to create freight load");
    return res.json();
  }

  async getLoadCandidates(loadId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/loads/${loadId}/candidates/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch matching candidates");
    return res.json();
  }

  async matchLoadToVehicle(loadId: string, vehicleId: string, isManualOverride = false, overrideReason = ""): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/loads/${loadId}/match/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        vehicle_id: vehicleId,
        is_manual_override: isManualOverride,
        override_reason: overrideReason,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Match failed" }));
      throw new Error(err.error || err.reason || "Failed to execute load matching");
    }
    return res.json();
  }

  async getFleetEmergencies(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/fleet/emergencies/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch active emergencies");
    return res.json();
  }

  async actOnEmergency(sosId: string, action: string, notes = ""): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/emergencies/${sosId}/action/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ action, notes }),
    });
    if (!res.ok) throw new Error(`Failed to execute emergency action: ${action}`);
    return res.json();
  }

  async activateDisasterMode(affectedCorridors?: string[], notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/disaster-mode/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ affected_corridors: affectedCorridors, notes }),
    });
    if (!res.ok) throw new Error("Failed to activate disaster mode");
    return res.json();
  }

  async resetDisasterMode(): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/disaster-mode/reset/`, {
      method: "POST",
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to reset disaster mode");
    return res.json();
  }

  async getLoadConsolidations(): Promise<any> {
    const res = await fetch(`${API_BASE}/fleet/consolidations/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch load consolidations");
    return res.json();
  }

  // --- PHASE 9 INTELLIGENCE & OPTIMIZATION APIS ---

  async getOperationalSummary(): Promise<any> {
    const res = await fetch(`${API_BASE}/intelligence/network/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch operational summary");
    return res.json();
  }

  async getCorridorsHealth(): Promise<any> {
    const res = await fetch(`${API_BASE}/intelligence/corridors/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch corridors health");
    return res.json();
  }

  async getAIRecommendations(): Promise<any> {
    const res = await fetch(`${API_BASE}/intelligence/recommendations/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch AI recommendations");
    return res.json();
  }

  async predictETA(params: { route_id?: string; origin_node_id?: string; destination_node_id?: string; weather_rainfall_mm?: number }): Promise<any> {
    const res = await fetch(`${API_BASE}/intelligence/eta/predict/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error("Failed to predict ETA");
    return res.json();
  }

  async getAccessibilityIntelligence(state?: string): Promise<any> {
    const url = state ? `${API_BASE}/intelligence/accessibility/?state=${encodeURIComponent(state)}` : `${API_BASE}/intelligence/accessibility/`;
    const res = await fetch(url, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch accessibility intelligence");
    return res.json();
  }

  async runFleetOptimization(params: { depot_ids?: string[]; load_ids?: string[]; vehicle_ids?: string[]; enable_consolidation?: boolean; is_simulation?: boolean }): Promise<any> {
    const res = await fetch(`${API_BASE}/optimization/fleet/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error("Failed to run fleet optimization");
    return res.json();
  }

  async getConsolidationRecommendations(): Promise<any> {
    const res = await fetch(`${API_BASE}/optimization/consolidation/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ is_simulation: true }),
    });
    if (!res.ok) throw new Error("Failed to get consolidation recommendations");
    return res.json();
  }

  async runDisruptionSimulation(params: { scenario_type: string; target_corridor?: string; custom_parameters?: any }): Promise<any> {
    const res = await fetch(`${API_BASE}/simulations/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error("Failed to execute disruption simulation");
    return res.json();
  }

  async compareDisruptionScenarios(scenarios: string[]): Promise<any> {
    const res = await fetch(`${API_BASE}/simulations/quick-evaluate/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ scenarios }),
    });
    if (!res.ok) throw new Error("Failed to compare disruption scenarios");
    return res.json();
  }

  async runDemoScenario(): Promise<any> {
    const res = await fetch(`${API_BASE}/intelligence/demo-scenario/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error("Failed to run demo scenario");
    return res.json();
  }

  async getDemoReadiness(): Promise<DemoReadinessResponse> {
    const res = await fetch(`${API_BASE}/demo/readiness/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch demo readiness");
    return res.json();
  }

  async executeDemoReset(confirmReset = true): Promise<DemoResetResponse> {
    const res = await fetch(`${API_BASE}/demo/reset/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        confirm_demo_reset: confirmReset,
        mode: "DEMO",
      }),
    });
    if (!res.ok) throw new Error("Failed to execute demo reset");
    return res.json();
  }

  async runPhase10Demo(seed = 42): Promise<DemoOrchestrationResponse> {
    const res = await fetch(`${API_BASE}/demo/orchestrate/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ seed }),
    });
    if (!res.ok) throw new Error("Failed to run Phase 10 demo orchestration");
    return res.json();
  }

  async getGeneralizationReport(): Promise<GeneralizationReportResponse> {
    const res = await fetch(`${API_BASE}/demo/generalization-report/`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch generalization report");
    return res.json();
  }
}

export interface DemoReadinessResponse {
  status: "READY" | "NOT_READY";
  environment: string;
  timestamp: string;
  checks: Record<string, "PASS" | "FAIL">;
  details: Record<string, any>;
}

export interface DemoResetResponse {
  success: boolean;
  message: string;
  mode: string;
  cleaned: Record<string, number>;
  demo_baseline_active: boolean;
}

export interface DemoOrchestrationResponse {
  success: boolean;
  status: string;
  steps_completed: number;
  total_steps: number;
  scenario: string;
  audit_trail: Array<{
    step: number;
    title: string;
    status: string;
    details?: any;
    timestamp: string;
  }>;
}

export interface GeneralizationReportResponse {
  evaluation_mode: string;
  notice: string;
  models_evaluated: string[];
  scenarios: Record<string, any>;
}


export interface SyncDiagnostics {
  total_records: number;
  applied_count: number;
  conflict_count: number;
  duplicate_count: number;
  rejected_count: number;
  active_sos_count: number;
  active_graph_bundle: {
    version_tag: string;
    region: string;
    node_count: number;
    edge_count: number;
    checksum_sha256: string;
  } | null;
  server_time: string;
}

export interface OfflineGraphVersion {
  id: string;
  version_tag: string;
  region: string;
  checksum_sha256: string;
  node_count: number;
  edge_count: number;
  is_active: boolean;
  created_at: string;
}

export const api = new ApiService();

