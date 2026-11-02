import React from "react";
import {
  Sun,
  Moon,
  Globe,
  LogOut,
  ShieldCheck,
  AlertTriangle,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useLanguage } from "../context/LanguageContext";
import { LanguageCode } from "../locales";
import { BrandLogo } from "./BrandLogo";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const { user, logout, isDriver } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const { language, setLanguage, languages, t } = useLanguage();

  return (
    <header
      style={{
        height: "var(--header-height)",
        background: "var(--bg-surface)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--border-subtle)",
        padding: "0 28px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 90,
      }}
    >
      {/* Title & Context */}
      <div>
        <h1 style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.01em", color: "var(--text-primary)" }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "1px" }}>
            {subtitle}
          </p>
        )}
      </div>

      {/* Right Controls: Theme + Language + User Role */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Status Pill */}
        {!isDriver ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "var(--bg-tertiary)",
              padding: "6px 12px",
              borderRadius: "var(--radius-full)",
              fontSize: "12px",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "#10b981",
                boxShadow: "0 0 8px #10b981",
              }}
            />
            <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Corridor Risk:</span>
            <span style={{ color: "#10b981", fontWeight: 700 }}>MONITORED</span>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              color: "#10b981",
              padding: "5px 12px",
              borderRadius: "var(--radius-full)",
              fontSize: "12px",
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: "#10b981",
              }}
            />
            <span>{t("online")}</span>
          </div>
        )}

        {/* Real Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          title={isDark ? t("lightTheme") : t("darkTheme")}
          className="btn-secondary"
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-tertiary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-primary)",
            cursor: "pointer",
            padding: 0,
          }}
        >
          {isDark ? <Sun size={17} color="#fbbf24" /> : <Moon size={17} color="#0ea5e9" />}
        </button>

        {/* Real Working Language Selector */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--bg-tertiary)",
            padding: "6px 10px",
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
                style={{
                  background: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                }}
              >
                {lang.nativeName} ({lang.name})
              </option>
            ))}
          </select>
        </div>

        {/* User Role Pill & Logout */}
        {user && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              paddingLeft: "8px",
              borderLeft: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ textAlign: "right", display: "none" /* hide on very small screens */ }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                {user.first_name || user.email.split("@")[0]}
              </div>
              <div style={{ fontSize: "10px", color: "var(--accent-cyan)", fontWeight: 600 }}>
                {user.role}
              </div>
            </div>

            <button
              onClick={logout}
              title={t("logout")}
              className="btn-secondary"
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                background: "var(--bg-tertiary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-secondary)",
                cursor: "pointer",
                padding: 0,
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
