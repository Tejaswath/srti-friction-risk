from datetime import datetime, timezone

from app.geojson_builder import build_geojson
from app.models import FrictionRiskPoint, RiskLevel


def _point(
    station_id: str,
    lat: float,
    lon: float,
    level: RiskLevel,
    score: int,
    condition_label: str | None = None,
):
    return FrictionRiskPoint(
        station_id=station_id,
        name=f"Station {station_id}",
        lat=lat,
        lon=lon,
        risk_score=score,
        risk_level=level,
        condition_label=condition_label,
        computed_at=datetime.now(timezone.utc),
    )


def test_build_geojson_all_points():
    points = [
        _point("1", 59.3, 18.0, RiskLevel.HIGH, 80),
        _point("2", 57.7, 11.9, RiskLevel.LOW, 20),
    ]
    result = build_geojson(points)
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2


def test_build_geojson_level_filter():
    points = [
        _point("1", 59.3, 18.0, RiskLevel.HIGH, 80),
        _point("2", 57.7, 11.9, RiskLevel.LOW, 20),
    ]
    result = build_geojson(points, level_filter="high")
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["risk_level"] == "high"


def test_build_geojson_bbox_filter():
    points = [
        _point("1", 59.3, 18.0, RiskLevel.HIGH, 80),
        _point("2", 57.7, 11.9, RiskLevel.LOW, 20),
    ]
    bbox = (17.5, 59.0, 19.0, 60.0)
    result = build_geojson(points, bbox=bbox)
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["station_id"] == "1"


def test_build_geojson_includes_condition_label():
    points = [_point("1", 59.3, 18.0, RiskLevel.HIGH, 80, condition_label="Rimfrost")]
    result = build_geojson(points)
    assert result["features"][0]["properties"]["condition_label"] == "Rimfrost"
