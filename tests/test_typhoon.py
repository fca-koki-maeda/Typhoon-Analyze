from datetime import date

import pandas as pd
import pytest

from typhoon_app.data.typhoon import get_event, list_typhoons, load_landfall, load_track


def test_load_landfall_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_landfall(tmp_path / "landfall.csv")


def test_load_track_missing_file_is_none(tmp_path):
    assert load_track(tmp_path / "track.csv") is None


def test_list_typhoons_sorted_newest_first(landfall_df):
    events = list_typhoons(landfall_df)
    assert [e.typhoon_id for e in events] == ["202515", "202512"]


def test_event_properties_and_windows(landfall_df):
    e = get_event("202515", landfall_df)
    assert (e.year, e.number) == (2025, 15)
    assert e.label == "2025年 第15号（9/5 接近）"
    assert e.reference_times == [pd.Timestamp("2025-09-05 01:00"), pd.Timestamp("2025-09-05 16:00")]
    assert e.fetch_window() == (date(2025, 8, 29), date(2025, 9, 12))
    assert e.display_window(3) == (pd.Timestamp("2025-09-02 01:00"), pd.Timestamp("2025-09-08 16:00"))
    assert e.center_pressure == 992.0
    assert e.max_wind_kt == 45.0
    assert (e.landfall_lat, e.landfall_lon) == (33.0, 132.4)


def test_get_event_unknown_id(landfall_df):
    with pytest.raises(KeyError):
        get_event("199999", landfall_df)


def test_track_is_attached_per_typhoon(landfall_df, track_df):
    with_track = get_event("202512", landfall_df, track_df)
    assert len(with_track.track) == 4
    without = get_event("202515", landfall_df, track_df)
    assert without.track is None
