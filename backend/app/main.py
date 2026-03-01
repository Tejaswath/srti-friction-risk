import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.geojson_builder import build_geojson
from app.ingestion import clear_all_caches, fetch_road_conditions, fetch_situations, fetch_weather
from app.models import HealthResponse, SummaryResponse
from app.scoring import compute_all_risks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SRTI Friction Risk Microservice",
    description=(
        "Real-time road friction risk scoring for Swedish roads. "
        "Based on Trafikverket weather, road condition, and situation data. "
        "NOT a friction measurement system."
    ),
    version="1.0.0",
)

origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_refresh: Optional[datetime] = None


async def _get_risk_data():
    global _last_refresh

    weather = await fetch_weather()
    try:
        conditions = await fetch_road_conditions()
    except Exception as exc:
        logger.exception("Road condition fetch failed, continuing without conditions: %s", exc)
        conditions = []

    try:
        alerts = await fetch_situations()
    except Exception as exc:
        logger.exception("Situation fetch failed, continuing without alerts: %s", exc)
        alerts = []

    risks = await compute_all_risks(weather, conditions, alerts)
    _last_refresh = datetime.now(timezone.utc)
    return risks


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        weather = await fetch_weather()
        return HealthResponse(status="ok", stations_cached=len(weather), last_refresh=_last_refresh)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Health check degraded: %s", exc)
        return HealthResponse(
            status=f"degraded: {str(exc)[:100]}",
            stations_cached=0,
            last_refresh=_last_refresh,
        )


@app.get("/risk/geojson")
async def get_risk_geojson(
    bbox: Optional[str] = Query(None, description="Bounding box: min_lon,min_lat,max_lon,max_lat"),
    level: Optional[str] = Query(None, description="Filter by risk level: low, medium, high"),
):
    parsed_bbox = None
    if bbox:
        try:
            parts = [float(chunk.strip()) for chunk in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            parsed_bbox = tuple(parts)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat",
            ) from exc

    if level and level not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="level must be low, medium, or high")

    risks = await _get_risk_data()
    return build_geojson(risks, bbox=parsed_bbox, level_filter=level)


@app.get("/risk/summary", response_model=SummaryResponse)
async def get_risk_summary(region: Optional[str] = Query(None, description="Reserved for future use")):
    del region
    risks = await _get_risk_data()

    if not risks:
        return SummaryResponse(
            total_stations=0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            avg_risk_score=0.0,
            last_refresh=_last_refresh,
        )

    return SummaryResponse(
        total_stations=len(risks),
        high_risk_count=sum(1 for risk in risks if risk.risk_level.value == "high"),
        medium_risk_count=sum(1 for risk in risks if risk.risk_level.value == "medium"),
        low_risk_count=sum(1 for risk in risks if risk.risk_level.value == "low"),
        avg_risk_score=round(sum(risk.risk_score for risk in risks) / len(risks), 1),
        last_refresh=_last_refresh,
    )


@app.post("/admin/refresh")
async def admin_refresh(x_admin_token: Optional[str] = Header(default=None)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    clear_all_caches()
    risks = await _get_risk_data()
    return {"status": "refreshed", "stations": len(risks)}
