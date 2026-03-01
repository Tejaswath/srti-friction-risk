# SRTI Friction Risk Microservice

Road friction risk estimation for Swedish roads using Trafikverket open data.

## Disclaimer

This system computes **risk estimates**, not physical friction measurements.
It combines weather observations, categorical road conditions, and situation alerts.

## Monorepo Layout

- `backend/` FastAPI ingestion + scoring service
- `frontend/` Next.js + Leaflet map UI
- `scripts/` local verification scripts
- `infra/azure/` Azure provisioning helper
- `frontend/figma-export/` handoff location for exported UI assets/code

## API Endpoints

- `GET /health`
- `GET /risk/geojson?bbox=min_lon,min_lat,max_lon,max_lat&level=low|medium|high`
- `GET /risk/summary`
- `POST /admin/refresh` with `x-admin-token`

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill TRAFIKVERKET_API_KEY and ADMIN_TOKEN
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Test Commands

Backend full suite:

```bash
./scripts/test_backend.sh
```

Backend smoke checks against running API:

```bash
./scripts/smoke_backend.sh http://localhost:8000 <admin-token>
```

## Test Coverage (current)

- Ingestion parsers and payload extraction
- Risk scoring component functions and stale-data handling
- GeoJSON response construction and filters
- API validation (`bbox`, `level`), summary aggregation, health fallback, admin auth path

## Deployment

### Azure backend

```bash
./infra/azure/deploy_backend.sh \
  "<subscription-id-or-name>" \
  "rg-srti-mvp-weu" \
  "swedencentral" \
  "asp-srti-mvp-b1" \
  "srti-friction-risk-api"
```

Then set app settings in Azure portal:

- `TRAFIKVERKET_API_KEY`
- `ADMIN_TOKEN`
- `ALLOWED_ORIGINS=https://<your-vercel-domain>`
- `CACHE_TTL_SECONDS=600`

### Vercel frontend

Set:

- `NEXT_PUBLIC_BACKEND_URL=https://<azure-app>.azurewebsites.net`

## Figma Handoff Contract

Drop exported UI in `frontend/figma-export/` and complete `frontend/figma-export/HANDOFF.md`.
Integration keeps data-fetching logic in existing app code and applies exported files only to presentation.

## License

MIT
