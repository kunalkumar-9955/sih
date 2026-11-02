import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { TransportMap } from "../components/TransportMap";
import { api, TransportEdge, TransportNode } from "../services/api";
import { Network, MapPin, Layers, Anchor, Train, Truck, ArrowRight } from "lucide-react";

export default function GraphPage() {
  const [nodes, setNodes] = useState<TransportNode[]>([]);
  const [edges, setEdges] = useState<TransportEdge[]>([]);
  const [filterMode, setFilterMode] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getGraphDump();
        setNodes(res.nodes || []);
        setEdges(res.edges || []);
      } catch (err) {
        console.error("Failed to load graph:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredEdges = filterMode === "ALL" ? edges : edges.filter((e) => e.mode === filterMode);

  return (
    <Layout
      title="Multimodal Transport Graph Topology"
      subtitle="Directed spatial graph of North Eastern Region roads, freight rail, and inland waterways"
    >
      <Head>
        <title>Transport Graph — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Map */}
        <div className="glass-panel-elevated" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <Network size={20} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: "16px", fontWeight: 700 }}>Corridor Topology & PostGIS Spatial Layer</h3>
            </div>
            {/* Mode Filter Pills */}
            <div style={{ display: "flex", gap: "8px" }}>
              {["ALL", "ROAD", "RAIL", "WATERWAY"].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setFilterMode(mode)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "var(--radius-full)",
                    border: filterMode === mode ? "1px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
                    background: filterMode === mode ? "rgba(14, 165, 233, 0.2)" : "var(--bg-tertiary)",
                    color: filterMode === mode ? "var(--accent-cyan)" : "var(--text-secondary)",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer"
                  }}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          <TransportMap nodes={nodes} edges={filteredEdges} height="520px" />
        </div>

        {/* Nodes & Edges Inspection Tables */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "24px" }}>
          {/* Nodes Table */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>
              Nodes ({nodes.length})
            </h3>
            <div style={{ maxHeight: "360px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {nodes.map((n) => (
                <div
                  key={n.id}
                  style={{
                    padding: "10px 12px",
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-sm)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "13px"
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{n.name}</div>
                    <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                      {n.state}, {n.district} • {n.elevation_m ? `${n.elevation_m}m elev` : "Lowland"}
                    </div>
                  </div>
                  <span className="badge badge-fastest" style={{ fontSize: "11px" }}>
                    {n.node_type_display}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Edges Table */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>
              Edges & Traversability ({filteredEdges.length})
            </h3>
            <div style={{ maxHeight: "360px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {filteredEdges.map((e) => (
                <div
                  key={e.id}
                  style={{
                    padding: "10px 12px",
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-sm)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "13px"
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{e.source_node_name} → {e.target_node_name}</div>
                    <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                      {e.road_name || e.mode_display} • {(e.distance_m / 1000).toFixed(1)} km • {e.base_transit_time_min}m
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{
                      fontWeight: 600,
                      fontSize: "11px",
                      color: e.hazard_score > 0.4 ? "#fb7185" : "#34d399"
                    }}>
                      Risk: {e.hazard_score}
                    </div>
                    <span className="badge badge-safest" style={{ fontSize: "10px", marginTop: "2px" }}>
                      {e.status_display}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
