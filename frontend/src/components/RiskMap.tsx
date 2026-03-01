"use client";

import "leaflet/dist/leaflet.css";

import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import L from "leaflet";
import type { ComponentProps } from "react";
import type { FeatureCollection, Point } from "geojson";

type RiskLevel = "low" | "medium" | "high";

type RiskFeatureProperties = {
  risk_level?: RiskLevel;
  name?: string;
  risk_score?: number;
  surface_temp_c?: number | null;
  humidity_pct?: number | null;
  precip_mm?: number | null;
  condition_label?: string | null;
  nearby_alerts?: number;
  data_staleness_minutes?: number | null;
};

type Props = {
  geojson: FeatureCollection<Point, RiskFeatureProperties> | null;
  legendCounts: Record<RiskLevel, number>;
  displayedCount: number;
  dataKey: string;
};

const RISK_COLORS: Record<RiskLevel, string> = {
  high: "#ef4444",
  medium: "#eab308",
  low: "#22c55e",
};

const LEGEND_ITEMS: Array<{ level: RiskLevel; label: string; range: string }> = [
  { level: "high", label: "High risk", range: "61-100" },
  { level: "medium", label: "Medium risk", range: "31-60" },
  { level: "low", label: "Low risk", range: "0-30" },
];

type GeoJsonProps = ComponentProps<typeof GeoJSON>;
type PointToLayerFn = NonNullable<GeoJsonProps["pointToLayer"]>;
type OnEachFeatureFn = NonNullable<GeoJsonProps["onEachFeature"]>;

const toRiskProps = (raw: unknown): RiskFeatureProperties | null => {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  return raw as RiskFeatureProperties;
};

const sanitizeHtml = (value: string): string =>
  value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const formatValue = (value: number | null | undefined, suffix: string): string => {
  if (value == null) {
    return "N/A";
  }
  return `${value}${suffix}`;
};

export default function RiskMap({ geojson, legendCounts, displayedCount, dataKey }: Props) {
  const pointToLayer: PointToLayerFn = (feature, latlng) => {
    const props = toRiskProps(feature?.properties);
    const level: RiskLevel =
      props?.risk_level === "high" || props?.risk_level === "medium" || props?.risk_level === "low"
        ? props.risk_level
        : "low";

    return L.circleMarker(latlng, {
      radius: 7,
      fillColor: RISK_COLORS[level],
      color: "#d1d5db",
      weight: 1,
      opacity: 0.9,
      fillOpacity: 0.9,
    });
  };

  const onEachFeature: OnEachFeatureFn = (feature, layer) => {
    if (!feature) {
      return;
    }
    const props = toRiskProps(feature.properties);
    if (!props) {
      return;
    }

    const level: RiskLevel =
      props.risk_level === "high" || props.risk_level === "medium" || props.risk_level === "low"
        ? props.risk_level
        : "low";

    const conditionLabel = props.condition_label ? sanitizeHtml(props.condition_label) : "No data";
    const stationName = props.name ? sanitizeHtml(props.name) : "Unknown station";
    const nearbyAlerts = props.nearby_alerts ?? 0;

    layer.bindPopup(
      `
      <div class="risk-popup-inner" style="border-left-color:${RISK_COLORS[level]}">
        <div class="risk-popup-title">${stationName}</div>
        <div class="risk-popup-score-row">
          <span class="risk-popup-score" style="color:${RISK_COLORS[level]}">${props.risk_score ?? "?"}/100</span>
          <span class="risk-popup-level">${level}</span>
        </div>
        <hr class="risk-popup-divider" />
        <div class="risk-popup-row"><span class="risk-popup-label">Surface</span><span class="risk-popup-value">${formatValue(props.surface_temp_c, "°C")}</span></div>
        <div class="risk-popup-row"><span class="risk-popup-label">Humidity</span><span class="risk-popup-value">${formatValue(props.humidity_pct, "%")}</span></div>
        <div class="risk-popup-row"><span class="risk-popup-label">Precip</span><span class="risk-popup-value">${formatValue(props.precip_mm, " mm")}</span></div>
        <div class="risk-popup-row"><span class="risk-popup-label">Road Condition</span><span class="risk-popup-value">${conditionLabel}</span></div>
        <div class="risk-popup-row"><span class="risk-popup-label">Nearby Alerts</span><span class="risk-popup-value">${nearbyAlerts}</span></div>
        <div class="risk-popup-meta">Data age: ${props.data_staleness_minutes ?? "?"} min</div>
      </div>
    `,
      { className: "risk-popup", maxWidth: 320 },
    );
  };

  return (
    <div className="relative h-full w-full">
      <MapContainer center={[62.5, 16.0]} zoom={5} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
        />
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png"
          className="map-labels-layer"
          opacity={1}
        />
        {geojson ? (
          <GeoJSON
            key={dataKey}
            data={geojson}
            pointToLayer={pointToLayer}
            onEachFeature={onEachFeature}
          />
        ) : null}
      </MapContainer>

      <aside className="pointer-events-none absolute bottom-6 left-6 z-[1000] max-w-xs rounded-lg border border-gray-700 bg-gray-900/90 p-4 text-sm text-white shadow-xl backdrop-blur-sm">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-gray-300">Risk Legend</h3>
        <ul className="space-y-2">
          {LEGEND_ITEMS.map((item) => (
            <li key={item.level} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 rounded-full ring-1 ring-white/30"
                  style={{ backgroundColor: RISK_COLORS[item.level] }}
                />
                <span>{item.label}</span>
              </div>
              <span className="text-gray-300">
                {item.range} ({legendCounts[item.level]})
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-3 border-t border-gray-700 pt-2 text-xs text-gray-400">
          Showing {displayedCount} station{displayedCount === 1 ? "" : "s"}
        </div>
      </aside>
    </div>
  );
}
