import pandas as pd
import pytest

from typhoon_app.data.schema import (
    TYPHOON_COLUMNS,
    WEATHER_COLUMNS,
    SchemaError,
    validate_typhoon,
    validate_weather,
)


def test_validate_weather_coerces_types(weather_raw):
    df = validate_weather(weather_raw)
    assert list(WEATHER_COLUMNS) == [c for c in df.columns if c in WEATHER_COLUMNS]
    assert str(df["datetime"].dtype).startswith("datetime64")
    assert df["pressure"].dtype == "float64"
    assert str(df["weather_code"].dtype) == "Int64"
    assert df["precipitation"].isna().sum() == 1          # 鹿児島 02:00 の欠測
    assert df["datetime"].iloc[0] == pd.Timestamp("2025-08-21 21:00:00")


def test_validate_weather_missing_column_names_it(weather_raw):
    with pytest.raises(SchemaError, match="pressure"):
        validate_weather(weather_raw.drop(columns=["pressure"]))


def test_validate_weather_rejects_unparseable_value(weather_raw):
    bad = weather_raw.astype({"precipitation": "string"})
    bad.loc[0, "precipitation"] = "--"   # データ側で 0.0 に変換されているべき値
    with pytest.raises(SchemaError, match="precipitation"):
        validate_weather(bad)


def test_validate_weather_sorts_by_station_and_time(weather_raw):
    shuffled = weather_raw.sample(frac=1, random_state=0)
    df = validate_weather(shuffled)
    assert df["station"].tolist()[:6] == ["福岡"] * 6
    assert df["datetime"].iloc[:6].is_monotonic_increasing


def test_validate_typhoon(fixtures_dir):
    raw = pd.read_csv(fixtures_dir / "landfall_small.csv", dtype={"typhoon_id": str})
    df = validate_typhoon(raw)
    assert list(TYPHOON_COLUMNS) == [c for c in df.columns if c in TYPHOON_COLUMNS]
    assert df["storm_diameter_nm"].isna().all()
    assert df["typhoon_id"].tolist() == ["202512", "202515", "202515"]
    with pytest.raises(SchemaError, match="lat"):
        validate_typhoon(raw.drop(columns=["lat"]))


def test_validate_weather_coerces_string_to_float64(weather_raw):
    # Test that numeric columns from "string" dtype are coerced to plain float64
    string_weather = weather_raw.astype({"pressure": "string", "temperature": "string"})
    df = validate_weather(string_weather)
    assert df["pressure"].dtype == "float64"
    assert df["temperature"].dtype == "float64"


def test_validate_weather_normalizes_tz_aware_to_naive_jst(weather_raw):
    aware = weather_raw.copy()
    aware["datetime"] = aware["datetime"].astype(str) + "+09:00"
    df = validate_weather(aware)
    assert df["datetime"].dt.tz is None
    assert df["datetime"].iloc[0] == pd.Timestamp("2025-08-21 21:00:00")
