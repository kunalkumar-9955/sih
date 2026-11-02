import React, { useEffect, useRef, useState } from "react";
import { TransportEdge, TransportNode, RouteOption } from "../services/api";

interface TransportMapProps {
  nodes?: TransportNode[];
  edges?: TransportEdge[];
  selectedRoute?: RouteOption | null;
  height?: string;
}

export const TransportMap: React.FC<TransportMapProps> = ({
  nodes = [],
  edges = [],
  selectedRoute = null,
  height = "560px",
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    let map: any;

    const initMap = async () => {
      const maplibregl = (await import("maplibre-gl")).default;

      if (!mapContainer.current) return;

      map = new maplibregl.Map({
        container: mapContainer.current,
        style: {
          version: 8,
          sources: {
            "osm-tiles": {
              type: "raster",
              tiles: [
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
              ],
              tileSize: 256,
              attribution: "&copy; OpenStreetMap contributors",
            },
          },
          layers: [
            {
              id: "osm-layer",
              type: "raster",
              source: "osm-tiles",
              minzoom: 0,
              maxzoom: 19,
              paint: {
                "raster-opacity": 0.82,
                "raster-brightness-min": 0.2,
                "raster-contrast": 0.15,
                "raster-saturation": -0.6, // dark, high-contrast look
              },
            },
          ],
        },
        center: [92.15, 25.75], // Centered on Meghalaya / Assam corridor
        zoom: 7.8,
      });

      map.addControl(new maplibregl.NavigationControl(), "top-right");

      map.on("load", () => {
        mapInstance.current = map;
        setMapLoaded(true);
      });
    };

    initMap();

    return () => {
      if (map) map.remove();
    };
  }, []);

  // Update nodes and edges on map
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !mapLoaded) return;

    // 1. Edge source & layer
    const edgeFeatures = edges.map((e) => ({
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: e.geometry_coordinates || [],
      },
      properties: {
        id: e.id,
        mode: e.mode,
        hazard: e.hazard_score,
        road_name: e.road_name,
        time: e.base_transit_time_min,
      },
    }));

    if (map.getSource("network-edges")) {
      map.getSource("network-edges").setData({
        type: "FeatureCollection",
        features: edgeFeatures,
      });
    } else {
      map.addSource("network-edges", {
        type: "geojson",
        data: { type: "FeatureCollection", features: edgeFeatures },
      });

      map.addLayer({
        id: "network-edges-line",
        type: "line",
        source: "network-edges",
        paint: {
          "line-color": [
            "match",
            ["get", "mode"],
            "RAIL", "#8b5cf6",
            "WATERWAY", "#10b981",
            "TRANSFER", "#f59e0b",
            "#0284c7" // ROAD
          ],
          "line-width": 3,
          "line-opacity": 0.65,
        },
      });
    }

    // 2. Node source & layer
    const nodeFeatures = nodes
      .filter((n) => n.coordinates)
      .map((n) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [n.coordinates!.longitude, n.coordinates!.latitude],
        },
        properties: {
          id: n.id,
          name: n.name,
          type: n.node_type,
          typeDisplay: n.node_type_display,
          elevation: n.elevation_m,
        },
      }));

    if (map.getSource("network-nodes")) {
      map.getSource("network-nodes").setData({
        type: "FeatureCollection",
        features: nodeFeatures,
      });
    } else {
      map.addSource("network-nodes", {
        type: "geojson",
        data: { type: "FeatureCollection", features: nodeFeatures },
      });

      map.addLayer({
        id: "network-nodes-circle",
        type: "circle",
        source: "network-nodes",
        paint: {
          "circle-radius": [
            "match",
            ["get", "type"],
            "MULTIMODAL_HUB", 9,
            "WATERWAY_TERMINAL", 8,
            "RAIL_YARD", 8,
            6
          ],
          "circle-color": [
            "match",
            ["get", "type"],
            "MULTIMODAL_HUB", "#38bdf8",
            "WATERWAY_TERMINAL", "#10b981",
            "RAIL_YARD", "#c084fc",
            "CHECKPOST", "#fbbf24",
            "#ffffff"
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#0a0f1d",
        },
      });
    }
  }, [nodes, edges, mapLoaded]);

  // Highlight active selected route
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || !mapLoaded) return;

    if (selectedRoute && selectedRoute.geometry_coordinates?.length > 0) {
      const coords = selectedRoute.geometry_coordinates;
      const routeFeature = {
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: coords,
        },
        properties: {
          type: selectedRoute.route_type,
        },
      };

      if (map.getSource("selected-route")) {
        map.getSource("selected-route").setData(routeFeature);
      } else {
        map.addSource("selected-route", {
          type: "geojson",
          data: routeFeature,
        });

        // Glowing outer line
        map.addLayer({
          id: "selected-route-glow",
          type: "line",
          source: "selected-route",
          paint: {
            "line-color": "#38bdf8",
            "line-width": 8,
            "line-opacity": 0.4,
            "line-blur": 4,
          },
        });

        // Core sharp line
        map.addLayer({
          id: "selected-route-core",
          type: "line",
          source: "selected-route",
          paint: {
            "line-color": "#0284c7",
            "line-width": 4,
          },
        });
      }

      // Fit map bounds to show complete computed route
      const importMaplibregl = async () => {
        const maplibregl = (await import("maplibre-gl")).default;
        const bounds = new maplibregl.LngLatBounds();
        coords.forEach((coord: [number, number]) => bounds.extend(coord));
        map.fitBounds(bounds, { padding: 60, maxZoom: 12 });
      };
      importMaplibregl();
    } else {
      if (map.getSource("selected-route")) {
        map.getSource("selected-route").setData({
          type: "FeatureCollection",
          features: [],
        });
      }
    }
  }, [selectedRoute, mapLoaded]);

  return (
    <div style={{ position: "relative", width: "100%", height, borderRadius: "var(--radius-md)", overflow: "hidden" }}>
      <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />

      {/* Map Legend Overlay */}
      <div style={{
        position: "absolute",
        bottom: "16px",
        left: "16px",
        background: "rgba(15, 23, 42, 0.9)",
        backdropFilter: "blur(12px)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-sm)",
        padding: "10px 14px",
        fontSize: "11px",
        color: "var(--text-secondary)",
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        boxShadow: "var(--shadow-md)"
      }}>
        <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: "2px" }}>Network Modes</div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: "16px", height: "3px", background: "#0284c7", borderRadius: "2px" }} />
          <span>NH-6 / NH-27 Road</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: "16px", height: "3px", background: "#8b5cf6", borderRadius: "2px" }} />
          <span>NFR Rail Network</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: "16px", height: "3px", background: "#10b981", borderRadius: "2px" }} />
          <span>NW-2 / NW-16 Waterways</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#38bdf8", border: "1px solid #fff" }} />
          <span>Multimodal Logistics Hub</span>
        </div>
      </div>
    </div>
  );
};
