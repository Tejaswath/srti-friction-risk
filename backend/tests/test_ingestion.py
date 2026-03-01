import pytest

from app.ingestion import (
    TrafikverketAPIError,
    _extract_result_block,
    _parse_dt,
    _parse_wgs84,
    _safe_float,
    _warn_if_limit_hit,
)


def test_parse_wgs84_point_ok():
    lat, lon = _parse_wgs84("POINT (18.0563 59.3293)")
    assert lat == 59.3293
    assert lon == 18.0563


def test_parse_wgs84_invalid_returns_none():
    lat, lon = _parse_wgs84("LINESTRING (18.0 59.0, 18.1 59.1)")
    assert lat is None
    assert lon is None


def test_safe_float_nested_success():
    payload = {"a": {"b": {"value": "1.23"}}}
    assert _safe_float(payload, "a", "b", "value") == 1.23


def test_safe_float_missing_returns_none():
    payload = {"a": {"b": {"value": "1.23"}}}
    assert _safe_float(payload, "a", "x", "value") is None


def test_parse_dt_accepts_isoz():
    parsed = _parse_dt("2026-03-01T12:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026


def test_parse_dt_invalid_returns_none():
    assert _parse_dt("not-a-date") is None


def test_extract_result_block_ok():
    payload = {"RESPONSE": {"RESULT": [{"WeatherMeasurepoint": []}]}}
    assert _extract_result_block(payload) == {"WeatherMeasurepoint": []}


def test_extract_result_block_error_raises():
    payload = {"RESPONSE": {"ERROR": "Auth failed"}}
    with pytest.raises(TrafikverketAPIError):
        _extract_result_block(payload)


def test_warn_if_limit_hit_logs_warning(caplog):
    with caplog.at_level("WARNING"):
        _warn_if_limit_hit("WeatherMeasurepoint", 1000, 1000)
    assert "may be truncated" in caplog.text


def test_warn_if_limit_hit_below_limit_no_warning(caplog):
    with caplog.at_level("WARNING"):
        _warn_if_limit_hit("WeatherMeasurepoint", 999, 1000)
    assert "may be truncated" not in caplog.text
