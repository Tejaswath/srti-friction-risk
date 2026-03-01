"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

const RiskMap = dynamic(() => import("@/components/RiskMap"), { ssr: false });

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type Summary = {
  total_stations: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  avg_risk_score: number;
  last_refresh: string | null;
};

export default function Home() {
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [levelFilter, setLevelFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState("");

  const geojsonUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (levelFilter) {
      params.set("level", levelFilter);
    }
    const query = params.toString();
    return `${BACKEND_URL}/risk/geojson${query ? `?${query}` : ""}`;
  }, [levelFilter]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [geoRes, sumRes] = await Promise.all([
        fetch(geojsonUrl, { cache: "no-store" }),
        fetch(`${BACKEND_URL}/risk/summary`, { cache: "no-store" }),
      ]);

      if (!geoRes.ok || !sumRes.ok) {
        throw new Error(`Backend request failed (${geoRes.status}/${sumRes.status})`);
      }

      const geoData = await geoRes.json();
      const sumData = await sumRes.json();

      setGeojson(geoData);
      setSummary(sumData);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [geojsonUrl]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold">SRTI Friction Risk Map</h1>
            <p className="text-sm text-gray-400">
              Real-time road friction risk index for Swedish roads
            </p>
          </div>
          <div className="flex items-center gap-4">
            <select
              value={levelFilter}
              onChange={(event) => setLevelFilter(event.target.value)}
              className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
            >
              <option value="">All levels</option>
              <option value="high">High risk only</option>
              <option value="medium">Medium risk only</option>
              <option value="low">Low risk only</option>
            </select>
            <button
              onClick={fetchData}
              disabled={loading}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
            >
              {loading ? "Loading..." : "Refresh"}
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
        <div className="border-b border-gray-800 px-6 py-3">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-6 text-sm">
            <span className="text-gray-300">{summary.total_stations} stations</span>
            <span className="text-red-400">{summary.high_risk_count} high</span>
            <span className="text-yellow-400">{summary.medium_risk_count} medium</span>
            <span className="text-green-400">{summary.low_risk_count} low</span>
            <span className="text-gray-400">Avg score: {summary.avg_risk_score}</span>
            <span className="ml-auto text-xs text-gray-500">Updated: {lastUpdated}</span>
          </div>
        </div>
      )}

      <div className="h-[calc(100vh-128px)]">
        <RiskMap geojson={geojson} />
      </div>

      <div className="fixed bottom-0 left-0 right-0 border-t border-gray-800 bg-gray-900/90 px-4 py-2 text-center text-xs text-gray-400">
        Risk estimates are based on weather and categorical road condition data.
        This is not a direct friction measurement system.
      </div>
    </main>
  );
}
