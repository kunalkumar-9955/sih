import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { Layout } from "../components/Layout";
import { TransportMap } from "../components/TransportMap";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { api, TransportEdge, TransportNode, Trip } from "../services/api";
import {
  Activity,
  AlertTriangle,
  Anchor,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Compass,
  Layers,
  MapPin,
  TrendingDown,
  Truck,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { t } = useLanguage();

  const [nodes, setNodes] = useState<TransportNode[]>([]);
  const [edges, setEdges] = useState<TransportEdge[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role === "DRIVER") {
      router.replace("/driver");
      return;
    }
    if (user?.role === "FLEET_OPERATOR") {
      router.replace("/fleet");
      return;
    }

    const fetchData = async () => {
      try {
        const [graphRes, tripsRes] = await Promise.all([
          api.getGraphDump().catch(() => ({ nodes: [], edges: [] })),
          api.getTrips().catch(() => ({ results: [] })),
        ]);
        setNodes(graphRes.nodes || []);
        setEdges(graphRes.edges || []);
        setTrips(tripsRes.results || []);
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <Layout
      title="RouteIQ Operational Intelligence"
      subtitle="Operational monitoring, real-time risk index, and dynamic multimodal graph"
    >
      <Head>
        <title>Operations — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      {/* Top Metrics Row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
        gap: "20px",
        marginBottom: "28px",
      }}>
        {/* Metric 1 */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 600 }}>Active Nodes</span>
            <div style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(14, 165, 233, 0.15)",
              color: "#38bdf8",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <MapPin size={18} />
            </div>
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {nodes.length > 0 ? nodes.length : 26}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Guwahati • Shillong • Silchar
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 600 }}>Intermodal Corridors</span>
            <div style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(16, 185, 129, 0.15)",
              color: "#34d399",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <Anchor size={18} />
            </div>
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {edges.length > 0 ? edges.length : 38}
          </div>
          <div style={{ fontSize: "12px", color: "#34d399", marginTop: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
            <CheckCircle2 size={13} />
            <span>Road, Rail & NW-2 Waterway</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 600 }}>Average Hazard Index</span>
            <div style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(245, 158, 11, 0.15)",
              color: "#fbbf24",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            0.18 <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-muted)" }}>/ 1.00</span>
          </div>
          <div style={{ fontSize: "12px", color: "#fbbf24", marginTop: "4px" }}>
            Sonapur bottleneck alert active
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 600 }}>Active Trips</span>
            <div style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(139, 92, 246, 0.15)",
              color: "#a78bfa",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <Truck size={18} />
            </div>
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            {trips.length > 0 ? trips.length : 3}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            GPS Live Position Tracking
          </div>
        </div>
      </div>

      {/* Main Map Card */}
      <div className="glass-panel-elevated" style={{ padding: "24px", marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 700 }}>NER Multimodal Transport Network</h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              High-resolution map of road corridors, railway lines, and inland waterways across Assam and Meghalaya
            </p>
          </div>
          <a
            href="/routes"
            className="btn btn-primary"
            style={{ padding: "8px 16px", fontSize: "13px" }}
          >
            <Compass size={16} />
            <span>Launch Route Engine</span>
          </a>
        </div>

        <TransportMap nodes={nodes} edges={edges} height="520px" />
      </div>

      {/* Corridor Segment Status List */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        <div className="glass-panel" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Strategic Corridor Health</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-sm)"
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>NH-6: Guwahati → Shillong</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>4-Lane Expressway • 98 km • High clearance</div>
              </div>
              <span className="badge badge-safest">100% CLEAR</span>
            </div>

            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-sm)"
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>NH-6: Khliehriat → Sonapur Tunnel</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Steep gradient • Landslide risk 0.75 • Cautious</div>
              </div>
              <span className="badge badge-hazard-high">HIGH RISK</span>
            </div>

            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-sm)"
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>NW-2 / NW-16: Pandu & Silchar Jetties</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Brahmaputra & Barak River Inland Navigation</div>
              </div>
              <span className="badge badge-multimodal">OPERATIONAL</span>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700 }}>Recent Trip Dispatch</h3>
            <a href="/trips" style={{ fontSize: "12px", color: "var(--accent-cyan)", display: "flex", alignItems: "center", gap: "2px" }}>
              <span>View all</span>
              <ArrowUpRight size={14} />
            </a>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{
              padding: "12px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-sm)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between"
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>Guwahati MMLP → Silchar Goods Yard</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Driver: Tenzing Norgay • Truck: AS-01-GB-1234</div>
              </div>
              <span className="badge badge-fastest">ACTIVE IN TRANSIT</span>
            </div>

            <div style={{
              padding: "12px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-sm)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between"
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>Shillong Central Hub → Jowai Terminal</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Agricultural Spices & Bamboo Crafts (2,400 kg)</div>
              </div>
              <span className="badge badge-safest">PLANNED</span>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
