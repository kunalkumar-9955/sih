import React from "react";
import Head from "next/head";
import { Layout } from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useLanguage } from "../context/LanguageContext";
import { LanguageCode } from "../locales";
import {
  UserCheck,
  Shield,
  Globe,
  Sun,
  Moon,
  Truck,
  CheckCircle2,
  Key,
} from "lucide-react";

export default function ProfilePage() {
  const { user, isDriver } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const { language, setLanguage, languages, t } = useLanguage();

  if (!user) return null;

  return (
    <Layout
      title={t("profile")}
      subtitle="Identity, Role-Based Access Credentials, and Preferences"
    >
      <Head>
        <title>My Profile — RouteIQ (SIH26002)</title>
      </Head>

      <div style={{ maxWidth: "800px", display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Profile Card */}
        <div className="glass-panel-elevated" style={{ padding: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "24px" }}>
            <div
              style={{
                width: "72px",
                height: "72px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "28px",
                fontWeight: 800,
                color: "#fff",
                boxShadow: "0 0 24px rgba(14, 165, 233, 0.4)",
              }}
            >
              {user.first_name ? user.first_name[0] : user.email[0].toUpperCase()}
            </div>
            <div>
              <h2 style={{ fontSize: "22px", fontWeight: 800, color: "var(--text-primary)" }}>
                {user.first_name ? `${user.first_name} ${user.last_name}` : user.email}
              </h2>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "4px" }}>
                <span className={isDriver ? "badge badge-safest" : "badge badge-fastest"}>
                  <Shield size={12} />
                  <span>{user.role}</span>
                </span>
                {user.is_verified && (
                  <span className="badge badge-safest">
                    <UserCheck size={12} />
                    <span>MDoNER Verified</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "20px",
              background: "var(--bg-tertiary)",
              padding: "20px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Email</div>
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{user.email}</div>
            </div>
            <div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Platform UUID</div>
              <div style={{ fontWeight: 500, fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-secondary)" }}>
                {user.id}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Active Language</div>
              <div style={{ fontWeight: 600, color: "var(--accent-cyan)" }}>
                {languages.find((l) => l.code === language)?.nativeName} ({language.toUpperCase()})
              </div>
            </div>
            <div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Security Level</div>
              <div style={{ fontWeight: 600, color: "var(--accent-emerald)" }}>Level 3 (HMAC-SHA256 JWT)</div>
            </div>
          </div>
        </div>

        {/* Preferences & Theme Toggle Card */}
        <div className="glass-panel" style={{ padding: "28px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>
            Application Preferences
          </h3>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "20px" }}>
            {/* Theme Selector */}
            <div
              style={{
                padding: "16px",
                background: "var(--bg-tertiary)",
                borderRadius: "var(--radius-sm)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--text-primary)" }}>
                  Display Theme
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  Currently: {isDark ? "Dark Mode" : "Light Mode"}
                </div>
              </div>
              <button
                onClick={toggleTheme}
                className="btn btn-secondary"
                style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
              >
                {isDark ? <Sun size={15} color="#fbbf24" /> : <Moon size={15} color="#0ea5e9" />}
                <span>{isDark ? "Switch Light" : "Switch Dark"}</span>
              </button>
            </div>

            {/* Language Selector */}
            <div
              style={{
                padding: "16px",
                background: "var(--bg-tertiary)",
                borderRadius: "var(--radius-sm)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--text-primary)" }}>
                  {t("language")}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  6 Regional Languages Supported
                </div>
              </div>

              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as LanguageCode)}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  padding: "6px 10px",
                  fontSize: "12px",
                  fontWeight: 600,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                {languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.nativeName}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* RBAC Capabilities Card */}
        <div className="glass-panel" style={{ padding: "28px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>
            Granted RBAC Platform Permissions ({user.role})
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px" }}>
            {isDriver ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Scoped Trip Waypoint Navigation</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Offline Graph Bundle Navigation</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Cryptographic e-Way Manifest Display</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Corridor Reroute Detour Acknowledgement</span>
                </div>
              </>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Full Regional Multimodal Graph Administration</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Disruption Simulator Scenario Execution</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>Clarke-Wright Multi-Depot Fleet Optimization</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span>System-wide Diagnostic Health Monitoring</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
