import React from "react";

interface BrandLogoProps {
  size?: number;
  showText?: boolean;
  subtitle?: string;
  variant?: "horizontal" | "vertical" | "icon-only";
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = 38,
  showText = true,
  subtitle = "Smart Multi-Modal Logistics & Risk Intelligence",
  variant = "horizontal",
}) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: variant === "vertical" ? "8px" : "12px",
        flexDirection: variant === "vertical" ? "column" : "row",
      }}
    >
      {/* RouteIQ Dynamic Multimodal & Risk Intelligence Mark */}
      <div
        style={{
          width: `${size}px`,
          height: `${size}px`,
          minWidth: `${size}px`,
          borderRadius: "10px",
          background: "linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #4f46e5 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 0 16px rgba(14, 165, 233, 0.4)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <svg
          width={Math.round(size * 0.65)}
          height={Math.round(size * 0.65)}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Risk Intelligence Pulse Ring */}
          <circle cx="12" cy="12" r="9" stroke="rgba(255, 255, 255, 0.25)" strokeWidth="1.2" strokeDasharray="2 2" />
          {/* Multimodal Corridor Network Line */}
          <path
            d="M4 18L9 11L14 15L20 6"
            stroke="#ffffff"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Multimodal Origin, Transshipment, and Destination Nodes */}
          <circle cx="4" cy="18" r="2.5" fill="#38bdf8" />
          <circle cx="9" cy="11" r="2" fill="#ffffff" />
          <circle cx="14" cy="15" r="2" fill="#a78bfa" />
          <circle cx="20" cy="6" r="2.8" fill="#10b981" />
          {/* Directional Velocity Arrow */}
          <path
            d="M16 6H20V10"
            stroke="#ffffff"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {showText && (
        <div>
          <div
            style={{
              fontFamily: "var(--font-heading)",
              fontWeight: 800,
              fontSize: size > 40 ? "20px" : "17px",
              letterSpacing: "-0.02em",
              color: "var(--text-primary)",
              lineHeight: 1.1,
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>RouteIQ</span>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                color: "var(--accent-cyan)",
                background: "rgba(14, 165, 233, 0.12)",
                padding: "2px 6px",
                borderRadius: "4px",
                border: "1px solid rgba(14, 165, 233, 0.25)",
              }}
            >
              SIH26002
            </span>
          </div>
          {subtitle && (
            <div
              style={{
                fontSize: "11px",
                color: "var(--text-secondary)",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                marginTop: "2px",
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

