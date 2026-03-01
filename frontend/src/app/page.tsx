"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FeatureCollection, Point } from "geojson";

const RiskMap = dynamic(() => import("@/components/RiskMap"), { ssr: false });

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const AUTO_REFRESH_MS = 600_000;

type RiskLevel = "low" | "medium" | "high";

type Summary = {
  total_stations: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  avg_risk_score: number;
  last_refresh: string | null;
};

type RiskFeatureProperties = {
  station_id?: string;
  name?: string;
  risk_score?: number;
  risk_level?: RiskLevel;
  surface_temp_c?: number | null;
  humidity_pct?: number | null;
  precip_mm?: number | null;
  condition_cause?: string | null;
  condition_label?: string | null;
  nearby_alerts?: number;
  data_staleness_minutes?: number | null;
  computed_at?: string;
};

type RiskFeatureCollection = FeatureCollection<Point, RiskFeatureProperties>;

const formatTimestamp = (value?: string | null): string => {
  if (!value) {
    return new Date().toLocaleTimeString();
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return new Date().toLocaleTimeString();
  }
  return parsed.toLocaleTimeString();
};

const toRiskCounts = (collection: RiskFeatureCollection | null) => {
  const counts = { high: 0, medium: 0, low: 0 };
  if (!collection) {
    return counts;
  }

  for (const feature of collection.features) {
    const level = feature.properties?.risk_level;
    if (level === "high" || level === "medium" || level === "low") {
      counts[level] += 1;
    }
  }
  return counts;
};

export default function Home() {
  const [geojsonAll, setGeojsonAll] = useState<RiskFeatureCollection | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [levelFilter, setLevelFilter] = useState<"" | RiskLevel>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [geoRes, sumRes] = await Promise.all([
        fetch(`${BACKEND_URL}/risk/geojson`, { cache: "no-store" }),
        fetch(`${BACKEND_URL}/risk/summary`, { cache: "no-store" }),
      ]);

      if (!geoRes.ok || !sumRes.ok) {
        throw new Error(`Backend request failed (${geoRes.status}/${sumRes.status})`);
      }

      const geoData: RiskFeatureCollection = await geoRes.json();
      const sumData: Summary = await sumRes.json();

      setGeojsonAll(geoData);
      setSummary(sumData);
      setLastUpdated(formatTimestamp(sumData.last_refresh));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      fetchData();
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [fetchData]);

  const filteredGeojson = useMemo<RiskFeatureCollection | null>(() => {
    if (!geojsonAll) {
      return null;
    }
    if (!levelFilter) {
      return geojsonAll;
    }
    return {
      ...geojsonAll,
      features: geojsonAll.features.filter(
        (feature) => feature.properties?.risk_level === levelFilter,
      ),
    };
  }, [geojsonAll, levelFilter]);

  const filteredCounts = useMemo(() => toRiskCounts(filteredGeojson), [filteredGeojson]);
  const displayedCount = filteredGeojson?.features.length ?? 0;
  const totalCount = summary?.total_stations ?? 0;

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-[0.45em] text-gray-100">S R T I</h1>
            <p className="text-sm text-gray-400">Friction Risk Monitor</p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={`${BACKEND_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="rounded border border-gray-700 px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-gray-300 hover:border-gray-500 hover:text-white"
            >
              API Docs
            </a>
            <select
              value={levelFilter}
              onChange={(event) => setLevelFilter(event.target.value as "" | RiskLevel)}
              className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
            >
              <option value="">
                All levels{summary ? ` (${summary.total_stations})` : ""}
              </option>
              <option value="high">
                High risk only{summary ? ` (${summary.high_risk_count})` : ""}
              </option>
              <option value="medium">
                Medium risk only{summary ? ` (${summary.medium_risk_count})` : ""}
              </option>
              <option value="low">
                Low risk only{summary ? ` (${summary.low_risk_count})` : ""}
              </option>
            </select>
            <button
              onClick={fetchData}
              disabled={loading}
              className="rounded border border-blue-500/70 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-100 hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="border-b border-red-900 bg-red-950 px-6 py-3 text-sm text-red-200">
          <div className="mx-auto max-w-7xl">Data fetch error: {error}</div>
        </div>
      )}

      {summary && (
        <section className="border-b border-gray-800 px-6 py-3">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-3 md:grid-cols-5">
            <div className="border-r border-gray-800 pr-3 md:pr-4">
              <div className="text-2xl font-semibold text-gray-100">{summary.total_stations}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-gray-400">Stations</div>
            </div>
            <div className="border-r border-gray-800 pr-3 md:pr-4">
              <div className="text-2xl font-semibold text-red-400">{summary.high_risk_count}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-gray-400">High risk</div>
            </div>
            <div className="border-r border-gray-800 pr-3 md:pr-4">
              <div className="text-2xl font-semibold text-yellow-400">{summary.medium_risk_count}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-gray-400">Medium risk</div>
            </div>
            <div className="border-r border-gray-800 pr-3 md:pr-4">
              <div className="text-2xl font-semibold text-green-400">{summary.low_risk_count}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-gray-400">Low risk</div>
            </div>
            <div className="md:text-right">
              <div className="text-2xl font-semibold text-gray-100">{summary.avg_risk_score}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-gray-400">Avg score</div>
            </div>
          </div>
          <div className="mx-auto mt-3 flex max-w-7xl flex-wrap items-center justify-between gap-2 text-xs">
            <div className="text-gray-400">Updated: {lastUpdated || "—"}</div>
            {levelFilter ? (
              <div className="rounded border border-cyan-600/50 bg-cyan-900/20 px-2 py-1 text-cyan-200">
                Filtered view: {levelFilter} ({displayedCount} shown of {totalCount})
              </div>
            ) : (
              <div className="text-gray-500">Showing all stations</div>
            )}
          </div>
        </section>
      )}

      <div className="h-[calc(100vh-248px)] md:h-[calc(100vh-220px)]">
        <RiskMap
          geojson={filteredGeojson}
          legendCounts={filteredCounts}
          displayedCount={displayedCount}
        />
      </div>

      <div className="fixed bottom-0 left-0 right-0 border-t border-gray-800 bg-gray-900/90 px-4 py-2 text-center text-xs text-gray-400">
        Risk estimates are based on weather and categorical road condition data.
        This is not a direct friction measurement system.
      </div>
    </main>
  );
}
