import logging
import re
from datetime import datetime
from typing import Optional

import httpx
from cachetools import TTLCache

from app.config import settings
from app.models import RoadConditionPoint, SituationAlert, WeatherPoint

logger = logging.getLogger(__name__)

API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

_weather_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)
_condition_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)
_situation_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)


class TrafikverketAPIError(RuntimeError):
    """Raised when Trafikverket API responds with malformed or error payloads."""


def _parse_wgs84(wkt: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    if not wkt:
        return None, None
    match = re.search(r"POINT\s*\(\s*([\d.\-]+)\s+([\d.\-]+)\s*\)", wkt)
    if match:
        lon, lat = float(match.group(1)), float(match.group(2))
        return lat, lon
    return None, None


def _safe_float(obj: dict, *keys: str) -> Optional[float]:
    current: object = obj
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    try:
        return float(current) if current is not None else None
    except (TypeError, ValueError):
        return None


def _safe_str(obj: dict, key: str) -> Optional[str]:
    value = obj.get(key)
    return str(value) if value is not None else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _extract_result_block(payload: dict) -> dict:
    response = payload.get("RESPONSE", {})
    if not isinstance(response, dict):
        raise TrafikverketAPIError("Missing RESPONSE object")

    errors = response.get("ERROR")
    if errors:
        raise TrafikverketAPIError(str(errors))

    result = response.get("RESULT", [])
    if not isinstance(result, list) or not result:
        return {}
    first = result[0]
    return first if isinstance(first, dict) else {}


async def _post_trafikverket(xml_body: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            API_URL,
            content=xml_body.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_weather() -> list[WeatherPoint]:
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
    block = _extract_result_block(data)
    results = block.get("WeatherMeasurepoint", [])
    points: list[WeatherPoint] = []

    for row in results:
        obs = row.get("Observation", {}) or {}
        geom = row.get("Geometry", {}) or {}
        lat, lon = _parse_wgs84(geom.get("WGS84"))
        if lat is None or lon is None:
            continue

        points.append(
            WeatherPoint(
                station_id=str(row.get("Id", "")),
                name=row.get("Name", "Unknown"),
                lat=lat,
                lon=lon,
                air_temp_c=_safe_float(obs, "Air", "Temperature", "Value"),
                surface_temp_c=_safe_float(obs, "Surface", "Temperature", "Value"),
                humidity_pct=_safe_float(obs, "Air", "RelativeHumidity", "Value"),
                precip_mm=_safe_float(
                    obs,
                    "Aggregated10minutes",
                    "Precipitation",
                    "TotalWaterEquivalent",
                    "Value",
                ),
                wind_speed_ms=_safe_float(obs, "Wind", "Speed", "Value"),
                observed_at=_parse_dt(obs.get("Sample")),
                modified_at=_parse_dt(row.get("ModifiedTime")),
            )
        )

    _weather_cache["data"] = points
    logger.info("Fetched %s weather points", len(points))
    return points


async def fetch_road_conditions() -> list[RoadConditionPoint]:
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
    block = _extract_result_block(data)
    results = block.get("RoadCondition", [])
    points: list[RoadConditionPoint] = []

    for row in results:
        geom = row.get("Geometry", {}) or {}
        lat, lon = _parse_wgs84(geom.get("WGS84"))
        if lat is None or lon is None:
            continue

        road_num = row.get("RoadNumberNumeric")
        points.append(
            RoadConditionPoint(
                condition_id=str(row.get("Id", "")),
                road_number=int(road_num) if road_num else None,
                cause=_safe_str(row, "Cause"),
                condition_text=_safe_str(row, "ConditionText"),
                lat=lat,
                lon=lon,
                measured_at=_parse_dt(row.get("MeasurementTime")),
            )
        )

    _condition_cache["data"] = points
    logger.info("Fetched %s road condition points", len(points))
    return points


async def fetch_situations() -> list[SituationAlert]:
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
    block = _extract_result_block(data)
    results = block.get("Situation", [])
    alerts: list[SituationAlert] = []

    for row in results:
        deviations = row.get("Deviation", [])
        if isinstance(deviations, dict):
            deviations = [deviations]

        for deviation in deviations:
            geom = deviation.get("Geometry", {}) or {}
            lat, lon = _parse_wgs84(geom.get("WGS84"))
            alerts.append(
                SituationAlert(
                    situation_id=str(row.get("Id", "")),
                    message_type=deviation.get("MessageType"),
                    situation_type=deviation.get("SituationType"),
                    header=deviation.get("Header"),
                    lat=lat,
                    lon=lon,
                    start_time=_parse_dt(deviation.get("StartTime")),
                    end_time=_parse_dt(deviation.get("EndTime")),
                )
            )

    _situation_cache["data"] = alerts
    logger.info("Fetched %s situation alerts", len(alerts))
    return alerts


def clear_all_caches() -> None:
    _weather_cache.clear()
    _condition_cache.clear()
    _situation_cache.clear()
