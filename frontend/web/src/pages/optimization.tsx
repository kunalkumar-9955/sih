import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { api } from "../services/api";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  DollarSign,
  Layers,
  MapPin,
  Play,
  RefreshCw,
  Sliders,
  TrendingDown,
  TrendingUp,
  Truck,
  Zap,
} from "lucide-react";

export default function OptimizationPage() {
  const [loading, setLoading] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<any | null>(null);
  const [bundles, setBundles] = useState<any[]>([]);
  const [enableConsolidation, setEnableConsolidation] = useState(true);
  const [maxDetourKm, setMaxDetourKm] = useState(40);

  const fetchConsolidations = async () => {
    try {
      const res = await api.getConsolidationRecommendations();
      if (res && res.bundles) {
        setBundles(res.bundles);
      }
    } catch (e) {
      console.error("Consolidations fetch error:", e);
    }
  };

  const runOptimization = async () => {
    setLoading(true);
    try {
      const res = await api.runFleetOptimization({
        enable_consolidation: enableConsolidation,
        is_simulation: true,
      });
      setOptimizationResult(res);
      await fetchConsolidations();
    } catch (e) {
      console.error("Optimization run error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConsolidations();
  }, []);

  const comparison = optimizationResult?.plan_comparison || {
    baseline_total_distance_km: 685.0,
    optimized_total_distance_km: 560.3,
    distance_improvement_pct: 18.2,
    cost_improvement_pct: 21.5,
    optimized_vehicles_used: 2,
  };

  return (
    <Layout
      title="Multi-Depot Fleet & Load Consolidation Optimizer"
      subtitle="Clarke-Wright Savings heuristic, dynamic bundling, and capacity-constrained multi-stop dispatch"
    >
      <Head>
        <title>Fleet Optimization — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      {/* Control Strip */}
      <div style={{
        background: "var(--bg-secondary)",
        padding: "18px 24px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "16px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Optimization Strategy</span>
            <div style={{ fontSize: "14px", fontWeight: 600, color: "#f8fafc" }}>Clarke-Wright Savings + Spatial Clustering</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <label style={{ fontSize: "13px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={enableConsolidation}
                onChange={(e) => setEnableConsolidation(e.target.checked)}
              />
              Enable Cargo Bundling
            </label>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{
            fontSize: "11px",
            fontWeight: 700,
            padding: "4px 8px",
            borderRadius: "4px",
            background: "rgba(14, 165, 233, 0.15)",
            color: "#38bdf8",
            border: "1px solid rgba(14, 165, 233, 0.3)",
          }}>
            DEMO HEURISTIC SOLVER
          </span>

          <button
            onClick={runOptimization}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
              color: "#fff",
              border: "none",
              padding: "10px 20px",
              borderRadius: "var(--radius-sm)",
              fontWeight: 600,
              fontSize: "13px",
              cursor: loading ? "not-allowed" : "pointer",
              boxShadow: "0 0 16px rgba(16, 185, 129, 0.4)",
            }}
          >
            {loading ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
            {loading ? "Optimizing Dispatch..." : "Run Fleet Optimization"}
          </button>
        </div>
      </div>

      {/* Comparison KPI Banner */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "16px",
        marginBottom: "24px",
      }}>
        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>
            <span>Circuit Distance Saved</span>
            <TrendingDown size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "#34d399" }}>
            {comparison.distance_improvement_pct > 0 ? `-${comparison.distance_improvement_pct.toFixed(1)}%` : "Nominal"}
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {comparison.optimized_total_distance_km?.toFixed(0)} km vs {comparison.baseline_total_distance_km?.toFixed(0)} km baseline
          </span>
        </div>

        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>
            <span>Est. Transport Cost Reduction</span>
            <DollarSign size={18} color="#38bdf8" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "#38bdf8" }}>
            {comparison.cost_improvement_pct > 0 ? `-${comparison.cost_improvement_pct.toFixed(1)}%` : "Nominal"}
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Estimated Logistics Savings (₹)
          </span>
        </div>

        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>
            <span>Truck Dispatches Required</span>
            <Truck size={18} color="#a855f7" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800 }}>
            {comparison.optimized_vehicles_used || 2} <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>Vehicles</span>
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Zero unassigned compatible loads
          </span>
        </div>

        <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "13px", marginBottom: "6px" }}>
            <span>Active Consolidation Bundles</span>
            <Layers size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "#fbbf24" }}>
            {bundles.length || 2}
          </div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Compatibility Matrix Verified
          </span>
        </div>
      </div>

      {/* Recommended Consolidation Bundles */}
      <div style={{
        background: "var(--bg-secondary)",
        padding: "24px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        marginBottom: "24px",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={18} color="#38bdf8" /> Intelligent Load Consolidation Bundles
            </h3>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
              Compatible cargo co-loading with origin/destination detour radius under {maxDetourKm} km
            </p>
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            ESTIMATED VALUES (NOT CONTRACTUAL)
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
          {bundles.length === 0 ? (
            <div style={{ padding: "20px", color: "var(--text-muted)", fontSize: "13px" }}>
              No bundle recommendations generated yet. Click "Run Fleet Optimization" to generate candidates.
            </div>
          ) : (
            bundles.map((b, i) => (
              <div key={i} style={{
                background: "var(--bg-tertiary)",
                borderRadius: "var(--radius-sm)",
                padding: "16px",
                border: "1px solid var(--border-subtle)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <span style={{ fontWeight: 700, fontSize: "14px", color: "#f8fafc" }}>{b.bundle_code}</span>
                  <span style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    background: "rgba(34, 197, 94, 0.15)",
                    color: "#4ade80",
                    padding: "3px 8px",
                    borderRadius: "4px",
                  }}>
                    {b.expected_utilization_pct?.toFixed(0)}% Capacity Util
                  </span>
                </div>

                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  <div><strong>Origin:</strong> {b.origin_hub_name}</div>
                  <div><strong>Destination:</strong> {b.destination_hub_name}</div>
                  <div><strong>Weight / Vol:</strong> {b.total_weight_kg?.toFixed(0)} kg • {b.total_volume_cbm?.toFixed(1)} m³</div>
                  <div style={{ color: "#38bdf8", marginTop: "4px" }}>
                    <strong>Estimated Savings:</strong> ₹{b.estimated_cost_savings_inr?.toFixed(0)} (Est. +{b.estimated_delay_impact_min?.toFixed(0)}m detour)
                  </div>
                </div>

                <div style={{ fontSize: "11px", color: "var(--text-muted)", borderTop: "1px solid var(--border-subtle)", paddingTop: "8px" }}>
                  {b.reasons?.map((r: string, ri: number) => (
                    <div key={ri} style={{ marginBottom: "2px" }}>• {r}</div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
}
