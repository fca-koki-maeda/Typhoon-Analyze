import numpy as np
import pandas as pd
import pytest

from typhoon_app.analysis.summary import SUMMARY_COLUMNS, summarize
from typhoon_app.data.schema import WEATHER_COLUMNS


def test_summarize_fukuoka(weather_df):
    s = summarize(weather_df).set_index("station")
    f = s.loc["福岡"]
    assert f["min_pressure"] == 995.0
    assert f["min_pressure_time"] == pd.Timestamp("2025-08-21 23:00")
    assert f["max_wind_speed"] == 6.0
    assert f["max_wind_speed_time"] == pd.Timestamp("2025-08-21 23:00")
    assert f["max_wind_direction"] == "南東"
    assert f["total_precipitation"] == pytest.approx(3.5)
    assert f["max_precipitation"] == 2.0
    assert f["max_precipitation_time"] == pd.Timestamp("2025-08-21 23:00")
    assert f["max_temperature"] == 28.0
    assert f["min_temperature"] == 26.0
    assert f["missing_rate"] == pytest.approx(100 / 24)   # 気温 1 セル欠測 / 4 要素 × 6 時刻


def test_summarize_kagoshima_with_missing(weather_df):
    k = summarize(weather_df).set_index("station").loc["鹿児島"]
    assert k["min_pressure"] == 980.0
    assert k["max_wind_speed"] == 20.0
    assert k["max_wind_speed_time"] == pd.Timestamp("2025-08-22 00:00")
    assert k["max_wind_direction"] == "南東"
    assert k["total_precipitation"] == pytest.approx(44.5)
    assert k["max_precipitation"] == 20.5
    assert k["missing_rate"] == pytest.approx(200 / 24)   # 降水 1 + 風速 1


def test_summarize_columns_and_order(weather_df):
    s = summarize(weather_df)
    assert list(s.columns) == SUMMARY_COLUMNS
    assert s["station"].tolist() == ["福岡", "鹿児島"]


def test_summarize_empty_input():
    s = summarize(pd.DataFrame(columns=list(WEATHER_COLUMNS)))
    assert s.empty and list(s.columns) == SUMMARY_COLUMNS


def test_summarize_all_missing_variable(weather_df):
    df = weather_df.assign(pressure=np.nan, wind_speed=np.nan)
    s = summarize(df).set_index("station")
    assert pd.isna(s.loc["福岡", "min_pressure"])
    assert pd.isna(s.loc["福岡", "min_pressure_time"])
    assert s.loc["福岡", "max_wind_direction"] is None
