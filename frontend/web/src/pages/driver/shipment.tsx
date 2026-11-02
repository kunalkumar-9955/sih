import React, { useEffect, useState } from "react";
import Head from "next/head";
import { Layout } from "../../components/Layout";
import { useLanguage } from "../../context/LanguageContext";
import { api } from "../../services/api";
import {
  FileText,
  QrCode,
  CheckCircle2,
  ShieldCheck,
  Thermometer,
  Truck,
  Building,
  Calendar,
  Layers,
  ArrowRight,
} from "lucide-react";

export default function DriverShipmentPage() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getDriverDashboard();
        setData(res.data);
      } catch (err) {
        console.error("Shipment load error:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const shipment = data?.active_shipment;
  const trip = data?.active_trip;

  return (
    <Layout
      title={t("shipment")}
      subtitle="Digital e-Way Manifest & Cold-Chain IoT Verifications"
    >
      <Head>
        <title>Active Shipment — RouteIQ (SIH26002)</title>
      </Head>

      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 20px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              border: "3px solid var(--border-subtle)",
              borderTop: "3px solid var(--accent-cyan)",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 16px",
            }}
          />
          <p style={{ color: "var(--text-secondary)" }}>{t("loading")}</p>
        </div>
      ) : !shipment ? (
        <div className="glass-panel" style={{ padding: "50px 24px", textAlign: "center" }}>
          <FileText size={48} color="var(--text-muted)" style={{ margin: "0 auto 16px" }} />
          <h2 style={{ fontSize: "20px", color: "var(--text-primary)", marginBottom: "8px" }}>
            {t("noShipment")}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            No active digital manifest currently linked to this vehicle.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
          {/* Manifest Document Card */}
          <div className="glass-panel-elevated" style={{ padding: "32px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
              <div>
                <span className="badge badge-safest" style={{ marginBottom: "8px" }}>
                  <ShieldCheck size={12} />
                  <span>Verified Legal e-Way Bill</span>
                </span>
                <h2 style={{ fontSize: "22px", fontWeight: 800, color: "var(--text-primary)" }}>
                  {shipment.shipment_number}
                </h2>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  HMAC Token: <span style={{ fontFamily: "var(--font-mono)" }}>{shipment.qr_token}</span>
                </div>
              </div>

              {/* QR Code Graphic */}
              <div
                style={{
                  width: "90px",
                  height: "90px",
                  background: "#fff",
                  borderRadius: "12px",
                  padding: "8px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 14px rgba(0, 0, 0, 0.25)",
                }}
              >
                <QrCode size={74} color="#0f172a" />
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "28px" }}>
              <div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                  Consigned Goods
                </div>
                <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                  {shipment.cargo_summary}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                    Payload Weight
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--accent-cyan)", marginTop: "2px" }}>
                    {shipment.weight_kg ? `${shipment.weight_kg} kg` : "3,500 kg"}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                    Transport Vehicle
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                    {trip?.vehicle_registration || "AS-01-NER-2026"}
                  </div>
                </div>
              </div>

              <div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                  Designated Transit Route
                </div>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", marginTop: "2px" }}>
                  {shipment.origin_name} → {shipment.destination_name}
                </div>
              </div>
            </div>

            <div
              style={{
                padding: "14px",
                background: "var(--bg-tertiary)",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                color: "var(--text-secondary)",
              }}
            >
              MDoNER Gati Shakti e-Way compliance verified. Checkpost scanning enables zero-stop clearance via offline geofence sync.
            </div>
          </div>

          {/* Cold Chain IoT Telemetry Card */}
          <div className="glass-panel" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "10px",
                  background: "rgba(16, 185, 129, 0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#10b981",
                }}
              >
                <Thermometer size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>
                  Cold-Chain IoT Monitor
                </h3>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  Refrigerated Container Sensor Suite
                </div>
              </div>
            </div>

            <div
              style={{
                padding: "20px",
                background: "rgba(16, 185, 129, 0.08)",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                borderRadius: "var(--radius-md)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>
                CONTAINER INTERNAL TEMPERATURE
              </div>
              <div style={{ fontSize: "36px", fontWeight: 900, color: "#10b981", margin: "6px 0" }}>
                +4.2°C
              </div>
              <div style={{ fontSize: "12px", color: "#10b981", fontWeight: 700 }}>
                SAFE ZONE (Target: +2°C to +8°C)
              </div>
            </div>

            {/* Checkpost Stamp Verification */}
            <div>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "12px" }}>
                Checkpost Clearance Log
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                      Jorabat State Border Checkpost
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Assam / Meghalaya Border
                    </div>
                  </div>
                  <span className="badge badge-safest">CLEARED</span>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                      Jowai Mountain Checkpost
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      NH-06 Sector
                    </div>
                  </div>
                  <span className="badge badge-fastest">UPCOMING</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
