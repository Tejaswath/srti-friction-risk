#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
TOKEN="${2:-change_me_to_a_random_string}"

echo "[1/6] health"
curl -fsS "$API_URL/health" >/dev/null

echo "[2/6] geojson"
curl -fsS "$API_URL/risk/geojson" >/dev/null

echo "[3/6] geojson level filter"
curl -fsS "$API_URL/risk/geojson?level=high" >/dev/null

echo "[4/6] summary"
curl -fsS "$API_URL/risk/summary" >/dev/null

echo "[5/6] admin refresh unauth should be 403"
status_unauth=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/admin/refresh")
if [[ "$status_unauth" != "403" ]]; then
  echo "Expected 403, got $status_unauth"
  exit 1
fi

echo "[6/6] admin refresh auth"
curl -fsS -X POST "$API_URL/admin/refresh" -H "x-admin-token: $TOKEN" >/dev/null

echo "Smoke tests passed"
