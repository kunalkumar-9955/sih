import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { Layout } from "../../components/Layout";
import { useLanguage } from "../../context/LanguageContext";
import { api } from "../../services/api";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  CloudRain,
  Mountain,
  ArrowRight,
  ShieldCheck,
  Radio,
} from "lucide-react";

export default function DriverAlertsPage() {
  const router = useRouter();
  const { t } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getDriverAlerts();
        setAlerts(res.data || []);
      } catch (err) {
        console.error("Alerts load error:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <Layout
      title={t("alerts")}
      subtitle="Corridor & Route-Scoped Hazards for Your Active Freight Vector"
    >
      <Head>
        <title>Route Alerts — RouteIQ (SIH26002)</title>
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
      ) : alerts.length === 0 ? (
        <div className="glass-panel" style={{ padding: "60px 24px", textAlign: "center" }}>
          <ShieldCheck size={52} color="#10b981" style={{ margin: "0 auto 16px" }} />
          <h2 style={{ fontSize: "20px", color: "var(--text-primary)", marginBottom: "8px" }}>
            {t("noHazards")}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", maxWidth: "420px", margin: "0 auto" }}>
            All 5 segments along your active transport path are currently within safe operational boundaries.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>
            Active Geohazard Advisories ({alerts.length})
          </div>

          {alerts.map((alt, idx) => (
            <div
              key={alt.id || idx}
              className="glass-panel"
              style={{
                padding: "24px",
                borderLeft: alt.severity === "CRITICAL" ? "4px solid #f43f5e" : "4px solid #f59e0b",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "20px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "flex", gap: "16px", flex: 1, minWidth: "260px" }}>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "12px",
                    background: alt.severity === "CRITICAL" ? "rgba(244, 63, 94, 0.15)" : "rgba(245, 158, 11, 0.15)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: alt.severity === "CRITICAL" ? "#f43f5e" : "#f59e0b",
                    flexShrink: 0,
                  }}
                >
                  <AlertTriangle size={22} />
                </div>

                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 800,
                        color: alt.severity === "CRITICAL" ? "#f43f5e" : "#f59e0b",
                        textTransform: "uppercase",
                      }}
                    >
                      {alt.severity} RISK
                    </span>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Source: {alt.source || "MDoNER State PWD Dispatch"}
                    </span>
                  </div>

                  <h3 style={{ fontSize: "17px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
                    {alt.road_name || "Mountain Corridor"}: {alt.type}
                  </h3>

                  <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {alt.message}
                  </p>

                  <div style={{ fontSize: "12px", color: "var(--accent-cyan)", marginTop: "10px", fontWeight: 600 }}>
                    Affects Corridor: <strong>{alt.corridor}</strong> | Automatic Detour Ready
                  </div>
                </div>
              </div>

              <button
                onClick={() => router.push("/driver/trip?advisory=reroute")}
                className="btn btn-primary"
                style={{ alignSelf: "center", fontSize: "13px", padding: "10px 18px" }}
              >
                <span>{t("viewReroute")}</span>
                <ArrowRight size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
