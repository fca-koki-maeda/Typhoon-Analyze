import pandas as pd
import pytest

from typhoon_app.analysis.timeseries import clip, time_steps, values_at
from typhoon_app.analysis.track import position_at, typhoon_position
from typhoon_app.data.typhoon import get_event


def test_clip_is_inclusive(weather_df):
    out = clip(weather_df, pd.Timestamp("2025-08-21 22:00"), pd.Timestamp("2025-08-22 00:00"))
    assert len(out) == 6
    assert out["datetime"].min() == pd.Timestamp("2025-08-21 22:00")
    assert out["datetime"].max() == pd.Timestamp("2025-08-22 00:00")


def test_time_steps_hourly_within_bounds():
    steps = time_steps(pd.Timestamp("2025-08-21 21:30"), pd.Timestamp("2025-08-22 02:10"))
    assert steps[0] == pd.Timestamp("2025-08-21 22:00")
    assert steps[-1] == pd.Timestamp("2025-08-22 02:00")
    assert len(steps) == 5


def test_values_at_returns_station_value_pairs(weather_df):
    v = values_at(weather_df, "pressure", pd.Timestamp("2025-08-21 23:00"))
    assert dict(zip(v["station"], v["value"])) == {"福岡": 995.0, "鹿児島": 980.0}


def test_values_at_unknown_time_is_empty(weather_df):
    assert values_at(weather_df, "pressure", pd.Timestamp("2025-08-25 00:00")).empty


def test_position_at_interpolates_between_points(track_df):
    assert position_at(track_df, pd.Timestamp("2025-08-21 18:00")) == pytest.approx((31.8, 130.5))
    assert position_at(track_df, pd.Timestamp("2025-08-21 09:00")) == pytest.approx((30.0, 129.5))


def test_position_at_outside_range_is_none(track_df):
    assert position_at(track_df, pd.Timestamp("2025-08-23 00:00")) is None
    assert position_at(None, pd.Timestamp("2025-08-21 18:00")) is None


def test_typhoon_position_prefers_track(landfall_df, track_df):
    e = get_event("202512", landfall_df, track_df)
    assert typhoon_position(e, pd.Timestamp("2025-08-21 18:00")) == pytest.approx((31.8, 130.5))


def test_typhoon_position_falls_back_to_landfall_within_6h(landfall_df):
    e = get_event("202512", landfall_df)   # track なし
    assert typhoon_position(e, pd.Timestamp("2025-08-21 18:00")) == pytest.approx((31.6, 130.3))
    assert typhoon_position(e, pd.Timestamp("2025-08-23 00:00")) is None
