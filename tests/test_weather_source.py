"""preprocess/weather_source.py のテスト。通信はフィクスチャで代替（ライブは RUN_LIVE_JMA=1 のときのみ）。"""
import math
import os
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from preprocess.weather_source import WeatherFetchError, _num, _parse_day, fetch_weather

FIXTURE = Path(__file__).parent / "fixtures" / "jma_hourly_47807_20250727.html"


def test_num_rules():
    assert _num("30.0") == 30.0
    assert _num("--", none_is_zero=True) == 0.0
    assert math.isnan(_num("--"))
    assert math.isnan(_num(""))
    assert math.isnan(_num("×"))
    assert math.isnan(_num("///"))
    assert _num("25.5)") == 25.5


def test_parse_day_matches_known_values():
    rows = _parse_day(FIXTURE.read_bytes(), date(2025, 7, 27), "福岡")
    assert len(rows) == 24
    first = rows[0]
    assert first["datetime"] == pd.Timestamp("2025-07-27 01:00")
    assert first["pressure"] == 1004.4
    assert first["temperature"] == 30.0
    assert first["precipitation"] == 0.0   # 表記は "--"（現象なし）
    assert first["wind_speed"] == 3.0
    assert rows[-1]["datetime"] == pd.Timestamp("2025-07-28 00:00")  # 24時 → 翌日 0 時


def test_parse_day_without_table_raises():
    with pytest.raises(WeatherFetchError, match="データ表"):
        _parse_day(b"<html><body>error</body></html>", date(2025, 7, 27), "福岡")


def test_fetch_weather_unknown_station_raises():
    with pytest.raises(WeatherFetchError, match="未対応"):
        fetch_weather("存在しない地点", date(2025, 7, 27), date(2025, 7, 27))


def test_fetch_weather_offline_via_monkeypatched_get(monkeypatch):
    """requests.get を差し替えて 2 日ぶんの結合と列を確認する（通信なし・sleep なし）。"""
    html = FIXTURE.read_bytes()
    calls = []

    class FakeResponse:
        content = html
        def raise_for_status(self):
            pass

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse()

    monkeypatch.setattr("preprocess.weather_source.requests.get", fake_get)
    monkeypatch.setattr("preprocess.weather_source.time.sleep", lambda s: None)
    df = fetch_weather("福岡", date(2025, 7, 27), date(2025, 7, 28))
    assert len(calls) == 2
    assert calls[0]["prec_no"] == 82 and calls[0]["block_no"] == 47807
    assert list(df.columns) == ["station", "datetime", "temperature", "precipitation", "wind_speed", "pressure"]
    assert len(df) == 48
    from typhoon_app.data.schema import validate_weather
    validated = validate_weather(df)
    assert validated["pressure"].dtype == "float64"


@pytest.mark.skipif(not os.environ.get("RUN_LIVE_JMA"), reason="ライブ取得は RUN_LIVE_JMA=1 のときのみ")
def test_fetch_weather_live_one_day():
    df = fetch_weather("福岡", date(2025, 7, 27), date(2025, 7, 27))
    assert len(df) == 24
    assert df["pressure"].iloc[0] == 1004.4


def test_fetch_weather_uses_station_master(monkeypatch):
    """station.csv で追加された地点でも取得できる（地点解決は load_stations 経由）。"""
    from typhoon_app.config import Station

    html = FIXTURE.read_bytes()

    class FakeResponse:
        content = html
        def raise_for_status(self):
            pass

    calls = []
    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse()

    monkeypatch.setattr("preprocess.weather_source.requests.get", fake_get)
    monkeypatch.setattr(
        "preprocess.weather_source.load_stations",
        lambda: {"東京": Station("東京", 35.69, 139.75, 44, 47662)},
    )
    df = fetch_weather("東京", date(2025, 7, 27), date(2025, 7, 27))
    assert calls[0]["prec_no"] == 44 and calls[0]["block_no"] == 47662
    assert set(df["station"]) == {"東京"}

    with pytest.raises(WeatherFetchError, match="未対応"):
        fetch_weather("福岡", date(2025, 7, 27), date(2025, 7, 27))  # マスタに無い地点はエラー
