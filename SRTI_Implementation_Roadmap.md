# SRTI Friction Risk Microservice — Full Implementation Roadmap

---

## What This Project Actually Is (Plain English)

Sweden has ~700 weather stations along its roads, operated by Trafikverket (the Swedish Transport Administration). These stations measure things like road surface temperature, air humidity, wind speed, and precipitation every 10 minutes. Separately, Trafikverket also publishes categorical road condition reports ("icy road," "snow-covered," "dry") and traffic situation alerts (accidents, hazards, roadwork).

**This project takes all three of those data streams, combines them, and computes a "friction risk score" for each measurement point on Swedish roads.** Think of it like a weather app, but instead of telling you "it's 28°F outside," it tells you "this stretch of road has a 78/100 slippery risk right now." The results are displayed on a live interactive map of Sweden where you can see red/yellow/green zones.

**Important honesty note:** We are NOT measuring actual friction coefficients (that requires specialized hardware on cars). We are estimating *risk* based on publicly available weather and condition data. This distinction matters and actually makes the project more interesting — it lets you talk about the data gap and how Volvo's fleet sensors fill it.

### Why This Is Useful For Your Volvo Application

Volvo Cars literally built a system that does the *vehicle side* of this exact problem. Their "Slippery Road Alert" feature uses fleet-wide ABS/ESC activations to detect when cars lose traction, then warns other Volvos nearby. They piloted it with Trafikverket in 2014 using 50 test cars.

Your project builds the *road authority side* — processing government sensor data to estimate where roads are dangerous. This makes you someone who understands the full ecosystem, not just the code. When you walk into an interview, you can say: "Volvo's Connected Safety detects friction from the vehicle. I built a system that detects friction risk from the infrastructure. Together, they create the complete picture."

It also connects to the EU's SRTI Directive, the DFRS consortium (where Volvo is a member alongside BMW, Ford, and Mercedes), and Euro NCAP 2026 requirements. This signals that you understand the regulatory world Volvo operates in.

---

## SECTION A — Pre-Flight Decisions

| Decision | Choice | Justification |
|----------|--------|---------------|
| Backend framework | **FastAPI** (Python) | Async-native, auto-generates OpenAPI docs, perfect for data-processing microservices. |
| Frontend framework | **Next.js 14** (TypeScript) | Deploys natively on Vercel with zero config, supports both SSR and client-side rendering. |
| Map library | **Leaflet.js** | Free, no API key required, lighter than Mapbox, sufficient for an MVP demo. |
| Backend host | **Render** (free tier) | Free web services with Docker support, auto-deploy from GitHub, free TLS. Sleeps after 15 min inactivity on free tier (acceptable for a portfolio demo). |
| Redis in MVP? | **No** | Use Python `cachetools.TTLCache` (in-memory with expiry). Keeps deployment simple. Document the limitation that cache resets on restart. |
| Database | **None for MVP** | All data is fetched live from Trafikverket and cached in-memory. No persistence needed. |

---

## SECTION B — Repo and VS Code Setup

### B.1 — Create the repository

```bash
mkdir srti-friction-risk && cd srti-friction-risk
git init
```

### B.2 — Folder structure

```
srti-friction-risk/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── models.py            # Pydantic data models
│   │   ├── ingestion.py         # Trafikverket API clients
│   │   ├── scoring.py           # Friction risk scoring engine
│   │   └── geojson_builder.py   # GeoJSON response construction
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_ingestion.py
│   │   ├── test_scoring.py
│   │   └── test_api.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── (Next.js app — created via create-next-app)
│   └── .env.example
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

### B.3 — Backend Python setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

cat > requirements.txt << 'EOF'
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic==2.10.4
pydantic-settings==2.7.1
cachetools==5.5.1
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.25.0
EOF

pip install -r requirements.txt
```

### B.4 — Frontend setup

```bash
cd ../frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-import-alias

npm install leaflet react-leaflet @types/leaflet
```

### B.5 — Git ignore

```bash
cd ..
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
.pytest_cache/

# Node
node_modules/
.next/
out/

# Env
.env
.env.local

# IDE
.vscode/settings.json
.idea/
*.swp
EOF
```

### B.6 — VS Code settings (optional but helpful)

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "ms-azuretools.vscode-docker"
  ]
}
```

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Backend",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    }
  ]
}
```

---

## SECTION C — Environment Variables and Secrets

### C.1 — Backend `.env.example`

```bash
# backend/.env.example

# REQUIRED — Trafikverket API authentication key
# Get yours free at: https://api.trafikinfo.trafikverket.se (register → "Min sida" → create key)
# OR via Trafiklab: https://trafiklab.se (register → create project → add "Trafikverket" API)
TRAFIKVERKET_API_KEY=your_key_here

# OPTIONAL — Admin refresh endpoint protection
ADMIN_TOKEN=change_me_to_a_random_string

# OPTIONAL — CORS allowed origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app

# OPTIONAL — Cache TTL in seconds (default 600 = 10 minutes)
CACHE_TTL_SECONDS=600
```

### C.2 — Frontend `.env.example`

```bash
# frontend/.env.example

# Public — exposed to browser (NEXT_PUBLIC_ prefix required)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# No server-only secrets needed for frontend MVP
```

### C.3 — Vercel environment variables

| Variable | Visibility | Value |
|----------|-----------|-------|
| `NEXT_PUBLIC_BACKEND_URL` | Public (prefixed) | `https://your-backend.onrender.com` |

### C.4 — Render environment variables

| Variable | Value |
|----------|-------|
| `TRAFIKVERKET_API_KEY` | Your actual API key |
| `ADMIN_TOKEN` | A random string |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` |

### C.5 — How to get your Trafikverket API key

1. Go to `https://api.trafikinfo.trafikverket.se`
2. Click "Registrera" (Register) — requires only an email address
3. Confirm your email
4. Log in → "Min sida" (My Page) → Create a new API key
5. Copy the key into your `.env` file

**Alternative via Trafiklab:**
1. Go to `https://trafiklab.se`
2. Register (can use GitHub login)
3. Create a project → Add the "Trafikverket öppet API" key
4. Copy the key

**Test it immediately:**

```bash
curl -X POST https://api.trafikinfo.trafikverket.se/v2/data.json \
  -H "Content-Type: text/xml" \
  -d '<REQUEST>
        <LOGIN authenticationkey="YOUR_KEY_HERE"/>
        <QUERY objecttype="WeatherMeasurepoint" schemaversion="2" limit="1">
          <INCLUDE>Name</INCLUDE>
          <INCLUDE>Geometry.WGS84</INCLUDE>
        </QUERY>
      </REQUEST>'
```

You should get a JSON response with one weather station name and coordinates. If you get an auth error, your key is wrong.

---

## SECTION D — Data Ingestion MVP

### D.1 — API query templates

All three data sources use the same Trafikverket v2 endpoint. You send an XML POST body and get JSON back.

**Endpoint:** `https://api.trafikinfo.trafikverket.se/v2/data.json`
**Method:** POST
**Content-Type:** `text/xml`

#### WeatherMeasurepoint (schemaversion 2)

```xml
<REQUEST>
  <LOGIN authenticationkey="{api_key}"/>
  <QUERY objecttype="WeatherMeasurepoint" schemaversion="2" limit="500">
    <INCLUDE>Id</INCLUDE>
    <INCLUDE>Name</INCLUDE>
    <INCLUDE>Geometry.WGS84</INCLUDE>
    <INCLUDE>Observation.Sample</INCLUDE>
    <INCLUDE>Observation.Air.Temperature.Value</INCLUDE>
    <INCLUDE>Observation.Air.RelativeHumidity.Value</INCLUDE>
    <INCLUDE>Observation.Surface.Temperature.Value</INCLUDE>
    <INCLUDE>Observation.Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value</INCLUDE>
    <INCLUDE>Observation.Wind.Speed.Value</INCLUDE>
    <INCLUDE>ModifiedTime</INCLUDE>
  </QUERY>
</REQUEST>
```

**Key fields returned:**
- `Observation.Surface.Temperature.Value` — Road surface temp (°C). Below 0 = freezing risk.
- `Observation.Air.RelativeHumidity.Value` — Humidity (%). Above 85% with cold = frost risk.
- `Observation.Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value` — Rain/snow (mm).
- `Geometry.WGS84` — GPS coordinates as WKT string: `"POINT (18.0563 59.3293)"`

#### RoadCondition (schemaversion 1.2)

```xml
<REQUEST>
  <LOGIN authenticationkey="{api_key}"/>
  <QUERY objecttype="RoadCondition" schemaversion="1.2" limit="500">
    <INCLUDE>Id</INCLUDE>
    <INCLUDE>RoadNumberNumeric</INCLUDE>
    <INCLUDE>Cause</INCLUDE>
    <INCLUDE>ConditionText</INCLUDE>
    <INCLUDE>Geometry.WGS84</INCLUDE>
    <INCLUDE>MeasurementTime</INCLUDE>
    <INCLUDE>ModifiedTime</INCLUDE>
  </QUERY>
</REQUEST>
```

**Key fields:** `Cause` contains categorical values like these (in Swedish):
- `Belagd med is och snö` — Covered with ice and snow
- `Ishalka` — Icy/slippery
- `Torr väg` — Dry road
- `Våt väg` — Wet road
- `Rimfrost` — Frost

#### Situation (schemaversion 1.5)

```xml
<REQUEST>
  <LOGIN authenticationkey="{api_key}"/>
  <QUERY objecttype="Situation" schemaversion="1.5" limit="200">
    <INCLUDE>Id</INCLUDE>
    <INCLUDE>Deviation.MessageType</INCLUDE>
    <INCLUDE>Deviation.SituationType</INCLUDE>
    <INCLUDE>Deviation.Geometry.WGS84</INCLUDE>
    <INCLUDE>Deviation.Header</INCLUDE>
    <INCLUDE>Deviation.StartTime</INCLUDE>
    <INCLUDE>Deviation.EndTime</INCLUDE>
    <INCLUDE>ModifiedTime</INCLUDE>
    <FILTER>
      <OR>
        <LIKE name="Deviation.SituationType" value="/Olycka/"/>
        <LIKE name="Deviation.SituationType" value="/Halka/"/>
        <LIKE name="Deviation.SituationType" value="/Väglag/"/>
      </OR>
    </FILTER>
  </QUERY>
</REQUEST>
```

**Note:** The Situation filter above targets accident, slippery, and road condition alerts. Adjust or remove the filter if you want all situations initially — you can always filter in code later.

### D.2 — Config module

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    trafikverket_api_key: str
    admin_token: str = "default-dev-token"
    allowed_origins: str = "http://localhost:3000"
    cache_ttl_seconds: int = 600

    class Config:
        env_file = ".env"

settings = Settings()
```

### D.3 — Pydantic data models (canonical internal schema)

```python
# backend/app/models.py
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

# --- Internal canonical models ---

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class WeatherPoint(BaseModel):
    """Normalized weather observation from a single measurement point."""
    station_id: str
    name: str
    lat: float
    lon: float
    air_temp_c: Optional[float] = None
    surface_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    precip_mm: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    observed_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

class RoadConditionPoint(BaseModel):
    """Normalized road condition report for a road segment."""
    condition_id: str
    road_number: Optional[int] = None
    cause: Optional[str] = None          # e.g., "Ishalka", "Torr väg"
    condition_text: Optional[str] = None
    lat: float
    lon: float
    measured_at: Optional[datetime] = None

class SituationAlert(BaseModel):
    """Normalized traffic situation/deviation alert."""
    situation_id: str
    message_type: Optional[str] = None
    situation_type: Optional[str] = None
    header: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class FrictionRiskPoint(BaseModel):
    """Final computed risk for a geographic point."""
    station_id: str
    name: str
    lat: float
    lon: float
    risk_score: int              # 0-100
    risk_level: RiskLevel        # low / medium / high
    surface_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    precip_mm: Optional[float] = None
    condition_cause: Optional[str] = None
    nearby_alerts: int = 0
    data_staleness_minutes: Optional[int] = None
    computed_at: datetime

# --- API response models ---

class HealthResponse(BaseModel):
    status: str
    stations_cached: int
    last_refresh: Optional[datetime] = None

class SummaryResponse(BaseModel):
    total_stations: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    avg_risk_score: float
    last_refresh: Optional[datetime] = None
```

### D.4 — Ingestion client

```python
# backend/app/ingestion.py
import httpx
import re
import logging
from datetime import datetime
from typing import Optional
from cachetools import TTLCache
from app.config import settings
from app.models import WeatherPoint, RoadConditionPoint, SituationAlert

logger = logging.getLogger(__name__)

API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# In-memory caches (TTL = configurable, default 10 min)
_weather_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)
_condition_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)
_situation_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)

def _parse_wgs84(wkt: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """Parse WKT 'POINT (lon lat)' into (lat, lon). Returns (None, None) on failure."""
    if not wkt:
        return None, None
    match = re.search(r"POINT\s*\(\s*([\d.\-]+)\s+([\d.\-]+)\s*\)", wkt)
    if match:
        lon, lat = float(match.group(1)), float(match.group(2))
        return lat, lon
    return None, None

def _safe_float(obj: dict, *keys) -> Optional[float]:
    """Safely traverse nested dict keys and return float or None."""
    current = obj
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    try:
        return float(current) if current is not None else None
    except (ValueError, TypeError):
        return None

def _safe_str(obj: dict, key: str) -> Optional[str]:
    val = obj.get(key)
    return str(val) if val is not None else None

def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

async def _post_trafikverket(xml_body: str) -> dict:
    """Send POST to Trafikverket v2 API and return parsed JSON."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            API_URL,
            content=xml_body.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
        )
        resp.raise_for_status()
        return resp.json()

# ---------- Weather ----------

async def fetch_weather() -> list[WeatherPoint]:
    """Fetch all WeatherMeasurepoint data. Returns cached if fresh."""
    if "data" in _weather_cache:
        return _weather_cache["data"]

    xml = f"""<REQUEST>
      <LOGIN authenticationkey="{settings.trafikverket_api_key}"/>
      <QUERY objecttype="WeatherMeasurepoint" schemaversion="2" limit="500">
        <INCLUDE>Id</INCLUDE>
        <INCLUDE>Name</INCLUDE>
        <INCLUDE>Geometry.WGS84</INCLUDE>
        <INCLUDE>Observation.Sample</INCLUDE>
        <INCLUDE>Observation.Air.Temperature.Value</INCLUDE>
        <INCLUDE>Observation.Air.RelativeHumidity.Value</INCLUDE>
        <INCLUDE>Observation.Surface.Temperature.Value</INCLUDE>
        <INCLUDE>Observation.Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value</INCLUDE>
        <INCLUDE>Observation.Wind.Speed.Value</INCLUDE>
        <INCLUDE>ModifiedTime</INCLUDE>
      </QUERY>
    </REQUEST>"""

    data = await _post_trafikverket(xml)
    results = data.get("RESPONSE", {}).get("RESULT", [{}])[0].get("WeatherMeasurepoint", [])
    points = []

    for r in results:
        obs = r.get("Observation", {}) or {}
        geom = r.get("Geometry", {}) or {}
        lat, lon = _parse_wgs84(geom.get("WGS84"))
        if lat is None or lon is None:
            continue

        points.append(WeatherPoint(
            station_id=str(r.get("Id", "")),
            name=r.get("Name", "Unknown"),
            lat=lat,
            lon=lon,
            air_temp_c=_safe_float(obs, "Air", "Temperature", "Value"),
            surface_temp_c=_safe_float(obs, "Surface", "Temperature", "Value"),
            humidity_pct=_safe_float(obs, "Air", "RelativeHumidity", "Value"),
            precip_mm=_safe_float(obs, "Aggregated10minutes", "Precipitation",
                                  "TotalWaterEquivalent", "Value"),
            wind_speed_ms=_safe_float(obs, "Wind", "Speed", "Value"),
            observed_at=_parse_dt(obs.get("Sample")),
            modified_at=_parse_dt(r.get("ModifiedTime")),
        ))

    _weather_cache["data"] = points
    logger.info(f"Fetched {len(points)} weather points")
    return points

# ---------- Road Condition ----------

async def fetch_road_conditions() -> list[RoadConditionPoint]:
    """Fetch all RoadCondition data. Returns cached if fresh."""
    if "data" in _condition_cache:
        return _condition_cache["data"]

    xml = f"""<REQUEST>
      <LOGIN authenticationkey="{settings.trafikverket_api_key}"/>
      <QUERY objecttype="RoadCondition" schemaversion="1.2" limit="500">
        <INCLUDE>Id</INCLUDE>
        <INCLUDE>RoadNumberNumeric</INCLUDE>
        <INCLUDE>Cause</INCLUDE>
        <INCLUDE>ConditionText</INCLUDE>
        <INCLUDE>Geometry.WGS84</INCLUDE>
        <INCLUDE>MeasurementTime</INCLUDE>
        <INCLUDE>ModifiedTime</INCLUDE>
      </QUERY>
    </REQUEST>"""

    data = await _post_trafikverket(xml)
    results = data.get("RESPONSE", {}).get("RESULT", [{}])[0].get("RoadCondition", [])
    points = []

    for r in results:
        geom = r.get("Geometry", {}) or {}
        lat, lon = _parse_wgs84(geom.get("WGS84"))
        if lat is None or lon is None:
            continue

        road_num = r.get("RoadNumberNumeric")
        points.append(RoadConditionPoint(
            condition_id=str(r.get("Id", "")),
            road_number=int(road_num) if road_num else None,
            cause=_safe_str(r, "Cause"),
            condition_text=_safe_str(r, "ConditionText"),
            lat=lat,
            lon=lon,
            measured_at=_parse_dt(r.get("MeasurementTime")),
        ))

    _condition_cache["data"] = points
    logger.info(f"Fetched {len(points)} road condition reports")
    return points

# ---------- Situation ----------

async def fetch_situations() -> list[SituationAlert]:
    """Fetch active traffic situations. Returns cached if fresh."""
    if "data" in _situation_cache:
        return _situation_cache["data"]

    xml = f"""<REQUEST>
      <LOGIN authenticationkey="{settings.trafikverket_api_key}"/>
      <QUERY objecttype="Situation" schemaversion="1.5" limit="200">
        <INCLUDE>Id</INCLUDE>
        <INCLUDE>Deviation.MessageType</INCLUDE>
        <INCLUDE>Deviation.SituationType</INCLUDE>
        <INCLUDE>Deviation.Geometry.WGS84</INCLUDE>
        <INCLUDE>Deviation.Header</INCLUDE>
        <INCLUDE>Deviation.StartTime</INCLUDE>
        <INCLUDE>Deviation.EndTime</INCLUDE>
        <INCLUDE>ModifiedTime</INCLUDE>
      </QUERY>
    </REQUEST>"""

    data = await _post_trafikverket(xml)
    results = data.get("RESPONSE", {}).get("RESULT", [{}])[0].get("Situation", [])
    alerts = []

    for r in results:
        devs = r.get("Deviation", [])
        if isinstance(devs, dict):
            devs = [devs]
        for dev in devs:
            geom = dev.get("Geometry", {}) or {}
            lat, lon = _parse_wgs84(geom.get("WGS84"))
            alerts.append(SituationAlert(
                situation_id=str(r.get("Id", "")),
                message_type=dev.get("MessageType"),
                situation_type=dev.get("SituationType"),
                header=dev.get("Header"),
                lat=lat,
                lon=lon,
                start_time=_parse_dt(dev.get("StartTime")),
                end_time=_parse_dt(dev.get("EndTime")),
            ))

    _situation_cache["data"] = alerts
    logger.info(f"Fetched {len(alerts)} situation alerts")
    return alerts

# ---------- Cache management ----------

def clear_all_caches():
    _weather_cache.clear()
    _condition_cache.clear()
    _situation_cache.clear()
```

### D.5 — Cache strategy and limitations

The MVP uses `cachetools.TTLCache` with a configurable TTL (default 10 minutes, matching Trafikverket's update interval).

**Limitations to document in README:**
- Cache is in-memory — resets when the server restarts
- On Render free tier, the server sleeps after 15 min of inactivity; first request after sleep will be slow (~30s cold start + API fetch)
- No cache sharing between multiple server instances (irrelevant for MVP single-instance deployment)
- If the Trafikverket API is down, stale cache expires and subsequent requests will fail

---

## SECTION E — Risk Scoring MVP

### E.1 — Scoring philosophy

The friction risk score combines four independent signals into a 0–100 composite score:

| Signal | Weight | Logic |
|--------|--------|-------|
| **Surface temperature** | 35% | Below 0°C is danger zone. Colder = higher risk. |
| **Precipitation** | 25% | Any precipitation with cold temps dramatically increases risk. |
| **Humidity** | 15% | Above 85% with sub-zero surface temp = frost/black ice risk. |
| **Road condition category** | 25% | Direct categorical boost: "Ishalka" = high, "Torr väg" = none. |

Nearby situation alerts add a bonus of +5 points per alert (capped at +15).

Time-decay: data older than 60 minutes is penalized (score reduced by 20%). Data older than 120 minutes gets a 50% penalty. Data older than 180 minutes is marked stale and excluded.

### E.2 — Risk label thresholds

| Score | Label |
|-------|-------|
| 0–30 | `low` (green) |
| 31–60 | `medium` (yellow) |
| 61–100 | `high` (red) |

### E.3 — Implementation

```python
# backend/app/scoring.py
import math
from datetime import datetime, timezone
from typing import Optional
from app.models import (
    WeatherPoint, RoadConditionPoint, SituationAlert,
    FrictionRiskPoint, RiskLevel,
)

# --- Condition cause mapping (Swedish → risk multiplier 0.0-1.0) ---
CONDITION_RISK_MAP: dict[str, float] = {
    # High risk
    "ishalka": 1.0,
    "belagd med is och snö": 0.95,
    "snöhalka": 0.9,
    "rimfrost": 0.8,
    "spårigt": 0.7,
    # Medium risk
    "våt väg": 0.4,
    "fuktigt väglag": 0.35,
    "delvis isbelagd": 0.75,
    # Low risk
    "torr väg": 0.0,
    "bar väg": 0.0,
}

def _match_condition_risk(cause: Optional[str]) -> float:
    """Fuzzy-match a Swedish condition cause string to a risk value."""
    if not cause:
        return 0.0
    cause_lower = cause.lower().strip()
    for key, val in CONDITION_RISK_MAP.items():
        if key in cause_lower:
            return val
    # Unknown condition — assume moderate
    return 0.3

def _surface_temp_score(temp_c: Optional[float]) -> float:
    """Score 0.0-1.0 based on road surface temperature. Sub-zero is dangerous."""
    if temp_c is None:
        return 0.3  # Unknown — assume moderate
    if temp_c > 5.0:
        return 0.0
    if temp_c > 2.0:
        return 0.15
    if temp_c > 0.0:
        return 0.5
    if temp_c > -3.0:
        return 0.75
    if temp_c > -10.0:
        return 0.9
    return 1.0  # Extreme cold

def _precip_score(precip_mm: Optional[float], surface_temp_c: Optional[float]) -> float:
    """Precipitation risk. Especially dangerous when combined with sub-zero temps."""
    if precip_mm is None or precip_mm <= 0.0:
        return 0.0
    base = min(precip_mm / 3.0, 1.0)  # Normalize: 3mm+ = max
    # Amplify if freezing
    if surface_temp_c is not None and surface_temp_c <= 0.0:
        base = min(base * 1.5, 1.0)
    return base

def _humidity_score(humidity_pct: Optional[float], surface_temp_c: Optional[float]) -> float:
    """High humidity + cold surface = frost/black ice."""
    if humidity_pct is None:
        return 0.1
    if humidity_pct < 70:
        return 0.0
    if humidity_pct < 85:
        factor = 0.2
    else:
        factor = 0.6
    # Only dangerous if surface is near or below freezing
    if surface_temp_c is not None and surface_temp_c > 3.0:
        factor *= 0.3
    return min(factor, 1.0)

def _time_decay_factor(observed_at: Optional[datetime]) -> float:
    """Returns a multiplier 0.0-1.0 based on data freshness."""
    if observed_at is None:
        return 0.5  # Unknown age — penalize somewhat
    now = datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        # Assume UTC if naive
        from datetime import timezone as tz
        observed_at = observed_at.replace(tzinfo=tz.utc)
    age_minutes = (now - observed_at).total_seconds() / 60.0
    if age_minutes < 0:
        age_minutes = 0
    if age_minutes <= 30:
        return 1.0
    if age_minutes <= 60:
        return 0.9
    if age_minutes <= 120:
        return 0.7
    if age_minutes <= 180:
        return 0.5
    return 0.0  # Too stale — effectively discard

def _count_nearby_alerts(
    lat: float, lon: float,
    alerts: list[SituationAlert],
    radius_deg: float = 0.15,  # ~15 km rough approximation
) -> int:
    """Count situation alerts within a rough bounding box."""
    count = 0
    for a in alerts:
        if a.lat is None or a.lon is None:
            continue
        if abs(a.lat - lat) < radius_deg and abs(a.lon - lon) < radius_deg:
            count += 1
    return count

def compute_risk(
    weather: WeatherPoint,
    conditions: list[RoadConditionPoint],
    alerts: list[SituationAlert],
) -> FrictionRiskPoint:
    """Compute the composite friction risk score for a single weather station."""

    # 1. Find nearest road condition report (simple distance)
    nearest_condition: Optional[RoadConditionPoint] = None
    min_dist = float("inf")
    for c in conditions:
        dist = math.hypot(c.lat - weather.lat, c.lon - weather.lon)
        if dist < min_dist and dist < 0.2:  # ~20km threshold
            min_dist = dist
            nearest_condition = c

    # 2. Component scores (each 0.0 - 1.0)
    temp_s = _surface_temp_score(weather.surface_temp_c)
    precip_s = _precip_score(weather.precip_mm, weather.surface_temp_c)
    humid_s = _humidity_score(weather.humidity_pct, weather.surface_temp_c)
    cond_s = _match_condition_risk(nearest_condition.cause if nearest_condition else None)

    # 3. Weighted composite (0.0 - 1.0)
    W_TEMP, W_PRECIP, W_HUMID, W_COND = 0.35, 0.25, 0.15, 0.25
    raw = (temp_s * W_TEMP) + (precip_s * W_PRECIP) + (humid_s * W_HUMID) + (cond_s * W_COND)

    # 4. Alert bonus
    nearby = _count_nearby_alerts(weather.lat, weather.lon, alerts)
    alert_bonus = min(nearby * 0.05, 0.15)  # +5 per alert, cap +15
    raw = min(raw + alert_bonus, 1.0)

    # 5. Time decay
    decay = _time_decay_factor(weather.observed_at)
    if decay == 0.0:
        # Data too stale — return minimum risk with warning
        score = 0
    else:
        score = round(raw * decay * 100)
    score = max(0, min(100, score))

    # 6. Label
    if score <= 30:
        level = RiskLevel.LOW
    elif score <= 60:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.HIGH

    # 7. Staleness info
    staleness = None
    if weather.observed_at:
        now = datetime.now(timezone.utc)
        obs = weather.observed_at
        if obs.tzinfo is None:
            obs = obs.replace(tzinfo=timezone.utc)
        staleness = round((now - obs).total_seconds() / 60.0)

    return FrictionRiskPoint(
        station_id=weather.station_id,
        name=weather.name,
        lat=weather.lat,
        lon=weather.lon,
        risk_score=score,
        risk_level=level,
        surface_temp_c=weather.surface_temp_c,
        humidity_pct=weather.humidity_pct,
        precip_mm=weather.precip_mm,
        condition_cause=nearest_condition.cause if nearest_condition else None,
        nearby_alerts=nearby,
        data_staleness_minutes=staleness,
        computed_at=datetime.now(timezone.utc),
    )

async def compute_all_risks(
    weather_points: list[WeatherPoint],
    conditions: list[RoadConditionPoint],
    alerts: list[SituationAlert],
) -> list[FrictionRiskPoint]:
    """Score all weather stations."""
    return [compute_risk(w, conditions, alerts) for w in weather_points]
```

---

## SECTION F — FastAPI Backend (Endpoints)

### F.1 — GeoJSON builder

```python
# backend/app/geojson_builder.py
from typing import Optional
from app.models import FrictionRiskPoint

def build_geojson(
    risk_points: list[FrictionRiskPoint],
    bbox: Optional[tuple[float, float, float, float]] = None,
    level_filter: Optional[str] = None,
) -> dict:
    """Build a GeoJSON FeatureCollection from risk points."""
    features = []
    for p in risk_points:
        # BBox filter: (min_lon, min_lat, max_lon, max_lat)
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            if not (min_lat <= p.lat <= max_lat and min_lon <= p.lon <= max_lon):
                continue
        # Level filter
        if level_filter and p.risk_level.value != level_filter:
            continue

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [p.lon, p.lat],
            },
            "properties": {
                "station_id": p.station_id,
                "name": p.name,
                "risk_score": p.risk_score,
                "risk_level": p.risk_level.value,
                "surface_temp_c": p.surface_temp_c,
                "humidity_pct": p.humidity_pct,
                "precip_mm": p.precip_mm,
                "condition_cause": p.condition_cause,
                "nearby_alerts": p.nearby_alerts,
                "data_staleness_minutes": p.data_staleness_minutes,
                "computed_at": p.computed_at.isoformat(),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
```

### F.2 — Main FastAPI application

```python
# backend/app/main.py
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import HealthResponse, SummaryResponse
from app.ingestion import (
    fetch_weather, fetch_road_conditions, fetch_situations,
    clear_all_caches,
)
from app.scoring import compute_all_risks
from app.geojson_builder import build_geojson

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SRTI Friction Risk Microservice",
    description=(
        "Real-time road friction risk scoring for Swedish roads. "
        "Based on Trafikverket weather, road condition, and situation data. "
        "NOT a friction measurement system — this computes risk scores from "
        "publicly available weather and categorical condition data."
    ),
    version="1.0.0",
)

# CORS
origins = [o.strip() for o in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Shared state ---
_last_refresh: Optional[datetime] = None

async def _get_risk_data():
    """Fetch all data and compute risk scores."""
    global _last_refresh
    weather = await fetch_weather()
    conditions = await fetch_road_conditions()
    alerts = await fetch_situations()
    risks = await compute_all_risks(weather, conditions, alerts)
    _last_refresh = datetime.now(timezone.utc)
    return risks

# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    try:
        weather = await fetch_weather()
        return HealthResponse(
            status="ok",
            stations_cached=len(weather),
            last_refresh=_last_refresh,
        )
    except Exception as e:
        return HealthResponse(
            status=f"degraded: {str(e)[:100]}",
            stations_cached=0,
            last_refresh=_last_refresh,
        )

@app.get("/risk/geojson")
async def get_risk_geojson(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box: min_lon,min_lat,max_lon,max_lat",
        example="11.0,55.0,24.0,69.5",
    ),
    level: Optional[str] = Query(
        None,
        description="Filter by risk level: low, medium, high",
        example="high",
    ),
):
    """Return GeoJSON FeatureCollection of friction risk points."""
    parsed_bbox = None
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            parsed_bbox = tuple(parts)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat",
            )

    if level and level not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="level must be low, medium, or high")

    risks = await _get_risk_data()
    geojson = build_geojson(risks, bbox=parsed_bbox, level_filter=level)
    return geojson

@app.get("/risk/summary", response_model=SummaryResponse)
async def get_risk_summary(
    region: Optional[str] = Query(None, description="(Reserved for future use)"),
):
    """Return aggregate risk statistics."""
    risks = await _get_risk_data()
    if not risks:
        return SummaryResponse(
            total_stations=0, high_risk_count=0,
            medium_risk_count=0, low_risk_count=0,
            avg_risk_score=0.0, last_refresh=_last_refresh,
        )
    return SummaryResponse(
        total_stations=len(risks),
        high_risk_count=sum(1 for r in risks if r.risk_level.value == "high"),
        medium_risk_count=sum(1 for r in risks if r.risk_level.value == "medium"),
        low_risk_count=sum(1 for r in risks if r.risk_level.value == "low"),
        avg_risk_score=round(sum(r.risk_score for r in risks) / len(risks), 1),
        last_refresh=_last_refresh,
    )

@app.post("/admin/refresh")
async def admin_refresh(
    x_admin_token: Optional[str] = Header(None),
):
    """Force-refresh all cached data. Protected by admin token."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    clear_all_caches()
    risks = await _get_risk_data()
    return {"status": "refreshed", "stations": len(risks)}
```

### F.3 — Example responses

**GET /health**
```json
{
  "status": "ok",
  "stations_cached": 687,
  "last_refresh": "2026-03-01T14:30:00Z"
}
```

**GET /risk/geojson?level=high** (truncated)
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [18.056, 59.329] },
      "properties": {
        "station_id": "1234",
        "name": "Kungälv",
        "risk_score": 78,
        "risk_level": "high",
        "surface_temp_c": -4.2,
        "humidity_pct": 92.0,
        "precip_mm": 1.3,
        "condition_cause": "Ishalka",
        "nearby_alerts": 2,
        "data_staleness_minutes": 7,
        "computed_at": "2026-03-01T14:30:00Z"
      }
    }
  ]
}
```

**GET /risk/summary**
```json
{
  "total_stations": 687,
  "high_risk_count": 42,
  "medium_risk_count": 198,
  "low_risk_count": 447,
  "avg_risk_score": 31.4,
  "last_refresh": "2026-03-01T14:30:00Z"
}
```

---

## SECTION G — Frontend MVP (Next.js on Vercel)

### G.1 — Key files to create/modify

After running `create-next-app`, create or modify these files:

#### `frontend/src/app/page.tsx` — Main page

```tsx
"use client";

import dynamic from "next/dynamic";
import { useState, useEffect, useCallback } from "react";

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
  const [geojson, setGeojson] = useState<any>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [levelFilter, setLevelFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const levelParam = levelFilter ? `?level=${levelFilter}` : "";
      const [geoRes, sumRes] = await Promise.all([
        fetch(`${BACKEND_URL}/risk/geojson${levelParam}`),
        fetch(`${BACKEND_URL}/risk/summary`),
      ]);
      const geoData = await geoRes.json();
      const sumData = await sumRes.json();
      setGeojson(geoData);
      setSummary(sumData);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  }, [levelFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">SRTI Friction Risk Map</h1>
            <p className="text-sm text-gray-400">
              Real-time road friction risk index — Swedish roads
            </p>
          </div>
          <div className="flex items-center gap-4">
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
            >
              <option value="">All levels</option>
              <option value="high">🔴 High risk only</option>
              <option value="medium">🟡 Medium risk only</option>
              <option value="low">🟢 Low risk only</option>
            </select>
            <button
              onClick={fetchData}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-1.5 rounded text-sm font-medium"
            >
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>
      </header>

      {/* Stats bar */}
      {summary && (
        <div className="border-b border-gray-800 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-6 text-sm">
            <span className="text-gray-400">
              {summary.total_stations} stations
            </span>
            <span className="text-red-400">
              🔴 {summary.high_risk_count} high
            </span>
            <span className="text-yellow-400">
              🟡 {summary.medium_risk_count} medium
            </span>
            <span className="text-green-400">
              🟢 {summary.low_risk_count} low
            </span>
            <span className="text-gray-500">
              Avg score: {summary.avg_risk_score}
            </span>
            <span className="ml-auto text-gray-500 text-xs">
              Updated: {lastUpdated}
            </span>
          </div>
        </div>
      )}

      {/* Map */}
      <div className="h-[calc(100vh-120px)]">
        <RiskMap geojson={geojson} />
      </div>

      {/* Disclaimer */}
      <div className="fixed bottom-0 left-0 right-0 bg-gray-900/90 border-t border-gray-800 px-4 py-2 text-center text-xs text-gray-500">
        ⚠️ Risk estimates based on weather + categorical condition data. Not a friction measurement system.
        Data: Trafikverket Open API (CC0).
      </div>
    </main>
  );
}
```

#### `frontend/src/components/RiskMap.tsx` — Leaflet map

```tsx
"use client";

import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useMemo } from "react";

type Props = {
  geojson: any;
};

const RISK_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#eab308",
  low: "#22c55e",
};

export default function RiskMap({ geojson }: Props) {
  const key = useMemo(() => JSON.stringify(geojson), [geojson]);

  const pointToLayer = (feature: any, latlng: L.LatLng) => {
    const level = feature.properties?.risk_level || "low";
    return L.circleMarker(latlng, {
      radius: 7,
      fillColor: RISK_COLORS[level] || "#22c55e",
      color: "#111",
      weight: 1,
      opacity: 0.9,
      fillOpacity: 0.8,
    });
  };

  const onEachFeature = (feature: any, layer: L.Layer) => {
    const p = feature.properties;
    if (!p) return;
    layer.bindPopup(`
      <div style="font-family: sans-serif; font-size: 13px; line-height: 1.5;">
        <strong>${p.name}</strong><br/>
        <span style="font-size: 20px; font-weight: bold; color: ${RISK_COLORS[p.risk_level]}">
          ${p.risk_score}/100
        </span>
        <span style="text-transform: uppercase; font-size: 11px; margin-left: 6px;">
          ${p.risk_level}
        </span><br/>
        <hr style="margin: 4px 0; border-color: #ddd;"/>
        Surface: ${p.surface_temp_c != null ? p.surface_temp_c + "°C" : "N/A"}<br/>
        Humidity: ${p.humidity_pct != null ? p.humidity_pct + "%" : "N/A"}<br/>
        Precip: ${p.precip_mm != null ? p.precip_mm + " mm" : "N/A"}<br/>
        ${p.condition_cause ? "Condition: " + p.condition_cause + "<br/>" : ""}
        ${p.nearby_alerts > 0 ? "⚠️ " + p.nearby_alerts + " nearby alert(s)<br/>" : ""}
        <span style="color: #999; font-size: 11px;">
          Data age: ${p.data_staleness_minutes ?? "?"} min
        </span>
      </div>
    `);
  };

  return (
    <MapContainer
      center={[62.5, 16.0]}
      zoom={5}
      style={{ height: "100%", width: "100%" }}
      className="bg-gray-900"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {geojson && (
        <GeoJSON
          key={key}
          data={geojson}
          pointToLayer={pointToLayer}
          onEachFeature={onEachFeature}
        />
      )}
    </MapContainer>
  );
}
```

### G.2 — CORS note

The FastAPI backend already includes CORS middleware configured from `ALLOWED_ORIGINS`. Make sure the Vercel domain is included when deploying.

---

## SECTION H — Local Run (One Command)

### H.1 — docker-compose.yml

```yaml
# docker-compose.yml (project root)
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      - ALLOWED_ORIGINS=http://localhost:3000
```

### H.2 — Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### H.3 — Run everything locally

```bash
# Terminal 1 — Backend (Docker)
cp backend/.env.example backend/.env
# Edit backend/.env and add your real TRAFIKVERKET_API_KEY
docker-compose up --build

# Terminal 2 — Frontend (dev server)
cd frontend
cp .env.example .env.local
# .env.local should have: NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:3000` in your browser.

### H.4 — Smoke test checklist

```bash
# 1. Health check
curl http://localhost:8000/health
# Expected: {"status":"ok","stations_cached":...,"last_refresh":...}

# 2. GeoJSON — all points
curl "http://localhost:8000/risk/geojson" | head -c 500
# Expected: {"type":"FeatureCollection","features":[{"type":"Feature",...}]}

# 3. GeoJSON — filtered by level
curl "http://localhost:8000/risk/geojson?level=high" | python3 -m json.tool | head -20
# Expected: Only features with "risk_level":"high"

# 4. GeoJSON — filtered by bounding box (Stockholm area)
curl "http://localhost:8000/risk/geojson?bbox=17.5,59.0,19.0,60.0"
# Expected: Only features within Stockholm area

# 5. Summary
curl http://localhost:8000/risk/summary
# Expected: {"total_stations":...,"high_risk_count":...,...}

# 6. Admin refresh (should fail without token)
curl -X POST http://localhost:8000/admin/refresh
# Expected: 403

# 7. Admin refresh (with token)
curl -X POST http://localhost:8000/admin/refresh -H "x-admin-token: change_me_to_a_random_string"
# Expected: {"status":"refreshed","stations":...}

# 8. OpenAPI docs
# Open http://localhost:8000/docs in browser
# Expected: Swagger UI with all endpoints
```

---

## SECTION I — Deploy Backend (Render)

### I.1 — Render setup

1. Push your repo to GitHub
2. Go to `https://dashboard.render.com`
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Configure:

| Setting | Value |
|---------|-------|
| Name | `srti-friction-risk-api` |
| Region | `Frankfurt (EU)` (closest to Sweden) |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | `Docker` |
| Instance Type | `Free` |

6. Add environment variables:

| Key | Value |
|-----|-------|
| `TRAFIKVERKET_API_KEY` | Your actual key |
| `ADMIN_TOKEN` | A random string |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (update after frontend deploy) |

7. Click "Create Web Service"

### I.2 — Post-deploy verification

```bash
# Replace with your actual Render URL
export API=https://srti-friction-risk-api.onrender.com

# Wait for first deploy (may take 2-5 min)
curl $API/health
curl "$API/risk/geojson" | python3 -m json.tool | head -30
curl "$API/risk/summary"

# Check OpenAPI docs
open "$API/docs"
```

**Note:** Render free tier sleeps after 15 min of no requests. First request after sleep takes ~30 seconds. This is fine for a portfolio demo.

---

## SECTION J — Deploy Frontend (Vercel)

### J.1 — Vercel setup

1. Go to `https://vercel.com`
2. Import your GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| Framework Preset | `Next.js` |
| Root Directory | `frontend` |
| Build Command | `next build` (default) |
| Output Directory | `.next` (default) |

4. Add environment variable:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_BACKEND_URL` | `https://srti-friction-risk-api.onrender.com` |

5. Deploy

### J.2 — After frontend deploy

Go back to Render and update `ALLOWED_ORIGINS` to include your Vercel URL (e.g., `https://srti-friction-risk.vercel.app`).

### J.3 — Post-deploy verification

1. Open your Vercel URL
2. Wait ~30 seconds if Render backend is sleeping
3. Confirm: Map loads with colored dots across Sweden
4. Confirm: Clicking a dot shows a popup with risk details
5. Confirm: Level filter dropdown works
6. Confirm: Refresh button fetches new data

---

## SECTION K — Final Demo Checklist (Must Pass All 12)

| # | Check | How to verify |
|---|-------|--------------|
| 1 | Backend health endpoint returns `"ok"` | `curl $API/health` |
| 2 | GeoJSON returns 100+ stations | Check `features` array length |
| 3 | Risk scores are 0–100 and levels are low/medium/high | Inspect any feature properties |
| 4 | BBox filter works | Pass Stockholm bbox, get fewer results |
| 5 | Level filter works | `?level=high` returns only high |
| 6 | Admin refresh works with token | POST with header returns 200 |
| 7 | Admin refresh fails without token | POST without header returns 403 |
| 8 | Frontend map renders with colored dots | Open Vercel URL, see dots on Sweden |
| 9 | Popup shows risk details on click | Click any dot |
| 10 | Level dropdown filters the map | Select "High risk only" |
| 11 | Disclaimer banner visible | Check bottom of page |
| 12 | OpenAPI docs accessible | Visit `$API/docs` |

### If API rate limits hit:

Trafikverket's API is generous for reasonable use. If you hit limits: increase `CACHE_TTL_SECONDS` to 900 (15 min) or 1800 (30 min). The demo still works because the map shows whatever was last cached.

### What to show in the README:

A screenshot of the map with colored risk dots, the architecture diagram (text or image), and a clear link to the live demo.

---

## SECTION L — README Template

```markdown
# SRTI Friction Risk Microservice 🇸🇪🧊

> Real-time road friction risk scoring for Swedish roads, powered by
> Trafikverket open data.

**⚠️ Disclaimer:** This project computes friction *risk estimates* based on
publicly available weather observations and categorical road condition reports.
It does NOT measure actual friction coefficients. Quantitative friction data
(e.g., from NIRA Dynamics sensors) is not publicly accessible. The risk score
is a heuristic composite — not a safety-critical measurement.

## Live Demo

- 🗺️ **Frontend:** [your-app.vercel.app](https://your-app.vercel.app)
- 🔌 **API Docs:** [your-api.onrender.com/docs](https://your-api.onrender.com/docs)

## Problem

Swedish roads experience dangerous friction conditions during winter months.
Trafikverket operates ~700 weather stations and publishes road condition data,
but this information is spread across multiple API endpoints with no composite
risk scoring. This project integrates three data streams into a single,
map-based risk visualization.

## Data Sources

| Source | Type | Update Frequency |
|--------|------|-----------------|
| Trafikverket WeatherMeasurepoint | Road surface temp, humidity, precip, wind | ~10 min |
| Trafikverket RoadCondition | Categorical road state ("icy", "dry", etc.) | Variable |
| Trafikverket Situation | Traffic incidents, hazard alerts | Real-time |

All data is fetched from the [Trafikverket Open API v2](https://api.trafikinfo.trafikverket.se)
under the CC0 license.

## Architecture

```
┌─────────────────────────────┐
│   Vercel (Next.js + Leaflet)│
│   - Interactive risk map    │
│   - Level filter controls   │
│   - Auto-refresh            │
└─────────────┬───────────────┘
              │ HTTPS (GeoJSON)
              ▼
┌─────────────────────────────┐
│   Render (FastAPI + Python) │
│   - /risk/geojson           │
│   - /risk/summary           │
│   - /health                 │
│   - In-memory TTL cache     │
└─────────────┬───────────────┘
              │ HTTP POST (XML → JSON)
              ▼
┌─────────────────────────────┐
│   Trafikverket Open API v2  │
│   - WeatherMeasurepoint     │
│   - RoadCondition           │
│   - Situation               │
└─────────────────────────────┘
```

## Risk Scoring

Composite score (0–100) based on:
- **Surface temperature** (35%) — sub-zero = danger
- **Precipitation** (25%) — rain/snow + cold = amplified risk
- **Humidity** (15%) — high humidity + cold surface = frost/black ice
- **Road condition report** (25%) — direct categorical signal

Bonus: +5 per nearby traffic alert (max +15). Time-decay penalizes stale data.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health + station count |
| GET | `/risk/geojson?bbox=&level=` | GeoJSON risk points |
| GET | `/risk/summary` | Aggregate statistics |
| POST | `/admin/refresh` | Force cache refresh (token required) |

## Run Locally

```bash
# 1. Clone and configure
git clone https://github.com/YOUR_USER/srti-friction-risk.git
cd srti-friction-risk
cp backend/.env.example backend/.env
# Edit backend/.env with your Trafikverket API key

# 2. Start backend
docker-compose up --build

# 3. Start frontend (new terminal)
cd frontend
cp .env.example .env.local
npm install && npm run dev

# 4. Open http://localhost:3000
```

## Limitations

- Risk scores are heuristic estimates, not safety-critical measurements
- Actual friction coefficient data (e.g., NIRA Dynamics) is not publicly available
- In-memory cache resets on server restart (no persistent storage)
- Free-tier hosting: backend sleeps after 15 min inactivity
- Nearest-station matching uses simple Euclidean distance, not road network routing
- Swedish condition categories are fuzzy-matched — edge cases may mis-classify

## Context: Why This Project Exists

Volvo Cars and Trafikverket launched a connected road friction pilot in 2014
using fleet-wide ABS/ESC data. Volvo's Slippery Road Alert feature represents
the *vehicle side* of friction detection. This project implements the
*road authority side* — processing government sensor data to estimate where
roads are dangerous. Together, they represent the complete SRTI
(Safety-Related Traffic Information) ecosystem.

Built with Swedish road safety data to demonstrate understanding of the
EU SRTI Directive (Regulation 886/2013) and the Data For Road Safety (DFRS)
consortium ecosystem.

## License

MIT
```

---

## Quick Reference: Build Order (Fastest Path)

For the impatient, here is the exact order to build this:

1. **Get your Trafikverket API key** (5 min)
2. **Create the repo and folder structure** (Section B)
3. **Create `backend/.env`** with your key (Section C)
4. **Build `config.py` → `models.py` → `ingestion.py`** and test with `pytest` or a simple script (Section D)
5. **Build `scoring.py`** and test that scores make sense (Section E)
6. **Build `geojson_builder.py` → `main.py`** and test with `curl` (Section F)
7. **Run backend in Docker** and verify all endpoints (Section H)
8. **Create the Next.js frontend** with Leaflet map (Section G)
9. **Deploy backend to Render** (Section I)
10. **Deploy frontend to Vercel** (Section J)
11. **Run the demo checklist** (Section K)
12. **Write the README** (Section L)

Total time estimate: 2–3 focused days for a working demo, or a comfortable week if polishing the UI and writing thorough documentation.
