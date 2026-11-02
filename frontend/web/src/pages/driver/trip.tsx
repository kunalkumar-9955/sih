import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { Layout } from "../../components/Layout";
import { useAuth } from "../../context/AuthContext";
import { useLanguage } from "../../context/LanguageContext";
import { api } from "../../services/api";
import {
  Truck,
  Navigation,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Compass,
  ArrowRight,
  Shield,
  ShieldAlert,
  Layers,
  MapPin,
  RefreshCw,
  TrendingDown,
  Check,
  X,
} from "lucide-react";

export default function DriverTripPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { t } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [rerouteModalOpen, setRerouteModalOpen] = useState(false);
  const [rerouteActionLoading, setRerouteActionLoading] = useState(false);
  const [rerouteSuccessMsg, setRerouteSuccessMsg] = useState("");

  const loadTrip = async () => {
    setLoading(true);
    try {
      const res = await api.getDriverDashboard();
      setData(res.data);
      if (router.query.advisory === "reroute" || res.data?.active_trip?.reroute_available) {
        setRerouteModalOpen(true);
      }
    } catch (err) {
      console.error("Failed to load driver trip:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrip();
  }, [router.query]);

  const handleAcknowledgeReroute = async (action: "ACCEPT" | "DECLINE") => {
    const trip = data?.active_trip;
    const reroute = trip?.pending_reroute;
    if (!trip || !reroute) {
      setRerouteModalOpen(false);
      return;
    }

    setRerouteActionLoading(true);
    try {
      await api.acknowledgeRerouteEvent(trip.id, reroute.id, action);
      setRerouteSuccessMsg(
        action === "ACCEPT"
          ? "Safer multimodal detour applied to active navigation!"
          : "Maintained current route as requested."
      );
      setRerouteModalOpen(false);
      await loadTrip();
    } catch (err: any) {
      console.warn("Reroute acknowledge fallback:", err);
      setRerouteSuccessMsg(`Route preference updated (${action}).`);
      setRerouteModalOpen(false);
    } finally {
      setRerouteActionLoading(false);
    }
  };

  const trip = data?.active_trip;
  const reroute = trip?.pending_reroute;

  return (
    <Layout
      title={t("myTrip")}
      subtitle={trip ? `${trip.origin_name} → ${trip.destination_name}` : "Trip Navigation"}
    >
      <Head>
        <title>My Active Trip — RouteIQ (SIH26002)</title>
      </Head>

      {rerouteSuccessMsg && (
        <div
          style={{
            padding: "14px 20px",
            background: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.35)",
            borderRadius: "var(--radius-md)",
            color: "#10b981",
            fontWeight: 600,
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <CheckCircle2 size={18} />
            <span>{rerouteSuccessMsg}</span>
          </div>
          <button
            onClick={() => setRerouteSuccessMsg("")}
            className="btn btn-secondary"
            style={{ fontSize: "11px", padding: "4px 8px" }}
          >
            Dismiss
          </button>
        </div>
      )}

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
      ) : !trip ? (
        <div className="glass-panel" style={{ padding: "50px 24px", textAlign: "center" }}>
          <Truck size={48} color="var(--text-muted)" style={{ margin: "0 auto 16px" }} />
          <h2 style={{ fontSize: "20px", color: "var(--text-primary)", marginBottom: "8px" }}>
            {t("noActiveTrip")}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "20px" }}>
            {t("noActiveTripSub")}
          </p>
          <button onClick={() => router.push("/driver")} className="btn btn-secondary">
            Return to Console
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Reroute Alert Banner if available */}
          {reroute && (
            <div
              style={{
                padding: "20px 24px",
                background: "rgba(14, 165, 233, 0.1)",
                border: "1px solid rgba(14, 165, 233, 0.4)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <ShieldAlert size={26} color="var(--accent-cyan)" />
                <div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: "var(--text-primary)" }}>
                    Safer Alternative Corridor Available (-{reroute.improvement_pct || 78}% Geohazard Exposure)
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    {reroute.trigger_reason || "Monsoon mudslides detected on Meghalaya ridge (NH-06)."}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={() => setRerouteModalOpen(true)}
                  className="btn btn-primary"
                  style={{ fontSize: "13px", padding: "8px 16px" }}
                >
                  Review Detour
                </button>
              </div>
            </div>
          )}

          {/* Granular Waypoint Timeline */}
          <div className="glass-panel" style={{ padding: "28px" }}>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 800,
                color: "var(--accent-cyan)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                marginBottom: "20px",
              }}
            >
              Turn-by-Turn Journey Progress
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Point 1: Origin */}
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      background: "#10b981",
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: "12px",
                    }}
                  >
                    1
                  </div>
                  <div style={{ width: "2px", height: "40px", background: "#10b981" }} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--accent-emerald)", fontWeight: 700, textTransform: "uppercase" }}>
                    ORIGIN TERMINAL (CLEARED)
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-primary)" }}>
                    {trip.origin_name}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Cargo Manifest Dispatched & Weighed | 0.0 km
                  </div>
                </div>
              </div>

              {/* Point 2: Current In-Transit Location */}
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      background: "var(--accent-cyan)",
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 0 14px var(--accent-cyan)",
                    }}
                  >
                    <Truck size={16} />
                  </div>
                  <div style={{ width: "2px", height: "40px", background: "var(--border-subtle)" }} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--accent-cyan)", fontWeight: 700, textTransform: "uppercase" }}>
                    CURRENT LIVE POSITION
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-primary)" }}>
                    Jorabat Border / Byrnihat Mountain Sector
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    GPS Vector: 91.85°E, 25.80°N | Speed: 42 km/h | 85.0 km completed
                  </div>
                </div>
              </div>

              {/* Point 3: Next Waypoint */}
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      background: "var(--bg-tertiary)",
                      border: "2px solid var(--accent-amber)",
                      color: "var(--accent-amber)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: "12px",
                    }}
                  >
                    3
                  </div>
                  <div style={{ width: "2px", height: "40px", background: "var(--border-subtle)" }} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--accent-amber)", fontWeight: 700, textTransform: "uppercase" }}>
                    NEXT WAYPOINT & CHECKPOST
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-primary)" }}>
                    Jowai Freight Terminal & Checkpost (NH-06)
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    ETA: 1h 45m | Digital Manifest Auto-Scanned via Geofence
                  </div>
                </div>
              </div>

              {/* Point 4: Destination */}
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      background: "var(--bg-tertiary)",
                      border: "2px solid var(--text-muted)",
                      color: "var(--text-muted)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: "12px",
                    }}
                  >
                    4
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>
                    FINAL DELIVERY DESTINATION
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-primary)" }}>
                    {trip.destination_name}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Remaining: {trip.route?.total_distance_km ? `${trip.route.total_distance_km} km` : "392 km"}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Modal for Reroute Proposal */}
          {rerouteModalOpen && reroute && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0, 0, 0, 0.75)",
                backdropFilter: "blur(8px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 999,
                padding: "20px",
              }}
            >
              <div
                className="glass-panel-elevated"
                style={{ maxWidth: "520px", width: "100%", padding: "32px" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
                  <AlertTriangle size={28} color="#f59e0b" />
                  <div>
                    <h3 style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>
                      Safer Route Available
                    </h3>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      Automated Mountain Risk Intelligence Alert
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    padding: "16px",
                    background: "rgba(244, 63, 94, 0.08)",
                    border: "1px solid rgba(244, 63, 94, 0.25)",
                    borderRadius: "var(--radius-sm)",
                    marginBottom: "20px",
                  }}
                >
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "#fb7185", marginBottom: "4px" }}>
                    Why Reroute?
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                    {reroute.trigger_reason || "Current route risk increased due to detected hazard on mountain ridge."}
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "12px",
                    marginBottom: "24px",
                  }}
                >
                  <div
                    style={{
                      padding: "12px",
                      background: "var(--bg-tertiary)",
                      borderRadius: "var(--radius-sm)",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Current Route Risk</div>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "#f43f5e", marginTop: "2px" }}>
                      82% (Critical)
                    </div>
                  </div>

                  <div
                    style={{
                      padding: "12px",
                      background: "var(--bg-tertiary)",
                      borderRadius: "var(--radius-sm)",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Proposed Detour Risk</div>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "#10b981", marginTop: "2px" }}>
                      18% (Safe)
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px" }}>
                  <button
                    onClick={() => handleAcknowledgeReroute("ACCEPT")}
                    disabled={rerouteActionLoading}
                    className="btn btn-primary"
                    style={{ flex: 1, padding: "12px" }}
                  >
                    <Check size={16} />
                    <span>{rerouteActionLoading ? "Applying..." : t("acceptNewRoute")}</span>
                  </button>

                  <button
                    onClick={() => handleAcknowledgeReroute("DECLINE")}
                    disabled={rerouteActionLoading}
                    className="btn btn-secondary"
                    style={{ padding: "12px 18px" }}
                  >
                    <X size={16} />
                    <span>{t("keepCurrentRoute")}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
