import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { TransportMap } from "../components/TransportMap";
import { api, RouteOption, TransportEdge, TransportNode } from "../services/api";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Clock,
  Compass,
  DollarSign,
  Fuel,
  Info,
  Layers,
  MapPin,
  Navigation,
  Package,
  Shield,
  Shuffle,
  Truck,
  Zap,
} from "lucide-react";

export default function RouteExplorerPage() {
  const [nodes, setNodes] = useState<TransportNode[]>([]);
  const [edges, setEdges] = useState<TransportEdge[]>([]);
  const [originId, setOriginId] = useState<string>("");
  const [destId, setDestId] = useState<string>("");
  const [cargoWeight, setCargoWeight] = useState<string>("12000");
  const [allowMultimodal, setAllowMultimodal] = useState<boolean>(true);
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<RouteOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const res = await api.getGraphDump();
        setNodes(res.nodes || []);
        setEdges(res.edges || []);
        if (res.nodes && res.nodes.length >= 2) {
          // Pre-select Guwahati MMLP and Silchar Hub
          const gMmlp = res.nodes.find((n) => n.short_code === "GAU-MMLP") || res.nodes[0];
          const sHub = res.nodes.find((n) => n.short_code === "AS-SILCHAR-HUB") || res.nodes[res.nodes.length - 1];
          setOriginId(gMmlp.id);
          setDestId(sHub.id);
        }
      } catch (err) {
        console.error("Failed to load nodes:", err);
      }
    };
    fetchGraph();
  }, []);

  const handleCompute = async () => {
    if (!originId || !destId) {
      setError("Please select both origin and destination nodes.");
      return;
    }
    if (originId === destId) {
      setError("Origin and destination cannot be the same node.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const weightNum = cargoWeight ? parseFloat(cargoWeight) : undefined;
      const computed = await api.computeRoutes(
        originId,
        destId,
        ["SAFEST", "FASTEST", "CHEAPEST", "MULTIMODAL"],
        { cargoWeight: weightNum, allowMultimodal }
      );
      setRoutes(computed);
      if (computed.length > 0) {
        setSelectedRoute(computed[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to calculate routes.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout
      title="Dynamic Multi-Modal Route Explorer"
      subtitle="Compute risk-aware paths across difficult mountainous terrain, landslides, and seasonal bottlenecks"
    >
      <Head>
        <title>Route Explorer — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      {/* Origin/Destination & Constraint Selector Bar */}
      <div className="glass-panel-elevated" style={{ padding: "20px 24px", marginBottom: "24px" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 1.2fr 0.8fr auto auto",
          gap: "16px",
          alignItems: "end"
        }}>
          {/* Origin */}
          <div>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600, color: "var(--accent-cyan)", marginBottom: "6px" }}>
              <MapPin size={14} />
              <span>ORIGIN LOGISTICS NODE</span>
            </label>
            <select
              value={originId}
              onChange={(e) => setOriginId(e.target.value)}
              style={{
                width: "100%",
                padding: "11px 12px",
                background: "var(--bg-tertiary)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                color: "#fff",
                fontSize: "13px",
                outline: "none"
              }}
            >
              {nodes.map((n) => (
                <option key={n.id} value={n.id} style={{ background: "#0f172a" }}>
                  {n.name} ({n.node_type_display})
                </option>
              ))}
            </select>
          </div>

          {/* Destination */}
          <div>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600, color: "var(--accent-emerald)", marginBottom: "6px" }}>
              <Compass size={14} />
              <span>DESTINATION LOGISTICS NODE</span>
            </label>
            <select
              value={destId}
              onChange={(e) => setDestId(e.target.value)}
              style={{
                width: "100%",
                padding: "11px 12px",
                background: "var(--bg-tertiary)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                color: "#fff",
                fontSize: "13px",
                outline: "none"
              }}
            >
              {nodes.map((n) => (
                <option key={n.id} value={n.id} style={{ background: "#0f172a" }}>
                  {n.name} ({n.node_type_display})
                </option>
              ))}
            </select>
          </div>

          {/* Cargo Payload Weight Constraint */}
          <div>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
              <Package size={14} />
              <span>CARGO WT (KG)</span>
            </label>
            <input
              type="number"
              value={cargoWeight}
              onChange={(e) => setCargoWeight(e.target.value)}
              placeholder="e.g. 15000"
              style={{
                width: "100%",
                padding: "11px 12px",
                background: "var(--bg-tertiary)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                color: "#fff",
                fontSize: "13px",
                outline: "none"
              }}
            />
          </div>

          {/* Multimodal Switch Toggle */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Multimodal
            </label>
            <label style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 14px",
              background: "var(--bg-tertiary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "13px"
            }}>
              <input
                type="checkbox"
                checked={allowMultimodal}
                onChange={(e) => setAllowMultimodal(e.target.checked)}
                style={{ cursor: "pointer", accentColor: "var(--accent-cyan)" }}
              />
              <span>Rail / Water</span>
            </label>
          </div>

          {/* Compute Button */}
          <button
            onClick={handleCompute}
            disabled={loading}
            className="btn btn-primary"
            style={{ padding: "12px 20px", height: "42px" }}
          >
            {loading ? "Optimizing..." : "Plan Routes"}
            {!loading && <Zap size={16} />}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: "12px", fontSize: "13px", color: "var(--accent-rose)", display: "flex", alignItems: "center", gap: "6px" }}>
            <AlertTriangle size={14} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Main Grid: Map (Left) & Route Comparison Cards (Right) */}
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "24px", alignItems: "start" }}>
        {/* Map Container */}
        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600 }}>Interactive Spatial Polyline View</span>
            {selectedRoute && (
              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                <span className={`badge badge-${selectedRoute.route_type.toLowerCase()}`}>
                  {selectedRoute.route_type_display} Selected
                </span>
                {selectedRoute.transfer_count ? (
                  <span className="badge badge-multimodal">
                    {selectedRoute.transfer_count} Transfer{selectedRoute.transfer_count > 1 ? "s" : ""}
                  </span>
                ) : null}
              </div>
            )}
          </div>
          <TransportMap
            nodes={nodes}
            edges={edges}
            selectedRoute={selectedRoute}
            height="620px"
          />
        </div>

        {/* Route Cards Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
            {routes.length > 0 ? `Optimization Options (${routes.length})` : "Route Options"}
          </h2>

          {routes.length === 0 && !loading && (
            <div className="glass-panel" style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
              <Compass size={36} style={{ margin: "0 auto 12px", color: "var(--accent-cyan)" }} />
              <p style={{ fontSize: "14px" }}>Click &quot;Plan Routes&quot; to evaluate SAFEST, FASTEST, CHEAPEST and MULTIMODAL alternatives with hazard weighting.</p>
            </div>
          )}

          {routes.map((r) => {
            const isSelected = selectedRoute?.id === r.id;
            let badgeClass = "badge-safest";
            let icon = <Shield size={16} />;
            if (r.route_type === "FASTEST") {
              badgeClass = "badge-fastest";
              icon = <Zap size={16} />;
            } else if (r.route_type === "CHEAPEST") {
              badgeClass = "badge-cheapest";
              icon = <DollarSign size={16} />;
            } else if (r.route_type === "MULTIMODAL") {
              badgeClass = "badge-multimodal";
              icon = <Shuffle size={16} />;
            }

            const riskScore = r.risk_score ?? r.hazard_penalty_score;

            return (
              <div
                key={r.id}
                onClick={() => setSelectedRoute(r)}
                className="glass-panel"
                style={{
                  padding: "18px 20px",
                  cursor: "pointer",
                  border: isSelected ? "2px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
                  boxShadow: isSelected ? "0 0 20px rgba(14, 165, 233, 0.25)" : "none",
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className={`badge ${badgeClass}`}>
                      {icon}
                      <span>{r.route_type_display}</span>
                    </span>
                    {isSelected && <Check size={16} color="var(--accent-cyan)" />}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Risk Index: <strong style={{ color: riskScore > 0.4 ? "#fb7185" : "#34d399" }}>{riskScore.toFixed(2)}</strong>
                  </div>
                </div>

                {/* Explanation Banner */}
                {r.explanation && (
                  <div style={{
                    padding: "8px 12px",
                    background: "rgba(14, 165, 233, 0.08)",
                    border: "1px solid rgba(14, 165, 233, 0.2)",
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: "var(--text-primary)",
                    lineHeight: 1.4,
                    marginBottom: "12px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "6px"
                  }}>
                    <Info size={14} color="var(--accent-cyan)" style={{ marginTop: "2px", flexShrink: 0 }} />
                    <span>{r.explanation}</span>
                  </div>
                )}

                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "12px",
                  marginBottom: "12px",
                  background: "var(--bg-tertiary)",
                  padding: "12px",
                  borderRadius: "var(--radius-sm)"
                }}>
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Distance</div>
                    <div style={{ fontSize: "16px", fontWeight: 700 }}>
                      {(r.total_distance_m / 1000).toFixed(1)} km
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Est. Duration</div>
                    <div style={{ fontSize: "16px", fontWeight: 700 }}>
                      {Math.floor(r.total_time_min / 60)}h {Math.round(r.total_time_min % 60)}m
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Est. Freight</div>
                    <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--accent-emerald)" }}>
                      ₹{Math.round(r.total_cost_inr).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Modes Used & Transfer Pill */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12px", color: "var(--text-secondary)" }}>
                  <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                    <span style={{ color: "var(--text-muted)" }}>Modes:</span>
                    {(r.modes_used || ["ROAD"]).map((m) => (
                      <span key={m} style={{
                        padding: "2px 6px",
                        background: "var(--bg-tertiary)",
                        borderRadius: "4px",
                        fontSize: "10px",
                        fontWeight: 600,
                        color: m === "RAIL" ? "#a78bfa" : m === "WATER" ? "#34d399" : m === "TRANSFER" ? "#fbbf24" : "#38bdf8"
                      }}>
                        {m}
                      </span>
                    ))}
                  </div>
                  <div>
                    {r.transfer_count ? `${r.transfer_count} Transfer(s)` : "Direct Corridor"}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Segment Details for Selected Route */}
          {selectedRoute && (
            <div className="glass-panel" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 700 }}>
                  Turn-by-Turn Corridor Traversal ({selectedRoute.segments.length} Segments)
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "260px", overflowY: "auto" }}>
                {selectedRoute.segments.map((seg, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      background: "var(--bg-tertiary)",
                      borderRadius: "6px",
                      fontSize: "12px"
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>
                        <span style={{ color: "var(--accent-cyan)", marginRight: "6px" }}>#{seg.sequence || idx + 1}</span>
                        {seg.source_node || seg.source_name} → {seg.target_node || seg.target_name}
                      </div>
                      <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                        {seg.road_name || seg.mode} • {(seg.distance_m / 1000).toFixed(1)} km
                        {seg.transfer_time_min ? ` • Transfer Penalty ${seg.transfer_time_min}m (₹${seg.transfer_cost_inr || 0})` : ""}
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontWeight: 600 }}>{seg.transit_time_min}m</div>
                      <div style={{ color: seg.hazard_score > 0.4 ? "#fb7185" : "#34d399", fontSize: "11px" }}>
                        Risk: {seg.hazard_score}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
