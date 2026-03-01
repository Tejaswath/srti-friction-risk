from datetime import datetime, timedelta, timezone

from app.models import RiskLevel, RoadConditionPoint, SituationAlert, WeatherPoint
from app.scoring import (
    _humidity_score,
    _match_condition_risk,
    _precip_score,
    _surface_temp_score,
    _time_decay_factor,
    compute_risk,
)


def _weather_point(surface_temp_c: float, humidity_pct: float, precip_mm: float) -> WeatherPoint:
    return WeatherPoint(
        station_id="station-1",
        name="Demo Station",
        lat=59.33,
        lon=18.06,
        surface_temp_c=surface_temp_c,
        humidity_pct=humidity_pct,
        precip_mm=precip_mm,
        observed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )


def test_surface_temp_score_ranges():
    assert _surface_temp_score(8.0) == 0.0
    assert _surface_temp_score(1.0) == 0.5
    assert _surface_temp_score(-2.0) == 0.75
    assert _surface_temp_score(-20.0) == 1.0


def test_precip_score_amplifies_when_freezing():
    non_freezing = _precip_score(1.0, 2.0)
    freezing = _precip_score(1.0, -1.0)
    assert freezing > non_freezing


def test_humidity_score_reduced_on_warm_surface():
    warm = _humidity_score(90.0, 5.0)
    cold = _humidity_score(90.0, -1.0)
    assert cold > warm


def test_condition_mapping_known_and_unknown():
    assert _match_condition_risk("Ishalka") == 1.0
    assert _match_condition_risk("Unknown condition") == 0.3
    assert _match_condition_risk(None) == 0.0


def test_time_decay_factor_windows():
    now = datetime.now(timezone.utc)
    assert _time_decay_factor(now - timedelta(minutes=10)) == 1.0
    assert _time_decay_factor(now - timedelta(minutes=45)) == 0.9
    assert _time_decay_factor(now - timedelta(minutes=90)) == 0.7
    assert _time_decay_factor(now - timedelta(minutes=150)) == 0.5
    assert _time_decay_factor(now - timedelta(minutes=181)) == 0.0


def test_low_risk_label_under_30():
    weather = _weather_point(surface_temp_c=8.0, humidity_pct=40.0, precip_mm=0.0)
    risk = compute_risk(weather, [], [])
    assert 0 <= risk.risk_score <= 30
    assert risk.risk_level == RiskLevel.LOW


def test_high_risk_over_60_with_alert_bonus():
    weather = _weather_point(surface_temp_c=-6.0, humidity_pct=95.0, precip_mm=2.5)
    alerts = [SituationAlert(situation_id="s1", lat=59.34, lon=18.07)]
    risk = compute_risk(weather, [], alerts)
    assert risk.risk_score >= 61
    assert risk.risk_level == RiskLevel.HIGH
    assert risk.nearby_alerts == 1


def test_nearest_condition_selected():
    weather = _weather_point(surface_temp_c=-1.0, humidity_pct=90.0, precip_mm=0.5)
    near = RoadConditionPoint(
        condition_id="c-near",
        cause="Ishalka",
        lat=59.331,
        lon=18.061,
    )
    far = RoadConditionPoint(
        condition_id="c-far",
        cause="Torr väg",
        lat=60.0,
        lon=20.0,
    )
    risk = compute_risk(weather, [far, near], [])
    assert risk.condition_cause == "Ishalka"


def test_stale_data_over_180_minutes_becomes_zero():
    weather = WeatherPoint(
        station_id="station-2",
        name="Old Data",
        lat=57.7,
        lon=11.97,
        surface_temp_c=-4.0,
        humidity_pct=92.0,
        precip_mm=1.0,
        observed_at=datetime.now(timezone.utc) - timedelta(minutes=181),
    )
    risk = compute_risk(weather, [], [])
    assert risk.risk_score == 0
    assert risk.risk_level == RiskLevel.LOW
