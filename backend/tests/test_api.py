from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import FrictionRiskPoint, RiskLevel, WeatherPoint

client = TestClient(app)


def _mock_risks():
    now = datetime.now(timezone.utc)
    return [
        FrictionRiskPoint(
            station_id="1",
            name="Stockholm",
            lat=59.3293,
            lon=18.0686,
            risk_score=70,
            risk_level=RiskLevel.HIGH,
            computed_at=now,
        ),
        FrictionRiskPoint(
            station_id="2",
            name="Gothenburg",
            lat=57.7089,
            lon=11.9746,
            risk_score=20,
            risk_level=RiskLevel.LOW,
            computed_at=now,
        ),
    ]


def test_geojson_invalid_level_returns_400():
    response = client.get("/risk/geojson?level=critical")
    assert response.status_code == 400


def test_geojson_invalid_bbox_returns_400():
    response = client.get("/risk/geojson?bbox=1,2,3")
    assert response.status_code == 400


def test_geojson_level_filter(monkeypatch):
    async def _fake_data():
        return _mock_risks()

    monkeypatch.setattr("app.main._get_risk_data", _fake_data)

    response = client.get("/risk/geojson?level=high")
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    assert payload["features"][0]["properties"]["risk_level"] == "high"


def test_geojson_bbox_filter(monkeypatch):
    async def _fake_data():
        return _mock_risks()

    monkeypatch.setattr("app.main._get_risk_data", _fake_data)

    response = client.get("/risk/geojson?bbox=17.5,59.0,19.0,60.0")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["features"]) == 1
    assert payload["features"][0]["properties"]["name"] == "Stockholm"


def test_summary_counts(monkeypatch):
    async def _fake_data():
        return _mock_risks()

    monkeypatch.setattr("app.main._get_risk_data", _fake_data)

    response = client.get("/risk/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_stations"] == 2
    assert payload["high_risk_count"] == 1
    assert payload["medium_risk_count"] == 0
    assert payload["low_risk_count"] == 1
    assert payload["avg_risk_score"] == 45.0


def test_health_ok(monkeypatch):
    async def _fake_fetch_weather():
        return [
            WeatherPoint(
                station_id="1",
                name="Test",
                lat=59.3,
                lon=18.0,
            )
        ]

    monkeypatch.setattr("app.main.fetch_weather", _fake_fetch_weather)

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stations_cached"] == 1


def test_health_degraded(monkeypatch):
    async def _raise_error():
        raise RuntimeError("upstream failed")

    monkeypatch.setattr("app.main.fetch_weather", _raise_error)

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"].startswith("degraded")


def test_admin_refresh_requires_token():
    response = client.post("/admin/refresh")
    assert response.status_code == 403


def test_admin_refresh_with_valid_token(monkeypatch):
    token = "test-admin-token"

    async def _fake_data():
        return _mock_risks()

    called = {"cleared": False}

    def _fake_clear_cache():
        called["cleared"] = True

    monkeypatch.setattr("app.main._get_risk_data", _fake_data)
    monkeypatch.setattr("app.main.clear_all_caches", _fake_clear_cache)

    response = client.post("/admin/refresh", headers={"x-admin-token": token})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "refreshed"
    assert payload["stations"] == 2
    assert called["cleared"] is True
