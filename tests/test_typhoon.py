from datetime import date

import pandas as pd
import pytest

from typhoon_app.data.typhoon import get_event, list_typhoons, load_track


def test_load_track_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_track(tmp_path / "track.csv")


def test_list_typhoons_sorted_newest_first(track_df):
    events = list_typhoons(track_df)
    assert [e.typhoon_id for e in events] == ["202515", "202512"]


def test_event_properties_and_windows(track_df):
    e = get_event("202512", track_df)
    assert (e.year, e.number) == (2025, 12)
    assert e.label == "2025年 第12号（8/21〜8/22）"
    assert e.period == (pd.Timestamp("2025-08-21 09:00"), pd.Timestamp("2025-08-22 03:00"))
    assert e.fetch_window() == (date(2025, 8, 20), date(2025, 8, 23))
    assert e.display_window() == (pd.Timestamp("2025-08-20 09:00"), pd.Timestamp("2025-08-23 03:00"))
    assert e.center_pressure == 994.0
    assert e.max_wind_kt == 45.0


def test_event_label_single_day(track_df):
    e = get_event("202515", track_df)
    assert e.label == "2025年 第15号（9/5）"
    assert e.center_pressure == 992.0


def test_get_event_unknown_id(track_df):
    with pytest.raises(KeyError):
        get_event("199999", track_df)
