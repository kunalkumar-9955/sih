import React from "react";
import { useRouter } from "next/router";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { BrandLogo } from "./BrandLogo";
import {
  LayoutDashboard,
  Navigation,
  Truck,
  Network,
  ShieldAlert,
  UserCheck,
  LogOut,
  Radio,
  Layers,
  FileText,
  Compass,
  AlertTriangle,
  Activity,
} from "lucide-react";

export const Sidebar: React.FC = () => {
  const router = useRouter();
  const { user, logout, isDriver } = useAuth();
  const { t } = useLanguage();

  // Role-Aware Navigation Menus
  const adminNavItems = [
    { labelKey: "commandCenter" as const, href: "/command-center", icon: Radio },
    { labelKey: "routes" as const, href: "/routes", icon: Navigation },
    { labelKey: "trips" as const, href: "/trips", icon: Truck },
    { labelKey: "hazards" as const, href: "/hazards", icon: ShieldAlert },
    { labelKey: "fleet" as const, href: "/fleet", icon: Layers },
    { labelKey: "graph" as const, href: "/graph", icon: Network },
    { labelKey: "optimization" as const, href: "/optimization", icon: Activity },
    { labelKey: "simulations" as const, href: "/simulations", icon: AlertTriangle },
    { labelKey: "dashboard" as const, href: "/", icon: LayoutDashboard },
    { labelKey: "profile" as const, href: "/profile", icon: UserCheck },
  ];

  const driverNavItems = [
    { labelKey: "driverDashboard" as const, href: "/driver", icon: LayoutDashboard },
    { labelKey: "myTrip" as const, href: "/driver/trip", icon: Truck },
    { labelKey: "navigation" as const, href: "/driver/map", icon: Compass },
    { labelKey: "shipment" as const, href: "/driver/shipment", icon: FileText },
    { labelKey: "alerts" as const, href: "/driver/alerts", icon: ShieldAlert },
    { labelKey: "profile" as const, href: "/profile", icon: UserCheck },
  ];

  const navItems = isDriver ? driverNavItems : adminNavItems;

  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        height: "100vh",
        background: "var(--bg-secondary)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        position: "fixed",
        left: 0,
        top: 0,
        zIndex: 100,
        padding: "20px 16px",
      }}
    >
      {/* Brand Header */}
      <div style={{ paddingBottom: "20px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "16px" }}>
        <BrandLogo
          size={36}
          showText={true}
          subtitle={isDriver ? "Driver Terminal" : "Operations Hub"}
        />
      </div>

      {/* Role Indicator Banner */}
      <div
        style={{
          padding: "8px 12px",
          background: isDriver ? "rgba(16, 185, 129, 0.08)" : "rgba(14, 165, 233, 0.08)",
          border: `1px solid ${isDriver ? "rgba(16, 185, 129, 0.25)" : "rgba(14, 165, 233, 0.25)"}`,
          borderRadius: "var(--radius-sm)",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "11px", fontWeight: 700, color: isDriver ? "#10b981" : "#0ea5e9", textTransform: "uppercase" }}>
          {isDriver ? "Driver Portal" : "Operations Portal"}
        </span>
        <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>
          {user?.role || "GUEST"}
        </span>
      </div>

      {/* Navigation Links with immediate translation */}
      <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: "4px", overflowY: "auto" }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = router.pathname === item.href;
          return (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                background: isActive
                  ? "linear-gradient(90deg, rgba(14, 165, 233, 0.15) 0%, rgba(14, 165, 233, 0.03) 100%)"
                  : "transparent",
                color: isActive ? "var(--accent-cyan)" : "var(--text-secondary)",
                border: isActive ? "1px solid rgba(14, 165, 233, 0.3)" : "1px solid transparent",
                fontWeight: isActive ? 700 : 500,
                fontSize: "13px",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease",
              }}
            >
              <Icon size={17} color={isActive ? "var(--accent-cyan)" : "currentColor"} />
              <span>{t(item.labelKey)}</span>
            </button>
          );
        })}
      </nav>

      {/* User Info & Sign Out Footer */}
      <div
        style={{
          paddingTop: "14px",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {user && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: "13px",
              }}
            >
              {(user.first_name?.[0] || user.email[0]).toUpperCase()}
            </div>
            <div style={{ overflow: "hidden", flex: 1 }}>
              <div
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {user.first_name ? `${user.first_name} ${user.last_name}` : user.email.split("@")[0]}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {user.email}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="btn-secondary"
          style={{
            width: "100%",
            padding: "8px 12px",
            fontSize: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
          }}
        >
          <LogOut size={14} />
          <span>{t("logout")}</span>
        </button>
      </div>
    </aside>
  );
};
