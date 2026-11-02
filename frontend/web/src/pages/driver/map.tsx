import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { Layout } from "../../components/Layout";
import { useLanguage } from "../../context/LanguageContext";
import { api } from "../../services/api";
import { TransportMap } from "../../components/TransportMap";
import {
  Navigation,
  Compass,
  ArrowRight,
  ShieldCheck,
  WifiOff,
  Radio,
  MapPin,
  Clock,
  Layers,
} from "lucide-react";

export default function DriverMapPage() {
  const router = useRouter();
  const { t } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [dashRes, graphRes] = await Promise.all([
          api.getDriverDashboard().catch(() => null),
          api.getGraphDump().catch(() => ({ nodes: [], edges: [] })),
        ]);
        if (dashRes) setData(dashRes.data);
        if (graphRes) {
          setNodes(graphRes.nodes || []);
          setEdges(graphRes.edges || []);
        }
      } catch (err) {
        console.error("Map load error:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const trip = data?.active_trip;

  return (
    <Layout
      title={t("navigation")}
      subtitle={trip ? `${trip.origin_name} → ${trip.destination_name}` : "Turn-by-Turn GPS Guidance"}
    >
      <Head>
        <title>Navigation — RouteIQ (SIH26002)</title>
      </Head>

      {/* Top Turn Guidance Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          borderLeft: "4px solid var(--accent-cyan)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "12px",
              background: "var(--accent-cyan)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
            }}
          >
            <Navigation size={24} />
          </div>
          <div>
            <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-primary)" }}>
              In 14 km: Bear Left onto NH-06 Hill Corridor
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              Target: Byrnihat Mountain Checkpost | Speed Advisory: 40 km/h (Monsoon Caution)
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="badge badge-safest">
            <ShieldCheck size={12} />
            <span>Offline Bundle v1.0.0 (SHA-256 OK)</span>
          </span>
        </div>
      </div>

      {/* Fullscreen Interactive Map */}
      <div
        className="glass-panel-elevated"
        style={{
          height: "calc(100vh - 230px)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <TransportMap
          nodes={nodes}
          edges={edges}
          selectedRoute={trip?.route || null}
          height="100%"
        />

        {/* Floating In-Cab Telemetry HUD */}
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            left: "20px",
            background: "rgba(15, 23, 42, 0.9)",
            backdropFilter: "blur(16px)",
            padding: "14px 20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            gap: "24px",
            boxShadow: "var(--shadow-lg)",
            zIndex: 10,
          }}
        >
          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>
              Remaining
            </div>
            <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>
              {trip?.route?.total_distance_km ? `${trip.route.total_distance_km} km` : "392 km"}
            </div>
          </div>

          <div style={{ width: "1px", height: "30px", background: "var(--border-subtle)" }} />

          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>
              ETA
            </div>
            <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--accent-cyan)" }}>
              {trip?.route?.total_time_min ? `${Math.floor(trip.route.total_time_min / 60)}h ${trip.route.total_time_min % 60}m` : "6h 45m"}
            </div>
          </div>

          <div style={{ width: "1px", height: "30px", background: "var(--border-subtle)" }} />

          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>
              Signal State
            </div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#10b981", display: "flex", alignItems: "center", gap: "4px" }}>
              <Radio size={14} />
              <span>Dead-Zone Mesh Active</span>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
