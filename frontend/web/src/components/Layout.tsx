import React from "react";
import { useRouter } from "next/router";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { LayoutDashboard, Truck, Compass, ShieldAlert, UserCheck } from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export const Layout: React.FC<LayoutProps> = ({ children, title, subtitle }) => {
  const { isDriver } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();

  const driverBottomNav = [
    { label: t("driverDashboard"), href: "/driver", icon: LayoutDashboard },
    { label: t("myTrip"), href: "/driver/trip", icon: Truck },
    { label: t("navigation"), href: "/driver/map", icon: Compass },
    { label: t("alerts"), href: "/driver/alerts", icon: ShieldAlert },
    { label: t("profile"), href: "/profile", icon: UserCheck },
  ];

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg-primary)" }}>
      <Sidebar />
      <div
        style={{
          marginLeft: "var(--sidebar-width)",
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          paddingBottom: isDriver ? "70px" : "0px", // space for bottom bar on mobile
        }}
      >
        <Header title={title} subtitle={subtitle} />
        <main style={{ flex: 1, padding: "28px", overflowY: "auto" }}>
          {children}
        </main>
      </div>

      {/* Driver Mobile Bottom Navigation Bar (Visible on mobile/tablet) */}
      {isDriver && (
        <nav
          className="driver-bottom-nav"
          style={{
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            height: "64px",
            background: "var(--bg-secondary)",
            backdropFilter: "blur(16px)",
            borderTop: "1px solid var(--border-subtle)",
            display: "none", // enabled via CSS media query below
            alignItems: "center",
            justifyContent: "space-around",
            zIndex: 1000,
            padding: "0 8px",
          }}
        >
          {driverBottomNav.map((item) => {
            const Icon = item.icon;
            const isActive = router.pathname === item.href;
            return (
              <button
                key={item.href}
                onClick={() => router.push(item.href)}
                style={{
                  background: "transparent",
                  border: "none",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "4px",
                  color: isActive ? "var(--accent-cyan)" : "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: "10px",
                  fontWeight: isActive ? 700 : 500,
                  padding: "6px 8px",
                }}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      )}

      <style jsx global>{`
        @media (max-width: 768px) {
          .driver-bottom-nav {
            display: flex !important;
          }
        }
      `}</style>
    </div>
  );
};
