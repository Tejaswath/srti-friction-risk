import math
from datetime import datetime, timezone
from typing import Optional

from app.models import (
    FrictionRiskPoint,
    RiskLevel,
    RoadConditionPoint,
    SituationAlert,
    WeatherPoint,
)

CONDITION_RISK_MAP: dict[str, float] = {
    "ishalka": 1.0,
    "belagd med is och snö": 0.95,
    "snöhalka": 0.9,
    "rimfrost": 0.8,
    "spårigt": 0.7,
    "våt väg": 0.4,
    "fuktigt väglag": 0.35,
    "delvis isbelagd": 0.75,
    "torr väg": 0.0,
    "bar väg": 0.0,
}


def _match_condition_risk(cause: Optional[str]) -> float:
    if not cause:
        return 0.0
    cause_lower = cause.lower().strip()
    for key, value in CONDITION_RISK_MAP.items():
        if key in cause_lower:
            return value
    return 0.3


def _surface_temp_score(temp_c: Optional[float]) -> float:
    if temp_c is None:
        return 0.3
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
    return 1.0


def _precip_score(precip_mm: Optional[float], surface_temp_c: Optional[float]) -> float:
    if precip_mm is None or precip_mm <= 0.0:
        return 0.0
    base = min(precip_mm / 3.0, 1.0)
    if surface_temp_c is not None and surface_temp_c <= 0.0:
        base = min(base * 1.5, 1.0)
    return base


def _humidity_score(humidity_pct: Optional[float], surface_temp_c: Optional[float]) -> float:
    if humidity_pct is None:
        return 0.1
    if humidity_pct < 70:
        return 0.0
    if humidity_pct < 85:
        factor = 0.2
    else:
        factor = 0.6
    if surface_temp_c is not None and surface_temp_c > 3.0:
        factor *= 0.3
    return min(factor, 1.0)


def _time_decay_factor(observed_at: Optional[datetime]) -> float:
    if observed_at is None:
        return 0.5

    now = datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    age_minutes = (now - observed_at).total_seconds() / 60.0
    age_minutes = max(age_minutes, 0.0)

    if age_minutes <= 30:
        return 1.0
    if age_minutes <= 60:
        return 0.9
    if age_minutes <= 120:
        return 0.7
    if age_minutes <= 180:
        return 0.5
    return 0.0


def _count_nearby_alerts(
    lat: float,
    lon: float,
    alerts: list[SituationAlert],
    radius_deg: float = 0.15,
) -> int:
    count = 0
    for alert in alerts:
        if alert.lat is None or alert.lon is None:
            continue
        if abs(alert.lat - lat) < radius_deg and abs(alert.lon - lon) < radius_deg:
            count += 1
    return count


def compute_risk(
    weather: WeatherPoint,
    conditions: list[RoadConditionPoint],
    alerts: list[SituationAlert],
) -> FrictionRiskPoint:
    nearest_condition: Optional[RoadConditionPoint] = None
    min_dist = float("inf")

    for condition in conditions:
        distance = math.hypot(condition.lat - weather.lat, condition.lon - weather.lon)
        if distance < min_dist and distance < 0.2:
            min_dist = distance
            nearest_condition = condition

    temp_score = _surface_temp_score(weather.surface_temp_c)
    precip_score = _precip_score(weather.precip_mm, weather.surface_temp_c)
    humid_score = _humidity_score(weather.humidity_pct, weather.surface_temp_c)
    cond_score = _match_condition_risk(nearest_condition.cause if nearest_condition else None)

    raw = (temp_score * 0.35) + (precip_score * 0.25) + (humid_score * 0.15) + (cond_score * 0.25)

    nearby_alerts = _count_nearby_alerts(weather.lat, weather.lon, alerts)
    raw = min(raw + min(nearby_alerts * 0.05, 0.15), 1.0)

    decay = _time_decay_factor(weather.observed_at)
    if decay == 0.0:
        score = 0
    else:
        score = round(raw * decay * 100)
    score = max(0, min(100, score))

    if score <= 30:
        level = RiskLevel.LOW
    elif score <= 60:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.HIGH

    staleness = None
    if weather.observed_at:
        observed_at = weather.observed_at
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        staleness = round((datetime.now(timezone.utc) - observed_at).total_seconds() / 60.0)

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
        nearby_alerts=nearby_alerts,
        data_staleness_minutes=staleness,
        computed_at=datetime.now(timezone.utc),
    )


async def compute_all_risks(
    weather_points: list[WeatherPoint],
    conditions: list[RoadConditionPoint],
    alerts: list[SituationAlert],
) -> list[FrictionRiskPoint]:
    return [compute_risk(point, conditions, alerts) for point in weather_points]
