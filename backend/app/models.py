from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


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
    cause: Optional[str] = None
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
    risk_score: int
    risk_level: RiskLevel
    surface_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    precip_mm: Optional[float] = None
    condition_cause: Optional[str] = None
    condition_label: Optional[str] = None
    nearby_alerts: int = 0
    data_staleness_minutes: Optional[int] = None
    computed_at: datetime


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
