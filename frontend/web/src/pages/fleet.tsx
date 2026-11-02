import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { api } from "../services/api";
import {
  Truck,
  Package,
  AlertOctagon,
  Shield,
  Layers,
  ArrowRight,
  CheckCircle2,
  RefreshCw,
  Compass,
  Zap,
  Clock,
  MapPin,
  Sliders,
  DollarSign,
  AlertTriangle,
  Flame,
  Check,
} from "lucide-react";

export default function FleetManagementPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [loads, setLoads] = useState<any[]>([]);
  const [emergencies, setEmergencies] = useState<any[]>([]);
  const [consolidations, setConsolidations] = useState<any[]>([]);

  // Matching Drawer
  const [selectedLoad, setSelectedLoad] = useState<any | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [manualOverride, setManualOverride] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [assigningVehicleId, setAssigningVehicleId] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  // Disaster Mode Action
  const [disasterActionLoading, setDisasterActionLoading] = useState(false);

  const fetchFleetData = async () => {
    try {
      const [ovRes, vehRes, loadsRes, emRes, consRes] = await Promise.all([
        api.getFleetOverview().catch(() => null),
        api.getFleetVehicles().catch(() => []),
        api.getFreightLoads().catch(() => []),
        api.getFleetEmergencies().catch(() => []),
        api.getLoadConsolidations().catch(() => ({ opportunities: [] })),
      ]);
      if (ovRes) setOverview(ovRes);
      setVehicles(vehRes || []);
      setLoads(loadsRes || []);
      setEmergencies(emRes || []);
      setConsolidations(consRes?.opportunities || []);
    } catch (err) {
      console.error("Failed to load fleet intelligence:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFleetData();
    const interval = setInterval(fetchFleetData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenMatching = async (load: any) => {
    setSelectedLoad(load);
    setCandidates([]);
    setCandidatesLoading(true);
    setManualOverride(false);
    setOverrideReason("");
    setFeedbackMsg(null);
    try {
      const res = await api.getLoadCandidates(load.id);
      setCandidates(res.ranked_candidates || []);
    } catch (err: any) {
      setFeedbackMsg(`Error fetching candidates: ${err.message}`);
    } finally {
      setCandidatesLoading(false);
    }
  };

  const handleAssignVehicle = async (vehicleId: string) => {
    if (!selectedLoad) return;
    setAssigningVehicleId(vehicleId);
    setFeedbackMsg(null);
    try {
      const res = await api.matchLoadToVehicle(
        selectedLoad.id,
        vehicleId,
        manualOverride,
        overrideReason
      );
      setFeedbackMsg(`Match Successful: ${res.message}`);
      await fetchFleetData();
      setTimeout(() => setSelectedLoad(null), 1500);
    } catch (err: any) {
      setFeedbackMsg(`Match Error: ${err.message}`);
    } finally {
      setAssigningVehicleId(null);
    }
  };

  const handleEmergencyAction = async (sosId: string, action: string) => {
    try {
      await api.actOnEmergency(sosId, action, `Operator handled via dashboard: ${action}`);
      await fetchFleetData();
    } catch (err: any) {
      alert(`Emergency action failed: ${err.message}`);
    }
  };

  const handleToggleDisasterMode = async () => {
    setDisasterActionLoading(true);
    try {
      if (overview?.operational_mode?.is_disaster_mode) {
        await api.resetDisasterMode();
      } else {
        await api.activateDisasterMode(["NH-6_CORRIDOR", "NW-2_WATERWAY"], "Control Room Flood Warning Trigger");
      }
      await fetchFleetData();
    } catch (err: any) {
      alert(`Failed to update disaster mode: ${err.message}`);
    } finally {
      setDisasterActionLoading(false);
    }
  };

  const isDisaster = overview?.operational_mode?.is_disaster_mode;

  return (
    <Layout
      title="Fleet Intelligence & Load Matching"
      subtitle="Phase 7: Autonomous Multi-Factor Dispatching, Capacity Optimization & Emergency Operations"
    >
      <Head>
        <title>Fleet Intelligence & Load Matching — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      {/* DISASTER MODE PROMINENT CONTROL BANNER */}
      <div
        style={{
          background: isDisaster
            ? "linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(185, 28, 28, 0.35) 100%)"
            : "linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.15) 100%)",
          border: `1px solid ${isDisaster ? "#ef4444" : "rgba(16, 185, 129, 0.3)"}`,
          borderRadius: "var(--radius-md)",
          padding: "16px 24px",
          marginBottom: "28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: isDisaster ? "0 0 25px rgba(239, 68, 68, 0.25)" : "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              background: isDisaster ? "#ef4444" : "#10b981",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
            }}
          >
            {isDisaster ? <Flame size={24} /> : <Shield size={24} />}
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h3 style={{ fontSize: "17px", fontWeight: 700, margin: 0 }}>
                {isDisaster ? "DISASTER RESPONSE MODE ACTIVE" : "NORMAL OPERATIONS MODE"}
              </h3>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 800,
                  padding: "3px 8px",
                  borderRadius: "12px",
                  background: isDisaster ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.2)",
                  color: isDisaster ? "#fca5a5" : "#6ee7b7",
                }}
              >
                {isDisaster ? "PRIORITY OVERRIDE" : "STANDARD DISPATCH"}
              </span>
            </div>
            <p style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--text-secondary)" }}>
              {isDisaster
                ? "Emergency medical aid and relief shipments prioritized. Strict geohazard bypass enforced."
                : "Commercial and multimodal freight dispatch operating under balanced cost-safety heuristics."}
            </p>
          </div>
        </div>

        <button
          onClick={handleToggleDisasterMode}
          disabled={disasterActionLoading}
          style={{
            background: isDisaster ? "#334155" : "linear-gradient(135deg, #ef4444, #dc2626)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
          }}
        >
          {disasterActionLoading ? (
            <RefreshCw size={16} className="animate-spin" />
          ) : isDisaster ? (
            <CheckCircle2 size={16} />
          ) : (
            <AlertOctagon size={16} />
          )}
          {isDisaster ? "Restore Normal Operations" : "Activate Disaster Mode"}
        </button>
      </div>

      {/* KPI METRICS OVERVIEW */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        <div className="card" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>
              FLEET VEHICLES
            </span>
            <Truck size={18} color="#0ea5e9" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, marginTop: "8px" }}>
            {overview?.fleet?.total_vehicles ?? "--"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            <span style={{ color: "#10b981", fontWeight: 600 }}>{overview?.fleet?.available ?? 0} Available</span> •{" "}
            <span>{overview?.fleet?.on_trip ?? 0} On Trip</span>
          </div>
        </div>

        <div className="card" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>
              PENDING LOADS
            </span>
            <Package size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, marginTop: "8px" }}>
            {overview?.loads?.available ?? "--"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            <span style={{ color: "#38bdf8", fontWeight: 600 }}>{overview?.loads?.matched ?? 0} Matched</span> •{" "}
            <span>{overview?.loads?.in_transit ?? 0} In Transit</span>
          </div>
        </div>

        <div className="card" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>
              CRITICAL DEMANDS
            </span>
            <Zap size={18} color="#ef4444" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, marginTop: "8px" }}>
            {overview?.loads?.urgent_emergency ?? 0}
          </div>
          <div style={{ fontSize: "12px", color: "#f87171", marginTop: "4px", fontWeight: 600 }}>
            High / Urgent Priority
          </div>
        </div>

        <div className="card" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>
              ACTIVE DISTRESS (SOS)
            </span>
            <AlertTriangle size={18} color="#f97316" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, marginTop: "8px", color: emergencies.length > 0 ? "#f97316" : "var(--text-primary)" }}>
            {emergencies.filter(e => e.status !== "RESOLVED" && e.status !== "FALSE_ALARM").length}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            Rescue dispatch active
          </div>
        </div>
      </div>

      {/* SECTION 1: FREIGHT DEMANDS & AUTOMATED MATCHING */}
      <div className="card" style={{ padding: "24px", marginBottom: "28px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>Freight Demands & Automated Matching</h2>
            <p style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--text-secondary)" }}>
              Intelligently matches registered loads against available fleet capacity and route geohazard conditions.
            </p>
          </div>
          <button
            onClick={fetchFleetData}
            style={{
              background: "transparent",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
              padding: "8px 14px",
              borderRadius: "var(--radius-sm)",
              fontSize: "12px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {loads.length === 0 ? (
          <div style={{ textAlign: "center", padding: "32px", color: "var(--text-muted)" }}>
            No active freight loads recorded in the system.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-secondary)", textAlign: "left" }}>
                  <th style={{ padding: "12px 8px" }}>CARGO / LOAD</th>
                  <th style={{ padding: "12px 8px" }}>CORRIDOR</th>
                  <th style={{ padding: "12px 8px" }}>WEIGHT / VOL</th>
                  <th style={{ padding: "12px 8px" }}>PRIORITY</th>
                  <th style={{ padding: "12px 8px" }}>STATUS</th>
                  <th style={{ padding: "12px 8px" }}>ASSIGNED FLEET</th>
                  <th style={{ padding: "12px 8px", textAlign: "right" }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {loads.map((load) => (
                  <tr key={load.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                    <td style={{ padding: "14px 8px", fontWeight: 600 }}>
                      {load.title || `Load #${load.id.slice(0, 8)}`}
                      <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 400 }}>
                        {load.cargo_type} {load.is_perishable ? "• Perishable" : ""}
                      </div>
                    </td>
                    <td style={{ padding: "14px 8px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span>{load.origin_node_name || "Origin"}</span>
                        <ArrowRight size={12} color="var(--text-muted)" />
                        <span>{load.destination_node_name || "Destination"}</span>
                      </div>
                    </td>
                    <td style={{ padding: "14px 8px" }}>
                      {Number(load.weight_kg).toLocaleString()} kg
                      {load.volume_cbm ? ` (${load.volume_cbm} cbm)` : ""}
                    </td>
                    <td style={{ padding: "14px 8px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background:
                            load.priority === "EMERGENCY"
                              ? "rgba(239, 68, 68, 0.2)"
                              : load.priority === "URGENT"
                              ? "rgba(249, 115, 22, 0.2)"
                              : "rgba(56, 189, 248, 0.15)",
                          color:
                            load.priority === "EMERGENCY"
                              ? "#ef4444"
                              : load.priority === "URGENT"
                              ? "#f97316"
                              : "#38bdf8",
                        }}
                      >
                        {load.priority}
                      </span>
                    </td>
                    <td style={{ padding: "14px 8px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background:
                            load.status === "MATCHED"
                              ? "rgba(16, 185, 129, 0.2)"
                              : load.status === "AVAILABLE"
                              ? "rgba(14, 165, 233, 0.2)"
                              : "rgba(148, 163, 184, 0.2)",
                          color:
                            load.status === "MATCHED"
                              ? "#10b981"
                              : load.status === "AVAILABLE"
                              ? "#0ea5e9"
                              : "#94a3b8",
                        }}
                      >
                        {load.status}
                      </span>
                    </td>
                    <td style={{ padding: "14px 8px", color: load.assigned_vehicle_reg ? "#38bdf8" : "var(--text-muted)" }}>
                      {load.assigned_vehicle_reg ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <Truck size={14} />
                          {load.assigned_vehicle_reg}
                        </div>
                      ) : (
                        "Unassigned"
                      )}
                    </td>
                    <td style={{ padding: "14px 8px", textAlign: "right" }}>
                      <button
                        onClick={() => handleOpenMatching(load)}
                        style={{
                          background: "var(--accent-blue)",
                          color: "#fff",
                          border: "none",
                          padding: "6px 14px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <Compass size={13} /> Find Match
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SECTION 2: EMERGENCY SOS TRIAGE & RESCUE DISPATCH */}
      {emergencies.length > 0 && (
        <div className="card" style={{ padding: "24px", marginBottom: "28px", borderColor: "rgba(239, 68, 68, 0.4)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <AlertOctagon size={20} color="#ef4444" />
            <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>Active SOS Distress Beacons & Evacuation</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {emergencies.map((sos) => (
              <div
                key={sos.id}
                style={{
                  background: "rgba(239, 68, 68, 0.08)",
                  border: "1px solid rgba(239, 68, 68, 0.25)",
                  borderRadius: "var(--radius-md)",
                  padding: "16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontWeight: 700, fontSize: "15px" }}>Driver: {sos.driver_email}</span>
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 800,
                        padding: "2px 8px",
                        borderRadius: "10px",
                        background: sos.status === "RESOLVED" ? "#10b981" : "#ef4444",
                        color: "#fff",
                      }}
                    >
                      {sos.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>
                    "{sos.message}"
                  </div>
                  {sos.nearest_hub_name && (
                    <div style={{ fontSize: "12px", color: "#38bdf8", marginTop: "6px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <MapPin size={13} />
                      Nearest Safe Depot: <strong>{sos.nearest_hub_name}</strong> ({sos.nearest_hub_distance_km} km away)
                    </div>
                  )}
                </div>

                {sos.status !== "RESOLVED" && (
                  <div style={{ display: "flex", gap: "8px" }}>
                    {sos.status === "TRIGGERED" && (
                      <button
                        onClick={() => handleEmergencyAction(sos.id, "ACKNOWLEDGE")}
                        style={{
                          background: "#3b82f6",
                          color: "#fff",
                          border: "none",
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Acknowledge
                      </button>
                    )}
                    {sos.status !== "DISPATCHED" && (
                      <button
                        onClick={() => handleEmergencyAction(sos.id, "DISPATCH")}
                        style={{
                          background: "#f97316",
                          color: "#fff",
                          border: "none",
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Dispatch Rescue
                      </button>
                    )}
                    <button
                      onClick={() => handleEmergencyAction(sos.id, "RESOLVE")}
                      style={{
                        background: "#10b981",
                        color: "#fff",
                        border: "none",
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Clear & Resolve
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: LOAD CONSOLIDATION OPPORTUNITIES */}
      {consolidations.length > 0 && (
        <div className="card" style={{ padding: "24px", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <Layers size={20} color="#38bdf8" />
            <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>
              AI Load Consolidation Opportunities ({consolidations.length})
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            {consolidations.map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "16px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "13px", fontWeight: 700 }}>Bundle #{idx + 1}</span>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#10b981" }}>
                    Save ~₹{Number(item.estimated_savings_inr).toLocaleString()}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "8px 0" }}>
                  Combined Payload: <strong>{item.combined_weight_kg} kg</strong> • Detour:{" "}
                  <strong>{item.total_detour_km} km</strong> (+{item.additional_delay_min} min)
                </p>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: "8px",
                    background: "rgba(56, 189, 248, 0.2)",
                    color: "#38bdf8",
                  }}
                >
                  HIGH CORRIDOR COMPATIBILITY
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CANDIDATE MATCHING MODAL / DRAWER */}
      {selectedLoad && (
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
            backdropFilter: "blur(4px)",
          }}
        >
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              width: "90%",
              maxWidth: "800px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "28px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.6)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
              <div>
                <h3 style={{ fontSize: "20px", fontWeight: 800, margin: 0 }}>
                  Automated Matching Recommendations
                </h3>
                <p style={{ margin: "6px 0 0", fontSize: "13px", color: "var(--text-secondary)" }}>
                  Evaluating candidates for <strong>{selectedLoad.title || `Load #${selectedLoad.id.slice(0, 8)}`}</strong> ({selectedLoad.weight_kg}kg • {selectedLoad.cargo_type})
                </p>
              </div>
              <button
                onClick={() => setSelectedLoad(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  fontSize: "20px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {feedbackMsg && (
              <div
                style={{
                  background: feedbackMsg.includes("Error") ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
                  border: `1px solid ${feedbackMsg.includes("Error") ? "#ef4444" : "#10b981"}`,
                  borderRadius: "var(--radius-sm)",
                  padding: "10px 14px",
                  fontSize: "13px",
                  marginBottom: "16px",
                  color: feedbackMsg.includes("Error") ? "#fca5a5" : "#6ee7b7",
                }}
              >
                {feedbackMsg}
              </div>
            )}

            {candidatesLoading ? (
              <div style={{ textAlign: "center", padding: "40px" }}>
                <RefreshCw size={28} className="animate-spin" color="var(--accent-blue)" />
                <p style={{ marginTop: "12px", fontSize: "14px", color: "var(--text-secondary)" }}>
                  Calculating multi-factor utility scores and geohazard risk indices...
                </p>
              </div>
            ) : candidates.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                No physically eligible vehicles currently available for this payload.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {candidates.map((c) => (
                  <div
                    key={c.vehicle_id}
                    style={{
                      background: "rgba(255, 255, 255, 0.02)",
                      border: `1px solid ${c.rank === 1 ? "var(--accent-blue)" : "var(--border-subtle)"}`,
                      borderRadius: "var(--radius-md)",
                      padding: "18px",
                      position: "relative",
                    }}
                  >
                    {c.rank === 1 && (
                      <span
                        style={{
                          position: "absolute",
                          top: "12px",
                          right: "12px",
                          background: "var(--accent-blue)",
                          color: "#fff",
                          fontSize: "10px",
                          fontWeight: 800,
                          padding: "3px 8px",
                          borderRadius: "10px",
                        }}
                      >
                        TOP RECOMMENDATION
                      </span>
                    )}

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "16px", fontWeight: 800 }}>{c.registration_number}</span>
                          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>({c.vehicle_type} • Cap: {c.capacity_kg}kg)</span>
                        </div>
                        <p style={{ margin: "6px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                          {c.explanation}
                        </p>
                      </div>
                      <div style={{ textAlign: "right", marginRight: c.rank === 1 ? "120px" : "0" }}>
                        <div style={{ fontSize: "22px", fontWeight: 900, color: c.final_score > 80 ? "#10b981" : "#f59e0b" }}>
                          {c.final_score}
                          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>/100</span>
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Matching Score</div>
                      </div>
                    </div>

                    {/* Subscore Breakdown Chips */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "12px" }}>
                      <span style={{ fontSize: "11px", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "6px" }}>
                        Capacity: <strong>{c.subscores.capacity_score}</strong>
                      </span>
                      <span style={{ fontSize: "11px", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "6px" }}>
                        Pickup Proximity: <strong>{c.distance_to_pickup_km} km</strong>
                      </span>
                      <span style={{ fontSize: "11px", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "6px" }}>
                        Safety: <strong>{c.subscores.safety_score}</strong>
                      </span>
                      <span style={{ fontSize: "11px", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "6px" }}>
                        Est Cost: <strong>₹{Number(c.estimated_cost_inr).toLocaleString()}</strong>
                      </span>
                    </div>

                    <div style={{ marginTop: "16px", display: "flex", justifyContent: "flex-end" }}>
                      <button
                        onClick={() => handleAssignVehicle(c.vehicle_id)}
                        disabled={assigningVehicleId === c.vehicle_id}
                        style={{
                          background: c.rank === 1 ? "var(--accent-blue)" : "#334155",
                          color: "#fff",
                          border: "none",
                          padding: "8px 16px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        {assigningVehicleId === c.vehicle_id ? (
                          <RefreshCw size={14} className="animate-spin" />
                        ) : (
                          <Check size={14} />
                        )}
                        {manualOverride ? "Override & Assign" : "Confirm Assignment"}
                      </button>
                    </div>
                  </div>
                ))}

                {/* Operator Manual Override Controls */}
                <div style={{ marginTop: "16px", padding: "14px", border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={manualOverride}
                      onChange={(e) => setManualOverride(e.target.checked)}
                    />
                    <span>Operator Manual Override (Bypass Automated Recommendation)</span>
                  </label>
                  {manualOverride && (
                    <input
                      type="text"
                      placeholder="Mandatory justification for audit log (e.g. Return load balancing, driver home base)..."
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      style={{
                        width: "100%",
                        marginTop: "10px",
                        padding: "8px 12px",
                        background: "rgba(0,0,0,0.3)",
                        border: "1px solid var(--border-subtle)",
                        color: "#fff",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "12px",
                      }}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
