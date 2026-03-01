from typing import Optional

from app.models import FrictionRiskPoint


def build_geojson(
    risk_points: list[FrictionRiskPoint],
    bbox: Optional[tuple[float, float, float, float]] = None,
    level_filter: Optional[str] = None,
) -> dict:
    features = []

    for point in risk_points:
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            if not (min_lat <= point.lat <= max_lat and min_lon <= point.lon <= max_lon):
                continue

        if level_filter and point.risk_level.value != level_filter:
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.lon, point.lat],
                },
                "properties": {
                    "station_id": point.station_id,
                    "name": point.name,
                    "risk_score": point.risk_score,
                    "risk_level": point.risk_level.value,
                    "surface_temp_c": point.surface_temp_c,
                    "humidity_pct": point.humidity_pct,
                    "precip_mm": point.precip_mm,
                    "condition_cause": point.condition_cause,
                    "condition_label": point.condition_label,
                    "nearby_alerts": point.nearby_alerts,
                    "data_staleness_minutes": point.data_staleness_minutes,
                    "computed_at": point.computed_at.isoformat(),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
