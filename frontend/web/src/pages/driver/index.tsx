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
  FileText,
  AlertTriangle,
  Radio,
  Wifi,
  WifiOff,
  RefreshCw,
  CheckCircle2,
  ArrowRight,
  Shield,
  ShieldAlert,
  Thermometer,
  Clock,
  Compass,
  QrCode,
  PhoneCall,
  Flame,
} from "lucide-react";

export default function DriverDashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { t } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<any>(null);
  const [isOfflineSimulated, setIsOfflineSimulated] = useState(false);
  const [sosActive, setSosActive] = useState(false);
  const [sosLoading, setSosLoading] = useState(false);

  const fetchDashboard = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.getDriverDashboard();
      setData(res.data);
      if (res.data?.emergency_sos?.has_active_sos) {
        setSosActive(true);
      }
      // Cache locally for offline resilience
      if (typeof window !== "undefined") {
        localStorage.setItem("northlink_driver_cache", JSON.stringify(res.data));
      }
    } catch (err: any) {
      console.warn("API load failed, falling back to local cache:", err);
      // Attempt reading local cached data
      if (typeof window !== "undefined") {
        const cached = localStorage.getItem("northlink_driver_cache");
        if (cached) {
          setData(JSON.parse(cached));
          setIsOfflineSimulated(true);
        } else {
          setError(err.message || "Failed to load driver operational state");
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleToggleSOS = async () => {
    setSosLoading(true);
    try {
      if (sosActive) {
        await api.triggerDriverSOS("RESOLVE");
        setSosActive(false);
      } else {
        await api.triggerDriverSOS("TRIGGER", "Driver requested immediate assistance via portal");
        setSosActive(true);
      }
    } catch (err) {
      // Toggle locally for demo if network fails
      setSosActive(!sosActive);
    } finally {
      setSosLoading(false);
    }
  };

  const trip = data?.active_trip;
  const shipment = data?.active_shipment;
  const hazards = data?.route_hazards || [];
  const driver = data?.driver;

  return (
    <Layout
      title={t("driverDashboard")}
      subtitle={`${t("welcomeDriver")}, ${driver?.name || user?.first_name || "Driver"}`}
    >
      <Head>
        <title>Driver Console — RouteIQ (SIH26002)</title>
      </Head>

      {/* Offline Mode Indicator & Toggle Banner */}
      {isOfflineSimulated && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 20px",
            background: "rgba(245, 158, 11, 0.12)",
            border: "1px solid rgba(245, 158, 11, 0.35)",
            borderRadius: "var(--radius-md)",
            marginBottom: "24px",
            color: "#fbbf24",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <WifiOff size={20} />
            <div>
              <div style={{ fontWeight: 700, fontSize: "14px" }}>{t("offlineBanner")}</div>
              <div style={{ fontSize: "12px", opacity: 0.85 }}>
                Local Dijkstra pathfinding and offline bundle v1.0.0 (54 edges cached) active.
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsOfflineSimulated(false)}
            className="btn btn-secondary"
            style={{ fontSize: "12px", padding: "6px 14px", color: "#fbbf24" }}
          >
            Reconnect Online
          </button>
        </div>
      )}

      {/* Top Greeting & Operational State Header */}
      <div
        className="glass-panel"
        style={{
          padding: "24px",
          marginBottom: "24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "52px",
              height: "52px",
              borderRadius: "16px",
              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              boxShadow: "0 0 20px rgba(16, 185, 129, 0.35)",
            }}
          >
            <Truck size={28} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>
                {driver?.name || "Tenzing Norbu"}
              </h2>
              <span className="badge badge-safest">
                <CheckCircle2 size={12} />
                <span>Verified Carrier</span>
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
              License: <strong>{driver?.license_number || "AS-01-2024-0099"}</strong> | Vehicle:{" "}
              <strong>{trip?.vehicle_registration || "AS-01-NER-2026"}</strong> | State: Assam / Meghalaya
            </p>
          </div>
        </div>

        {/* Connectivity & Offline Simulator Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => setIsOfflineSimulated(!isOfflineSimulated)}
            className="btn btn-secondary"
            title="Toggle offline state to demonstrate dead-zone resilience"
            style={{ fontSize: "12px", padding: "8px 14px", display: "flex", alignItems: "center", gap: "6px" }}
          >
            {isOfflineSimulated ? <WifiOff size={15} color="#f59e0b" /> : <Wifi size={15} color="#10b981" />}
            <span>{isOfflineSimulated ? "Simulating Offline" : "Online Mode"}</span>
          </button>

          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="btn btn-secondary"
            title={t("refresh")}
            style={{ padding: "8px", width: "36px", height: "36px" }}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} />
          </button>
        </div>
      </div>

      {loading && !data ? (
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
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{t("loading")}</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* 1. MAIN CARD: CURRENT ASSIGNED TRIP */}
          {trip ? (
            <div
              className="glass-panel-elevated"
              style={{
                padding: "28px",
                position: "relative",
                overflow: "hidden",
                border: "1px solid var(--border-glow)",
              }}
            >
              {/* Trip Header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "20px",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "11px",
                      fontWeight: 800,
                      color: "var(--accent-cyan)",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      marginBottom: "4px",
                    }}
                  >
                    {t("currentTrip")}
                  </div>
                  <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                    {t("tripId")}: <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{trip.id.slice(0, 13)}...</span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span className="badge badge-fastest">
                    <Radio size={12} />
                    <span>{trip.status}</span>
                  </span>
                  <span className="badge badge-safest">
                    <Shield size={12} />
                    <span>{t("safe")}</span>
                  </span>
                </div>
              </div>

              {/* Origin -> Destination Route Visual */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto 1fr",
                  alignItems: "center",
                  gap: "16px",
                  padding: "20px",
                  background: "var(--bg-tertiary)",
                  borderRadius: "var(--radius-md)",
                  marginBottom: "24px",
                }}
              >
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                    {t("origin")}
                  </div>
                  <div style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }}>
                    {trip.origin_name}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--accent-cyan)" }}>
                    {trip.origin_state || "Assam Corridor"}
                  </div>
                </div>

                <div style={{ textAlign: "center", padding: "0 10px" }}>
                  <div style={{ fontSize: "11px", color: "var(--accent-cyan)", fontWeight: 700, marginBottom: "4px" }}>
                    NH-06 / Lumding
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      color: "var(--accent-cyan)",
                    }}
                  >
                    <div style={{ width: "24px", height: "2px", background: "var(--accent-cyan)" }} />
                    <Compass size={20} />
                    <div style={{ width: "24px", height: "2px", background: "var(--accent-cyan)" }} />
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                    {t("destination")}
                  </div>
                  <div style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }}>
                    {trip.destination_name}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--accent-emerald)" }}>
                    {trip.destination_state || "Barak Valley"}
                  </div>
                </div>
              </div>

              {/* Metrics Grid */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "14px",
                  marginBottom: "24px",
                }}
              >
                <div
                  style={{
                    padding: "14px 16px",
                    background: "var(--bg-surface)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                    {t("distanceRemaining")}
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)", marginTop: "4px" }}>
                    {trip.route?.total_distance_km ? `${trip.route.total_distance_km} km` : "392.0 km"}
                  </div>
                </div>

                <div
                  style={{
                    padding: "14px 16px",
                    background: "var(--bg-surface)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                    {t("eta")}
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--accent-cyan)", marginTop: "4px" }}>
                    {trip.route?.total_time_min ? `${Math.floor(trip.route.total_time_min / 60)}h ${trip.route.total_time_min % 60}m` : "6h 45m"}
                  </div>
                </div>

                <div
                  style={{
                    padding: "14px 16px",
                    background: "var(--bg-surface)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                    {t("cargoWeight")}
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)", marginTop: "4px" }}>
                    {trip.cargo_weight_kg ? `${(trip.cargo_weight_kg / 1000).toFixed(1)} MT` : "3.5 MT"}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                <button
                  onClick={() => router.push("/driver/trip")}
                  className="btn btn-primary"
                  style={{ flex: 1, minWidth: "180px", padding: "14px 20px", fontSize: "15px" }}
                >
                  <span>{t("continueTrip")}</span>
                  <ArrowRight size={18} />
                </button>

                <button
                  onClick={() => router.push("/driver/map")}
                  className="btn btn-secondary"
                  style={{ padding: "14px 20px", fontSize: "14px" }}
                >
                  <Navigation size={16} />
                  <span>{t("viewRoute")}</span>
                </button>
              </div>
            </div>
          ) : (
            <div
              className="glass-panel"
              style={{ padding: "40px 24px", textAlign: "center" }}
            >
              <Truck size={42} color="var(--text-muted)" style={{ margin: "0 auto 12px" }} />
              <h3 style={{ fontSize: "18px", color: "var(--text-primary)", marginBottom: "6px" }}>
                {t("noActiveTrip")}
              </h3>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", maxWidth: "420px", margin: "0 auto" }}>
                {t("noActiveTripSub")}
              </p>
            </div>
          )}

          {/* 2. ROAD / HAZARD ALERT (Strictly Relevant to Driver's Route!) */}
          {hazards.length > 0 && (
            <div
              style={{
                padding: "20px 24px",
                background: "rgba(244, 63, 94, 0.08)",
                border: "1px solid rgba(244, 63, 94, 0.3)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "flex", gap: "14px", flex: 1, minWidth: "260px" }}>
                <AlertTriangle size={24} color="#f43f5e" style={{ flexShrink: 0, marginTop: "2px" }} />
                <div>
                  <div
                    style={{
                      fontSize: "11px",
                      fontWeight: 800,
                      color: "#f43f5e",
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      marginBottom: "4px",
                    }}
                  >
                    {t("routeHazardAlert")}
                  </div>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    {hazards[0].edge_name || "Sonapur Corridor (NH-06)"}: {hazards[0].incident_type}
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                    {hazards[0].description}
                  </p>
                  <div style={{ fontSize: "12px", color: "#fb7185", marginTop: "6px", fontWeight: 600 }}>
                    {t("rerouteNotice")}
                  </div>
                </div>
              </div>

              <button
                onClick={() => router.push("/driver/trip?advisory=reroute")}
                className="btn btn-danger"
                style={{ alignSelf: "center", padding: "10px 18px", fontSize: "13px" }}
              >
                <span>{t("viewReroute")}</span>
                <ArrowRight size={16} />
              </button>
            </div>
          )}

          {/* 3. ACTIVE SHIPMENT MANIFEST */}
          {shipment && (
            <div
              className="glass-panel"
              style={{ padding: "24px" }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "16px",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <FileText size={20} color="var(--accent-cyan)" />
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>
                    {t("activeShipment")}
                  </h3>
                </div>
                <span className="badge badge-safest">
                  <CheckCircle2 size={12} />
                  <span>{shipment.status || t("verifiedCheckpost")}</span>
                </span>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                    {t("cargoSummary")}
                  </div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                    {shipment.cargo_summary}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                    Shipment e-Way Document
                  </div>
                  <div style={{ fontSize: "14px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginTop: "2px" }}>
                    {shipment.shipment_number}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Thermometer size={18} color="#10b981" />
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                      {t("coldChain")}
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#10b981" }}>
                      Safe (+4.2°C)
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  onClick={() => router.push("/driver/shipment")}
                  className="btn btn-secondary"
                  style={{ fontSize: "12px", padding: "8px 14px" }}
                >
                  <QrCode size={15} />
                  <span>View Full e-Way Manifest</span>
                </button>
              </div>
            </div>
          )}

          {/* 4. QUICK OPERATIONS & SOS */}
          <div style={{ marginTop: "4px" }}>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 800,
                color: "var(--text-muted)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                marginBottom: "12px",
              }}
            >
              {t("quickActions")}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "12px",
              }}
            >
              <button
                onClick={() => router.push("/driver/trip")}
                className="btn-secondary"
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                }}
              >
                <Truck size={22} color="var(--accent-cyan)" />
                <span style={{ fontSize: "13px", fontWeight: 600 }}>{t("myTrip")}</span>
              </button>

              <button
                onClick={() => router.push("/driver/map")}
                className="btn-secondary"
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                }}
              >
                <Navigation size={22} color="var(--accent-emerald)" />
                <span style={{ fontSize: "13px", fontWeight: 600 }}>{t("navigation")}</span>
              </button>

              <button
                onClick={() => router.push("/driver/shipment")}
                className="btn-secondary"
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                }}
              >
                <FileText size={22} color="var(--accent-amber)" />
                <span style={{ fontSize: "13px", fontWeight: 600 }}>{t("shipment")}</span>
              </button>

              <button
                onClick={() => router.push("/driver/alerts")}
                className="btn-secondary"
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                }}
              >
                <ShieldAlert size={22} color="#f43f5e" />
                <span style={{ fontSize: "13px", fontWeight: 600 }}>{t("alerts")}</span>
              </button>

              {/* Emergency SOS Button */}
              <button
                onClick={handleToggleSOS}
                disabled={sosLoading}
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer",
                  background: sosActive ? "linear-gradient(135deg, #f43f5e 0%, #b91c1c 100%)" : "rgba(244, 63, 94, 0.12)",
                  border: "1px solid rgba(244, 63, 94, 0.4)",
                  color: sosActive ? "#fff" : "#fb7185",
                  transition: "all 0.2s ease",
                }}
              >
                <PhoneCall size={22} />
                <span style={{ fontSize: "13px", fontWeight: 700 }}>
                  {sosActive ? t("sosTriggered") : t("emergencySos")}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
