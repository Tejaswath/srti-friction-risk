"use client";

import "leaflet/dist/leaflet.css";

import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import L from "leaflet";
import { useMemo } from "react";
import type { Feature, FeatureCollection, Point } from "geojson";

type Props = {
  geojson: FeatureCollection | null;
};

const RISK_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#eab308",
  low: "#22c55e",
};

type RiskFeatureProperties = {
  risk_level?: string;
  name?: string;
  risk_score?: number;
  surface_temp_c?: number | null;
  humidity_pct?: number | null;
  precip_mm?: number | null;
  condition_cause?: string | null;
  nearby_alerts?: number;
  data_staleness_minutes?: number | null;
};

type RiskFeature = Feature<Point, RiskFeatureProperties>;

export default function RiskMap({ geojson }: Props) {
  const mapKey = useMemo(() => JSON.stringify(geojson), [geojson]);

  const pointToLayer = (feature: RiskFeature | undefined, latlng: L.LatLng) => {
    const level = feature?.properties?.risk_level || "low";
    return L.circleMarker(latlng, {
      radius: 7,
      fillColor: RISK_COLORS[level] || RISK_COLORS.low,
      color: "#111827",
      weight: 1,
      opacity: 0.9,
      fillOpacity: 0.85,
    });
  };

  const onEachFeature = (feature: RiskFeature | undefined, layer: L.Layer) => {
    if (!feature) {
      return;
    }
    const props = feature.properties;
    if (!props) {
      return;
    }

    const scoreColor = RISK_COLORS[props.risk_level] || RISK_COLORS.low;
    layer.bindPopup(`
      <div style="font-family: sans-serif; font-size: 13px; line-height: 1.4; min-width: 180px;">
        <strong>${props.name}</strong><br />
        <span style="font-size: 20px; font-weight: 700; color: ${scoreColor};">${props.risk_score}/100</span>
        <span style="text-transform: uppercase; font-size: 11px; margin-left: 6px;">${props.risk_level}</span>
        <hr style="margin: 6px 0; border-color: #ddd;" />
        Surface: ${props.surface_temp_c ?? "N/A"}${props.surface_temp_c != null ? "°C" : ""}<br />
        Humidity: ${props.humidity_pct ?? "N/A"}${props.humidity_pct != null ? "%" : ""}<br />
        Precip: ${props.precip_mm ?? "N/A"}${props.precip_mm != null ? " mm" : ""}<br />
        ${props.condition_cause ? `Condition: ${props.condition_cause}<br />` : ""}
        ${props.nearby_alerts > 0 ? `Nearby alerts: ${props.nearby_alerts}<br />` : ""}
        <span style="color: #6b7280; font-size: 11px;">
          Data age: ${props.data_staleness_minutes ?? "?"} min
        </span>
      </div>
    `);
  };

  return (
    <MapContainer
      center={[62.5, 16.0]}
      zoom={5}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {geojson ? (
        <GeoJSON
          key={mapKey}
          data={geojson}
          pointToLayer={pointToLayer}
          onEachFeature={onEachFeature}
        />
      ) : null}
    </MapContainer>
  );
}
