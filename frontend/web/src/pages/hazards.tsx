import React from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { ShieldAlert, AlertTriangle, CloudRain, Mountain, Wind, CheckCircle } from "lucide-react";

export default function HazardsPage() {
  return (
    <Layout
      title="Hazard & Early Warning Risk Intelligence"
      subtitle="Terrain gradients, real-time landslide warnings, and extreme monsoon weather tracking"
    >
      <Head>
        <title>Hazards & Alerts — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Critical Alerts Banner */}
        <div style={{
          background: "rgba(244, 63, 94, 0.12)",
          border: "1px solid rgba(244, 63, 94, 0.3)",
          borderRadius: "var(--radius-md)",
          padding: "20px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "rgba(244, 63, 94, 0.2)",
              color: "#fb7185",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <AlertTriangle size={24} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: "16px", color: "#fb7185" }}>
                Active Geohazard Alert: NH-6 Sonapur Tunnel Segment
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
                Precipitation threshold exceeded (140mm/24h). Debris hazard index elevated to 0.75. Heavy multi-axle trucks advised to utilize rail detour via Lumding–Badarpur.
              </div>
            </div>
          </div>
          <span className="badge badge-hazard-high">CRITICAL ADVISORY</span>
        </div>

        {/* Hazard Grid Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
          <div className="glass-panel" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <Mountain size={20} color="var(--accent-amber)" />
              <h4 style={{ fontWeight: 700, fontSize: "15px" }}>Steep Gradient Corridor</h4>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Khliehriat to Malidor descent has a gradient &gt;8%. Heavy trucks restricted to low gear.
            </p>
            <span className="badge badge-cheapest">Gradient Alert</span>
          </div>

          <div className="glass-panel" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <CloudRain size={20} color="var(--accent-cyan)" />
              <h4 style={{ fontWeight: 700, fontSize: "15px" }}>IMD Radar Precipitation</h4>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Barak Valley catchment normal. River navigation on NW-16 (Fulertal-Silchar) green flagged.
            </p>
            <span className="badge badge-safest">Waterway Safe</span>
          </div>

          <div className="glass-panel" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <Wind size={20} color="var(--accent-purple)" />
              <h4 style={{ fontWeight: 700, fontSize: "15px" }}>Fog & Visibility Index</h4>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Shillong Plateau (Laitkor Peak) visibility 800m. Night transit operational with fog lights.
            </p>
            <span className="badge badge-multimodal">Moderate Caution</span>
          </div>
        </div>
      </div>
    </Layout>
  );
}
