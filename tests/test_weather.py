from datetime import date

import pandas as pd

from typhoon_app.data.source import get_fetcher
from typhoon_app.data.weather import (
    cache_path,
    combine,
    get_station_weather,
    get_weather,
    write_cache,
)

WINDOW = (date(2025, 8, 14), date(2025, 8, 28))


def make_fetcher(df: pd.DataFrame, calls: list):
    def fetch(station, start, end):
        calls.append((station, start, end))
        return df[df["station"] == station]

    return fetch


def test_cache_hit_does_not_call_fetcher(tmp_path, weather_df):
    write_cache(weather_df[weather_df["station"] == "福岡"], cache_path("202512", "福岡", tmp_path))
    calls = []
    r = get_station_weather("202512", "福岡", WINDOW, make_fetcher(weather_df, calls), tmp_path)
    assert r.status == "cached" and r.ok
    assert calls == []
    assert len(r.df) == 6


def test_cache_miss_fetches_then_saves(tmp_path, weather_df):
    calls = []
    r = get_station_weather("202512", "鹿児島", WINDOW, make_fetcher(weather_df, calls), tmp_path)
    assert r.status == "fetched"
    assert calls == [("鹿児島", date(2025, 8, 14), date(2025, 8, 28))]
    assert cache_path("202512", "鹿児島", tmp_path).exists()
    again = get_station_weather("202512", "鹿児島", WINDOW, make_fetcher(weather_df, calls), tmp_path)
    assert again.status == "cached" and len(calls) == 1
    assert len(again.df) == 6


def test_no_fetcher_means_unavailable(tmp_path):
    r = get_station_weather("202512", "福岡", WINDOW, None, tmp_path)
    assert r.status == "unavailable" and not r.ok and r.df is None


def test_fetch_error_does_not_stop_other_stations(tmp_path, weather_df):
    def failing(station, start, end):
        if station == "福岡":
            raise RuntimeError("network down")
        return weather_df[weather_df["station"] == station]

    results = get_weather("202512", ["福岡", "鹿児島"], WINDOW, failing, tmp_path)
    assert results["福岡"].status == "error"
    assert "network down" in results["福岡"].message
    assert results["鹿児島"].status == "fetched"
    combined = combine(results)
    assert set(combined["station"]) == {"鹿児島"}


def test_bad_schema_from_fetcher_is_error(tmp_path, weather_df):
    def bad(station, start, end):
        return weather_df.drop(columns=["pressure"])

    r = get_station_weather("202512", "福岡", WINDOW, bad, tmp_path)
    assert r.status == "error" and "pressure" in r.message
    assert not cache_path("202512", "福岡", tmp_path).exists()


def test_combine_empty_has_contract_columns():
    df = combine({})
    assert df.empty and "pressure" in df.columns


def test_get_fetcher_missing_module_is_none():
    assert get_fetcher("no_such_module_xyz", "fetch_weather") is None


def test_get_fetcher_returns_callable():
    assert callable(get_fetcher("math", "sqrt"))
