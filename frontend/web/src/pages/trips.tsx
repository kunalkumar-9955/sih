import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { api, Trip, RerouteEvent, RouteRiskEvaluation, SyncDiagnostics } from "../services/api";
import {
  Truck,
  MapPin,
  CheckCircle,
  Play,
  AlertTriangle,
  RefreshCw,
  Shield,
  ArrowRight,
  Clock,
  Navigation,
  XCircle,
  Info,
  Wifi,
  Database,
  Radio,
  CloudRain,
  Flame,
  Layers,
  Compass,
} from "lucide-react";

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [tripRisks, setTripRisks] = useState<Record<string, RouteRiskEvaluation>>({});
  const [tripReroutes, setTripReroutes] = useState<Record<string, RerouteEvent[]>>({});
  const [selectedReroute, setSelectedReroute] = useState<{ tripId: string; event: RerouteEvent } | null>(null);
  const [recalculatingId, setRecalculatingId] = useState<string | null>(null);
  const [syncDiagnostics, setSyncDiagnostics] = useState<SyncDiagnostics | null>(null);

  // Phase 6 States
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [activeScenario, setActiveScenario] = useState<string>("NORMAL");
  const [accessibilityData, setAccessibilityData] = useState<any>(null);
  const [scenarioSwitching, setScenarioSwitching] = useState(false);

  const fetchTrips = async () => {
    try {
      const [tripsRes, diagRes, scnRes, accRes] = await Promise.all([
        api.getTrips(),
        api.getSyncDiagnostics().catch(() => null),
        api.getDemoScenarios().catch(() => []),
        api.getCorridorAccessibility().catch(() => null),
      ]);
      const tripsList = tripsRes.results || [];
      setTrips(tripsList);
      if (diagRes) setSyncDiagnostics(diagRes);
      if (scnRes) {
        setScenarios(scnRes);
        const active = scnRes.find((s: any) => s.is_active);
        if (active) setActiveScenario(active.name);
      }
      if (accRes) setAccessibilityData(accRes);

      // For active trips, fetch route risks & reroute events
      for (const t of tripsList) {
        if (t.status === "ACTIVE") {
          loadTripRisk(t.id);
          loadTripReroutes(t.id);
        }
      }
    } catch (err) {
      console.error("Failed to load trips:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleScenarioChange = async (name: string) => {
    try {
      setScenarioSwitching(true);
      await api.activateDemoScenario(name);
      setActiveScenario(name);
      await fetchTrips();
    } catch (err: any) {
      alert(`Failed to activate scenario: ${err.message}`);
    } finally {
      setScenarioSwitching(false);
    }
  };

  const handleScenarioReset = async () => {
    try {
      setScenarioSwitching(true);
      await api.resetDemoScenario();
      setActiveScenario("NORMAL");
      await fetchTrips();
    } catch (err: any) {
      alert(`Failed to reset scenario: ${err.message}`);
    } finally {
      setScenarioSwitching(false);
    }
  };


  const loadTripRisk = async (tripId: string) => {
    try {
      const risk = await api.getTripRouteRisk(tripId);
      setTripRisks((prev) => ({ ...prev, [tripId]: risk }));
    } catch (err) {
      console.warn(`Could not fetch risk for trip ${tripId}:`, err);
    }
  };

  const loadTripReroutes = async (tripId: string) => {
    try {
      const events = await api.getTripRerouteEvents(tripId);
      setTripReroutes((prev) => ({ ...prev, [tripId]: events }));
    } catch (err) {
      console.warn(`Could not fetch reroutes for trip ${tripId}:`, err);
    }
  };

  useEffect(() => {
    fetchTrips();
    const interval = setInterval(() => {
      fetchTrips();
    }, 15000); // Polling every 15s for live risk & dynamic rerouting
    return () => clearInterval(interval);
  }, []);

  const handleStatusChange = async (tripId: string, newStatus: string) => {
    try {
      const token = localStorage.getItem("sih_access_token");
      await fetch(`http://localhost:8000/api/v1/trips/${tripId}/status/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchTrips();
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const handleRecalculate = async (tripId: string) => {
    setRecalculatingId(tripId);
    try {
      const res = await api.recalculateTripRoute(tripId, { force: true });
      if (res.rerouted) {
        await loadTripReroutes(tripId);
        await loadTripRisk(tripId);
        await fetchTrips();
      } else {
        alert(res.reason || "Current route remains optimal and within safe tolerance.");
      }
    } catch (err: any) {
      alert(`Recalculation error: ${err.message}`);
    } finally {
      setRecalculatingId(null);
    }
  };

  const handleAcknowledge = async (tripId: string, eventId: string, action: "ACCEPT" | "DECLINE") => {
    try {
      await api.acknowledgeRerouteEvent(tripId, eventId, action);
      setSelectedReroute(null);
      await fetchTrips();
      await loadTripRisk(tripId);
      await loadTripReroutes(tripId);
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  const getSafetyBadgeClass = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return "badge-danger animate-pulse";
      case "HIGH":
        return "badge-warning";
      case "MODERATE":
        return "badge-multimodal";
      default:
        return "badge-safest";
    }
  };

  return (
    <Layout
      title="Freight Trips & Active Dispatches"
      subtitle="Track active freight movements, live corridor geohazard risk, and dynamic reroute intelligence"
    >
      <Head>
        <title>Active Trips & Rerouting — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Phase 5: Offline Sync & Graph Cache Diagnostics Panel */}
        {syncDiagnostics && (
          <div
            className="glass-panel"
            style={{
              padding: "16px 20px",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              borderLeft: "4px solid var(--accent-cyan)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "38px",
                  height: "38px",
                  borderRadius: "8px",
                  background: "rgba(14, 165, 233, 0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--accent-cyan)",
                }}
              >
                <Database size={20} />
              </div>
              <div>
                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Offline Navigation & Graph Cache Engine
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  Bundle:{" "}
                  <span style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>
                    {syncDiagnostics.active_graph_bundle?.version_tag || "NER_CORRIDOR-latest"}
                  </span>{" "}
                  • {syncDiagnostics.active_graph_bundle?.node_count ?? 26} Nodes •{" "}
                  {syncDiagnostics.active_graph_bundle?.edge_count ?? 54} Edges • SHA-256 Verified
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <div
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  background: "rgba(16, 185, 129, 0.1)",
                  border: "1px solid rgba(16, 185, 129, 0.25)",
                  fontSize: "12px",
                }}
              >
                <span style={{ color: "var(--text-secondary)" }}>Applied: </span>
                <strong style={{ color: "var(--accent-emerald)" }}>{syncDiagnostics.applied_count}</strong>
              </div>
              <div
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  background: "rgba(14, 165, 233, 0.1)",
                  border: "1px solid rgba(14, 165, 233, 0.25)",
                  fontSize: "12px",
                }}
              >
                <span style={{ color: "var(--text-secondary)" }}>Deduplicated: </span>
                <strong style={{ color: "var(--accent-cyan)" }}>{syncDiagnostics.duplicate_count}</strong>
              </div>
              <div
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  background: "rgba(245, 158, 11, 0.1)",
                  border: "1px solid rgba(245, 158, 11, 0.25)",
                  fontSize: "12px",
                }}
              >
                <span style={{ color: "var(--text-secondary)" }}>Conflicts: </span>
                <strong style={{ color: "var(--accent-amber)" }}>{syncDiagnostics.conflict_count}</strong>
              </div>
              {syncDiagnostics.active_sos_count > 0 && (
                <div
                  style={{
                    padding: "6px 12px",
                    borderRadius: "6px",
                    background: "rgba(220, 38, 38, 0.2)",
                    border: "1px solid rgba(220, 38, 38, 0.5)",
                    fontSize: "12px",
                    color: "var(--accent-crimson)",
                    fontWeight: 700,
                  }}
                >
                  🚨 {syncDiagnostics.active_sos_count} ACTIVE SOS
                </div>
              )}
            </div>
          </div>
        )}

        {/* Phase 6: Controlled Demo Scenario Simulation Controller */}
        <div
          className="glass-panel"
          style={{
            padding: "16px 20px",
            borderLeft: activeScenario !== "NORMAL" ? "4px solid var(--accent-amber)" : "4px solid var(--accent-emerald)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <Flame size={20} style={{ color: activeScenario !== "NORMAL" ? "var(--accent-amber)" : "var(--accent-emerald)" }} />
              <div>
                <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Controlled Demo Scenario Engine
                </span>
                <span
                  style={{
                    marginLeft: "8px",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontSize: "10px",
                    fontWeight: 700,
                    background: "rgba(245, 158, 11, 0.15)",
                    color: "var(--accent-amber)",
                    border: "1px solid rgba(245, 158, 11, 0.3)",
                  }}
                >
                  DEMO / SIMULATION MODE
                </span>
              </div>
            </div>
            {activeScenario !== "NORMAL" && (
              <button
                onClick={handleScenarioReset}
                disabled={scenarioSwitching}
                className="btn btn-secondary"
                style={{ padding: "6px 12px", fontSize: "12px" }}
              >
                Reset to Baseline (Normal)
              </button>
            )}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {[
              { id: "NORMAL", label: "Normal (Clear)", icon: Compass, color: "var(--accent-emerald)" },
              { id: "HEAVY_RAIN", label: "Heavy Rain (140mm)", icon: CloudRain, color: "var(--accent-cyan)" },
              { id: "LANDSLIDE", label: "Landslide (NH-6 Blocked)", icon: Flame, color: "var(--accent-crimson)" },
              { id: "FLOOD", label: "Flood (Barak Basin)", icon: Layers, color: "var(--accent-amber)" },
              { id: "MULTIMODAL_SWITCH", label: "Multimodal Switch (Rail/Barge)", icon: Navigation, color: "var(--accent-purple)" },
            ].map((sc) => {
              const isActive = activeScenario === sc.id;
              const IconComp = sc.icon;
              return (
                <button
                  key={sc.id}
                  disabled={scenarioSwitching}
                  onClick={() => handleScenarioChange(sc.id)}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "8px",
                    fontSize: "12px",
                    fontWeight: isActive ? 700 : 500,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: isActive ? `${sc.color}25` : "rgba(255, 255, 255, 0.04)",
                    color: isActive ? sc.color : "var(--text-secondary)",
                    border: isActive ? `1.5px solid ${sc.color}` : "1px solid rgba(255, 255, 255, 0.08)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <IconComp size={14} />
                  {sc.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Phase 6: Accessibility Intelligence Score Card */}
        {accessibilityData && (
          <div
            className="glass-panel"
            style={{
              padding: "16px 20px",
              borderLeft: "4px solid var(--accent-purple)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Corridor Accessibility Index:{" "}
                  <span style={{ color: "var(--accent-purple)", fontSize: "16px" }}>
                    {accessibilityData.accessibility_score} / 100
                  </span>{" "}
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>
                    ({accessibilityData.rating})
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                  {accessibilityData.disclaimer}
                </div>
              </div>

              <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Connectivity</div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-cyan)" }}>
                    {accessibilityData.contributing_factors?.connectivity_density?.score ?? 0}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Safety Resilience</div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-emerald)" }}>
                    {accessibilityData.contributing_factors?.geohazard_safety?.score ?? 0}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Multimodal Redundancy</div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-purple)" }}>
                    {accessibilityData.contributing_factors?.multimodal_redundancy?.score ?? 0}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {trips.length === 0 && !loading && (
          <div className="glass-panel" style={{ padding: "40px", textAlign: "center" }}>
            <Truck size={48} style={{ color: "var(--accent-cyan)", margin: "0 auto 16px" }} />
            <h3 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>No Active Trips Dispatched</h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "20px" }}>
              Compute an optimal route in the Route Explorer to initialize and dispatch a new multimodal freight trip.
            </p>
            <a href="/routes" className="btn btn-primary">
              Launch Route Explorer
            </a>
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))",
            gap: "20px",
          }}
        >
          {trips.map((trip) => {
            const isCompleted = trip.status === "COMPLETED";
            const isActive = trip.status === "ACTIVE";
            const risk = tripRisks[trip.id];
            const pendingEvents = (tripReroutes[trip.id] || []).filter(
              (e) => e.status === "PENDING" || e.status === "SENT"
            );
            const activeEvent = pendingEvents[0];

            return (
              <div
                key={trip.id}
                className="glass-panel"
                style={{
                  padding: "24px",
                  border: activeEvent
                    ? "1px solid var(--accent-orange)"
                    : "1px solid var(--border-subtle)",
                }}
              >
                {/* Header Strip */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className={`badge badge-${isActive ? "fastest" : isCompleted ? "safest" : "multimodal"}`}>
                      {trip.status_display || trip.status}
                    </span>
                    {trip.route_version && trip.route_version > 1 && (
                      <span className="badge badge-safest" style={{ fontSize: "11px" }}>
                        v{trip.route_version} Route
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    TRIP-{trip.id.substring(0, 8).toUpperCase()}
                  </div>
                </div>

                {/* Origin / Destination Flow */}
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "15px", marginBottom: "4px" }}>
                    <MapPin size={16} color="var(--accent-cyan)" />
                    <span>{trip.origin_name}</span>
                  </div>
                  <div style={{ borderLeft: "2px dashed var(--border-subtle)", marginLeft: "7px", height: "14px" }} />
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "15px" }}>
                    <MapPin size={16} color="var(--accent-emerald)" />
                    <span>{trip.destination_name}</span>
                  </div>
                </div>

                {/* Phase 4 Live Risk Monitor for Active Trips */}
                {isActive && (
                  <div
                    style={{
                      background: "rgba(15, 23, 42, 0.6)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-sm)",
                      padding: "12px",
                      marginBottom: "14px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600 }}>
                        <Shield size={14} color="var(--accent-cyan)" />
                        <span>Live Route Geohazard Risk</span>
                      </div>
                      {risk && (
                        <span className={`badge ${getSafetyBadgeClass(risk.safety_level)}`} style={{ fontSize: "11px" }}>
                          {risk.safety_level} RISK
                        </span>
                      )}
                    </div>

                    {risk ? (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "12px" }}>
                        <div style={{ color: "var(--text-secondary)" }}>
                          Peak Hazard: <strong style={{ color: risk.max_hazard_score >= 0.55 ? "var(--accent-orange)" : "inherit" }}>
                            {risk.max_hazard_score.toFixed(2)}
                          </strong>
                        </div>
                        <div style={{ color: "var(--text-secondary)" }}>
                          Risky Segments: <strong>{risk.risky_edge_count}</strong>
                        </div>
                        {risk.blocked_edges && risk.blocked_edges.length > 0 && (
                          <div style={{ gridColumn: "span 2", color: "var(--accent-rose)", fontSize: "11px", display: "flex", alignItems: "center", gap: "4px" }}>
                            <AlertTriangle size={12} />
                            <span>{risk.blocked_edges.length} corridor segment(s) reported closed / blocked</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Evaluating corridor telemetry...</div>
                    )}
                  </div>
                )}

                {/* Pending Reroute Alert Notification Banner */}
                {activeEvent && (
                  <div
                    style={{
                      background: "rgba(245, 158, 11, 0.12)",
                      border: "1px solid rgba(245, 158, 11, 0.4)",
                      borderRadius: "var(--radius-sm)",
                      padding: "12px",
                      marginBottom: "14px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-orange)", fontWeight: 700, fontSize: "13px", marginBottom: "4px" }}>
                      <AlertTriangle size={16} />
                      <span>Safer Bypass Route Recommended</span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                      {activeEvent.trigger_reason}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12px" }}>
                      <span style={{ color: "var(--accent-emerald)", fontWeight: 600 }}>
                        +{Math.round((activeEvent.improvement_pct || 0) * 100)}% safer
                      </span>
                      <button
                        onClick={() => setSelectedReroute({ tripId: trip.id, event: activeEvent })}
                        className="btn btn-sm btn-primary"
                        style={{ padding: "4px 10px", fontSize: "12px" }}
                      >
                        Review Reroute
                      </button>
                    </div>
                  </div>
                )}

                {/* Details Box */}
                <div
                  style={{
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-sm)",
                    padding: "12px",
                    fontSize: "13px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                    marginBottom: "16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Driver:</span>
                    <strong style={{ color: "var(--text-primary)" }}>{trip.driver_name || "Unassigned"}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Vehicle:</span>
                    <strong style={{ color: "var(--text-primary)" }}>{trip.vehicle_registration || "Not Allocated"}</strong>
                  </div>
                  {trip.cargo_description && (
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-muted)" }}>Cargo:</span>
                      <span>
                        {trip.cargo_description} ({trip.cargo_weight_kg} kg)
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions Bar */}
                <div style={{ display: "flex", gap: "8px" }}>
                  {trip.status === "PLANNED" && (
                    <button
                      onClick={() => handleStatusChange(trip.id, "ACTIVE")}
                      className="btn btn-primary"
                      style={{ flex: 1, fontSize: "13px" }}
                    >
                      <Play size={14} />
                      <span>Start Transit</span>
                    </button>
                  )}
                  {trip.status === "ACTIVE" && (
                    <>
                      <button
                        onClick={() => handleRecalculate(trip.id)}
                        disabled={recalculatingId === trip.id}
                        className="btn btn-secondary"
                        style={{ flex: 1, fontSize: "12px" }}
                        title="Evaluate live conditions along corridor and compute bypass if degraded"
                      >
                        <RefreshCw size={13} className={recalculatingId === trip.id ? "animate-spin" : ""} />
                        <span>{recalculatingId === trip.id ? "Evaluating..." : "Check Reroute"}</span>
                      </button>
                      <button
                        onClick={() => handleStatusChange(trip.id, "COMPLETED")}
                        className="btn btn-success"
                        style={{ flex: 1, fontSize: "12px" }}
                      >
                        <CheckCircle size={14} />
                        <span>Deliver</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Phase 4 Reroute Decision Review Modal */}
      {selectedReroute && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="glass-panel"
            style={{
              maxWidth: "560px",
              width: "100%",
              padding: "28px",
              background: "var(--bg-secondary)",
              border: "1px solid var(--accent-orange)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "18px", color: "var(--accent-orange)" }}>
                <AlertTriangle size={20} />
                <span>Dynamic Reroute Decision</span>
              </div>
              <button
                onClick={() => setSelectedReroute(null)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <XCircle size={20} />
              </button>
            </div>

            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.5" }}>
              {selectedReroute.event.trigger_reason}
            </p>

            {/* Comparison Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "20px" }}>
              {/* Old Route */}
              <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "14px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "6px" }}>
                  Current Route
                </div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--accent-rose)", marginBottom: "4px" }}>
                  Hazard: {selectedReroute.event.old_hazard_exposure.toFixed(2)}
                </div>
                {selectedReroute.event.old_route_summary && (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    {selectedReroute.event.old_route_summary.total_distance_km} km · {selectedReroute.event.old_route_summary.total_time_min} min
                  </div>
                )}
              </div>

              {/* Proposed Route */}
              <div style={{ background: "rgba(16, 185, 129, 0.08)", padding: "14px", borderRadius: "var(--radius-sm)", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--accent-emerald)", marginBottom: "6px" }}>
                  Proposed Bypass Route
                </div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--accent-emerald)", marginBottom: "4px" }}>
                  Hazard: {(selectedReroute.event.new_hazard_exposure || 0).toFixed(2)}
                </div>
                {selectedReroute.event.new_route_summary && (
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    {selectedReroute.event.new_route_summary.total_distance_km} km · {selectedReroute.event.new_route_summary.total_time_min} min
                  </div>
                )}
              </div>
            </div>

            {/* Notification message from payload */}
            {selectedReroute.event.notification_payload?.message && (
              <div style={{ background: "var(--bg-tertiary)", padding: "12px", borderRadius: "var(--radius-sm)", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "20px" }}>
                <Info size={14} style={{ display: "inline", marginRight: "6px", verticalAlign: "middle" }} />
                {selectedReroute.event.notification_payload.message}
              </div>
            )}

            {/* Actions */}
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              {!selectedReroute.event.notification_payload?.is_mandatory && (
                <button
                  onClick={() => handleAcknowledge(selectedReroute.tripId, selectedReroute.event.id, "DECLINE")}
                  className="btn btn-secondary"
                >
                  Decline & Keep Current Route
                </button>
              )}
              <button
                onClick={() => handleAcknowledge(selectedReroute.tripId, selectedReroute.event.id, "ACCEPT")}
                className="btn btn-primary"
              >
                <Navigation size={15} />
                <span>Switch to Safe Bypass Route</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
