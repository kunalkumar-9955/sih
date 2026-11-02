import React, { useState } from "react";
import Head from "next/head";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useLanguage } from "../context/LanguageContext";
import { LanguageCode } from "../locales";
import { BrandLogo } from "../components/BrandLogo";
import { ArrowRight, Lock, Mail, AlertCircle, Sun, Moon, Globe } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const { language, setLanguage, languages, t } = useLanguage();

  const [email, setEmail] = useState("admin@sih26002.gov.in");
  const [password, setPassword] = useState("Admin@SIH26002!");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  const setDemoRole = (roleEmail: string, rolePass: string) => {
    setEmail(roleEmail);
    setPassword(rolePass);
    setError("");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-primary)",
        padding: "24px",
        position: "relative",
      }}
    >
      <Head>
        <title>Sign In — RouteIQ | Smart Multi-Modal Logistics & Risk Intelligence Platform (SIH26002)</title>
      </Head>

      {/* Top Floating Controls: Theme & Language */}
      <div
        style={{
          position: "absolute",
          top: "20px",
          right: "24px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <button
          onClick={toggleTheme}
          title={isDark ? t("lightTheme") : t("darkTheme")}
          className="btn-secondary"
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "var(--radius-sm)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 0,
            cursor: "pointer",
          }}
        >
          {isDark ? <Sun size={17} color="#fbbf24" /> : <Moon size={17} color="#0ea5e9" />}
        </button>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--bg-tertiary)",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <Globe size={14} color="var(--accent-cyan)" />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as LanguageCode)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-primary)",
              fontSize: "12px",
              fontWeight: 600,
              outline: "none",
              cursor: "pointer",
            }}
          >
            {languages.map((lang) => (
              <option
                key={lang.code}
                value={lang.code}
                style={{ background: "var(--bg-secondary)", color: "var(--text-primary)" }}
              >
                {lang.nativeName}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div
        className="glass-panel-elevated"
        style={{
          width: "100%",
          maxWidth: "460px",
          padding: "36px 32px",
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "12px" }}>
            <BrandLogo size={46} showText={false} />
          </div>
          <h1
            style={{
              fontSize: "24px",
              fontWeight: 800,
              letterSpacing: "-0.02em",
              color: "var(--text-primary)",
              marginBottom: "4px",
            }}
          >
            RouteIQ
          </h1>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
            {t("brandSubtitle")}
          </p>
        </div>

        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "12px 14px",
              background: "rgba(244, 63, 94, 0.12)",
              border: "1px solid rgba(244, 63, 94, 0.3)",
              borderRadius: "var(--radius-sm)",
              color: "#fb7185",
              fontSize: "13px",
              marginBottom: "20px",
            }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                marginBottom: "6px",
              }}
            >
              Official Email Address
            </label>
            <div style={{ position: "relative" }}>
              <Mail
                size={16}
                style={{
                  position: "absolute",
                  left: "14px",
                  top: "14px",
                  color: "var(--text-muted)",
                }}
              />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@domain.gov.in"
                style={{
                  width: "100%",
                  padding: "12px 14px 12px 42px",
                  background: "var(--bg-tertiary)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: "14px",
                  outline: "none",
                  transition: "border-color 0.2s ease",
                }}
              />
            </div>
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                marginBottom: "6px",
              }}
            >
              Secure Password
            </label>
            <div style={{ position: "relative" }}>
              <Lock
                size={16}
                style={{
                  position: "absolute",
                  left: "14px",
                  top: "14px",
                  color: "var(--text-muted)",
                }}
              />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: "100%",
                  padding: "12px 14px 12px 42px",
                  background: "var(--bg-tertiary)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: "14px",
                  outline: "none",
                  transition: "border-color 0.2s ease",
                }}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{
              padding: "13px",
              fontSize: "14px",
              marginTop: "4px",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Authenticating..." : "Sign In to RouteIQ"}
            {!loading && <ArrowRight size={18} />}
          </button>
        </form>

        {/* Fast Switch Role Accounts for Demonstration */}
        <div style={{ marginTop: "24px", paddingTop: "18px", borderTop: "1px solid var(--border-subtle)" }}>
          <div
            style={{
              fontSize: "11px",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              textAlign: "center",
              marginBottom: "12px",
            }}
          >
            Quick Demo Persona Login
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
            <button
              type="button"
              onClick={() => setDemoRole("admin@sih26002.gov.in", "Admin@SIH26002!")}
              className="btn btn-secondary"
              style={{
                fontSize: "12px",
                padding: "10px 8px",
                border: email.includes("admin") ? "1px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
                background: email.includes("admin") ? "rgba(14, 165, 233, 0.1)" : "var(--bg-tertiary)",
              }}
            >
              Ministry Admin
            </button>
            <button
              type="button"
              onClick={() => setDemoRole("driver1@ner.gov.in", "SecurePassword123!")}
              className="btn btn-secondary"
              style={{
                fontSize: "12px",
                padding: "10px 8px",
                border: email.includes("driver") ? "1px solid var(--accent-emerald)" : "1px solid var(--border-subtle)",
                background: email.includes("driver") ? "rgba(16, 185, 129, 0.1)" : "var(--bg-tertiary)",
              }}
            >
              Truck Driver
            </button>
          </div>
          <div
            style={{
              fontSize: "11px",
              color: "var(--text-muted)",
              textAlign: "center",
              marginTop: "12px",
            }}
          >
            SIH Problem Statement: <strong>SIH26002</strong> | Ministry of Development of North Eastern Region
          </div>
        </div>
      </div>
    </div>
  );
}
