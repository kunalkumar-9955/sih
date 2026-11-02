import React, { useEffect } from "react";
import { useRouter } from "next/router";
import { useAuth } from "../context/AuthContext";
import { ShieldAlert, ArrowRight } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
  driverOnly?: boolean;
  adminOnly?: boolean;
}

// Pages restricted to Admin / Operations / Fleet Managers
const ADMIN_OPERATIONAL_ROUTES = [
  "/command-center",
  "/simulations",
  "/optimization",
  "/fleet",
  "/graph",
];

// Pages restricted to Drivers
const DRIVER_SPECIFIC_ROUTES = [
  "/driver",
  "/driver/trip",
  "/driver/map",
  "/driver/shipment",
  "/driver/alerts",
];

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
  driverOnly,
  adminOnly,
}) => {
  const { user, isAuthenticated, loading, getDefaultPath } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();

  const currentPath = router.pathname;

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated && currentPath !== "/login") {
        router.push("/login");
        return;
      }

      // Root "/" redirect to role-specific home
      if (isAuthenticated && currentPath === "/") {
        const target = getDefaultPath();
        if (target !== "/") {
          router.replace(target);
        }
        return;
      }

      // If Driver tries to access admin operational routes
      if (user?.role === "DRIVER" && ADMIN_OPERATIONAL_ROUTES.some((r) => currentPath.startsWith(r))) {
        router.replace("/driver");
        return;
      }
    }
  }, [loading, isAuthenticated, user, currentPath, router, getDefaultPath]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          height: "100vh",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg-primary)",
          color: "var(--text-secondary)",
          fontFamily: "var(--font-heading)",
          fontSize: "18px",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              border: "3px solid var(--border-subtle)",
              borderTop: "3px solid var(--accent-cyan)",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 16px",
            }}
          />
          <p style={{ color: "var(--text-primary)", fontWeight: 600 }}>RouteIQ Intelligence...</p>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Validating Role-Based Security & Spatial Graph
          </p>
        </div>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Explicit role guards if passed as props
  if (user) {
    if (adminOnly && user.role === "DRIVER") {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg-primary)",
            padding: "24px",
          }}
        >
          <div
            className="glass-panel-elevated"
            style={{ maxWidth: "480px", padding: "36px", textAlign: "center" }}
          >
            <ShieldAlert size={48} color="#f43f5e" style={{ margin: "0 auto 16px" }} />
            <h2 style={{ fontSize: "22px", marginBottom: "8px", color: "var(--text-primary)" }}>
              403 / Access Restricted
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "24px" }}>
              Administrative operational controls and systemic simulation engines are restricted to
              Command Center operators. Drivers are assigned to the Driver Console.
            </p>
            <button
              onClick={() => router.push("/driver")}
              className="btn btn-primary"
              style={{ width: "100%" }}
            >
              <span>Go to Driver Console</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      );
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg-primary)",
            padding: "24px",
          }}
        >
          <div
            className="glass-panel-elevated"
            style={{ maxWidth: "480px", padding: "36px", textAlign: "center" }}
          >
            <ShieldAlert size={48} color="#f43f5e" style={{ margin: "0 auto 16px" }} />
            <h2 style={{ fontSize: "22px", marginBottom: "8px", color: "var(--text-primary)" }}>
              Access Denied
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "24px" }}>
              Your account role ({user.role}) does not have permission to view this section.
            </p>
            <button
              onClick={() => router.push(getDefaultPath())}
              className="btn btn-primary"
              style={{ width: "100%" }}
            >
              <span>Return to My Dashboard</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
};
