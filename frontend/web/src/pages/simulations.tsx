import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { api } from "../services/api";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  CloudRain,
  Compass,
  Layers,
  Play,
  RefreshCw,
  ShieldAlert,
  Sliders,
  TrendingDown,
  Zap,
} from "lucide-react";

export default function SimulationsPage() {
  const [selectedScenario, setSelectedScenario] = useState("LANDSLIDE");
  const [rainfallMm, setRainfallMm] = useState(110);
  const [targetCorridor, setTargetCorridor] = useState("NH-6");
  const [loading, setLoading] = useState(false);
  const [simulationResult, setSimulationResult] = useState<any | null>(null);
  const [comparisons, setComparisons] = useState<any[]>([]);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const res = await api.runDisruptionSimulation({
        scenario_type: selectedScenario,
        target_corridor: targetCorridor,
        custom_parameters: { rainfall_intensity_mm: rainfallMm },
      });
      setSimulationResult(res);
      await fetchComparisons();
    } catch (e) {
      console.error("Simulation run error:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchComparisons = async () => {
    try {
      const res = await api.compareDisruptionScenarios(["NORMAL", "HEAVY_RAINFALL", "LANDSLIDE", "CRITICAL_CORRIDOR"]);
      if (res && res.comparisons) {
        setComparisons(res.comparisons);
      }
    } catch (e) {
      console.error("Scenarios comparison error:", e);
    }
  };

  useEffect(() => {
    fetchComparisons();
  }, []);

  const delta = simulationResult?.resilience_delta || {
    pre_disruption_accessibility: 88.5,
    post_disruption_accessibility: 59.2,
    accessibility_delta_pct: -29.3,
    multimodal_redundancy_before: 82.0,
    multimodal_redundancy_after: 45.0,
  };

  const metrics = simulationResult?.impact_metrics || {
    affected_edges_count: 8,
    affected_nodes_count: 5,
    impacted_shipments_count: 2,
    estimated_delay_hours: 4.8,
    alternative_routes_available: 3,
  };

  return (
    <Layout
      title="Network Disruption Scenario Simulator"
      subtitle="Extreme weather, geotechnical slope instability, and corridor outage impact simulation"
    >
      <Head>
        <title>Disruption Simulator — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      {/* Safety & Isolation Disclaimer Banner */}
      <div style={{
        background: "rgba(245, 158, 11, 0.12)",
        border: "1px solid #f59e0b",
        padding: "14px 20px",
        borderRadius: "var(--radius-md)",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <AlertOctagon size={20} color="#fbbf24" />
          <span style={{ fontSize: "13px", fontWeight: 600, color: "#fef3c7" }}>
            SIMULATION SANDBOX: All modeled disruptions run in memory and DO NOT mutate live road graph or dispatch trips.
          </span>
        </div>
        <span style={{
          fontSize: "11px",
          fontWeight: 700,
          background: "rgba(245, 158, 11, 0.25)",
          color: "#fbbf24",
          padding: "3px 8px",
          borderRadius: "4px",
        }}>
          ZERO PRODUCTION RISK
        </span>
      </div>

      {/* Scenario Control Panel */}
      <div style={{
        background: "var(--bg-secondary)",
        padding: "20px 24px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "16px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
              DISRUPTION SCENARIO
            </label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              style={{
                background: "var(--bg-tertiary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "13px",
                fontWeight: 600,
              }}
            >
              <option value="LANDSLIDE">Major Landslide Corridor Blockage (NH-6)</option>
              <option value="HEAVY_RAINFALL">Extreme Monsoon Rainfall (IMD Red Alert)</option>
              <option value="FLOOD">Brahmaputra Basin Flood & River Siltation</option>
              <option value="ROAD_CLOSURE">Critical Highway Bridge Outage</option>
              <option value="CRITICAL_CORRIDOR">Multi-Hazard Simultaneous Corridor Disruption</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
              SIMULATED RAINFALL (MM/24H)
            </label>
            <input
              type="number"
              value={rainfallMm}
              onChange={(e) => setRainfallMm(Number(e.target.value))}
              style={{
                background: "var(--bg-tertiary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "13px",
                width: "120px",
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
              TARGET CORRIDOR
            </label>
            <select
              value={targetCorridor}
              onChange={(e) => setTargetCorridor(e.target.value)}
              style={{
                background: "var(--bg-tertiary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: "13px",
              }}
            >
              <option value="NH-6">NH-6 (Shillong - Jowai - Silchar)</option>
              <option value="NH-27">NH-27 (East-West Highway)</option>
              <option value="NW-2">NW-2 (Brahmaputra Inland Waterway)</option>
              <option value="RAIL_LUMDING">Lumding - Badarpur Railway Hill Section</option>
            </select>
          </div>
        </div>

        <button
          onClick={runSimulation}
          disabled={loading}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
            color: "#fff",
            border: "none",
            padding: "10px 22px",
            borderRadius: "var(--radius-sm)",
            fontWeight: 700,
            fontSize: "13px",
            cursor: loading ? "not-allowed" : "pointer",
            boxShadow: "0 0 16px rgba(245, 158, 11, 0.4)",
          }}
        >
          {loading ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
          {loading ? "Simulating Outage..." : "Run Scenario Simulation"}
        </button>
      </div>

      {/* Resilience Delta Cards */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "16px",
        marginBottom: "24px",
      }}>
        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>Accessibility Impact</div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "#f87171" }}>
            {delta.post_disruption_accessibility?.toFixed(1)} <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>/ 100</span>
          </div>
          <span style={{ fontSize: "12px", color: "#f87171", display: "flex", alignItems: "center", gap: "4px", marginTop: "4px" }}>
            <TrendingDown size={14} /> {delta.accessibility_delta_pct?.toFixed(1)}% degradation
          </span>
        </div>

        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>Multimodal Redundancy</div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "#fbbf24" }}>
            {delta.multimodal_redundancy_after?.toFixed(1)} <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>/ 100</span>
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Rail / Barge detours available
          </span>
        </div>

        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>Impacted Network Segments</div>
          <div style={{ fontSize: "26px", fontWeight: 800 }}>
            {metrics.affected_edges_count} <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>Edges</span>
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            {metrics.affected_nodes_count} Nodes Isolated / Choked
          </span>
        </div>

        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>Est. Corridor Delay Added</div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "#38bdf8" }}>
            +{metrics.estimated_delay_hours?.toFixed(1)} <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>Hours</span>
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            {metrics.alternative_routes_available} Bypasses Identified
          </span>
        </div>
      </div>

      {/* Scenario Comparisons Table */}
      <div style={{
        background: "var(--bg-secondary)",
        padding: "24px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        marginBottom: "24px",
      }}>
        <h3 style={{ fontSize: "16px", fontWeight: 700, margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>
          <Layers size={18} color="#0ea5e9" /> Comparative Disruption Matrix
        </h3>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", textAlign: "left" }}>
                <th style={{ padding: "12px 16px" }}>Scenario</th>
                <th style={{ padding: "12px 16px" }}>Description</th>
                <th style={{ padding: "12px 16px" }}>Accessibility Score</th>
                <th style={{ padding: "12px 16px" }}>Degradation</th>
                <th style={{ padding: "12px 16px" }}>Affected Edges</th>
                <th style={{ padding: "12px 16px" }}>Est. Delay Added</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((c, i) => (
                <tr key={i} style={{ borderBottom: "1px solid rgba(148, 163, 184, 0.08)" }}>
                  <td style={{ padding: "12px 16px", fontWeight: 700, color: "#f8fafc" }}>{c.scenario}</td>
                  <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>{c.name}</td>
                  <td style={{ padding: "12px 16px", fontWeight: 600 }}>{c.accessibility_score?.toFixed(1)}/100</td>
                  <td style={{ padding: "12px 16px", color: c.accessibility_delta_pct < 0 ? "#f87171" : "#4ade80" }}>
                    {c.accessibility_delta_pct ? `${c.accessibility_delta_pct?.toFixed(1)}%` : "0.0%"}
                  </td>
                  <td style={{ padding: "12px 16px" }}>{c.affected_edges}</td>
                  <td style={{ padding: "12px 16px", color: "#38bdf8" }}>+{c.estimated_delay_hours?.toFixed(1)} hrs</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
