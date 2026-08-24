import pandas as pd

from typhoon_app.analysis.summary import summarize
from typhoon_app.charts.ranking import ranking_chart
from typhoon_app.charts.timeseries import variable_chart
from typhoon_app.config import VARIABLES
from typhoon_app.data.schema import WEATHER_COLUMNS


def test_variable_chart_line_one_trace_per_station_and_period_band(weather_df):
    period = (pd.Timestamp("2025-08-21 17:00"), pd.Timestamp("2025-08-21 23:00"))
    fig = variable_chart(weather_df, VARIABLES["pressure"], period, ["鹿児島", "福岡"])
    assert len(fig.data) == 2
    assert fig.data[0].type == "scatter"
    assert fig.data[0].name == "鹿児島"        # station_order が効く
    assert len(fig.layout.shapes) == 1
    assert fig.layout.shapes[0].type == "rect"
    assert any("台風接近期間" in a.text for a in fig.layout.annotations)
    assert "hPa" in fig.layout.yaxis.title.text


def test_variable_chart_bar_for_precipitation(weather_df):
    fig = variable_chart(weather_df, VARIABLES["precipitation"])
    assert len(fig.data) == 2
    assert fig.data[0].type == "bar"


def test_variable_chart_empty(weather_df):
    fig = variable_chart(pd.DataFrame(columns=list(WEATHER_COLUMNS)), VARIABLES["pressure"])
    assert len(fig.data) == 0
    assert "データなし" in fig.layout.annotations[0].text


def test_ranking_chart_orders_by_value(weather_df):
    s = summarize(weather_df)
    fig = ranking_chart(s, "min_pressure", "最低気圧", "hPa", ascending=True)
    assert list(fig.data[0].y) == ["鹿児島", "福岡"]
    fig2 = ranking_chart(s, "total_precipitation", "総降水量", "mm", ascending=False)
    assert list(fig2.data[0].y) == ["鹿児島", "福岡"]


from pathlib import Path

from typhoon_app.analysis.timeseries import values_at
from typhoon_app.charts.map import station_map
from typhoon_app.data.station import load_stations


def test_station_map_with_values_track_and_position(weather_df, track_df):
    stations = load_stations(Path("/nonexistent/station.csv"))
    values = values_at(weather_df, "pressure", pd.Timestamp("2025-08-21 23:00"))
    track_202512 = track_df[track_df["typhoon_id"] == "202512"]
    fig = station_map(stations, values, VARIABLES["pressure"], track_202512, (31.8, 130.5), title="t")
    names = [tr.name for tr in fig.data]
    assert "台風経路" in names and "台風中心" in names
    assert "観測地点" in names and "観測地点（欠測）" in names   # 福岡・鹿児島以外は値が無い
    assert fig.layout.map.style == "open-street-map"
    assert fig.layout.map.zoom == 5


def test_station_map_without_values_or_track():
    stations = load_stations(Path("/nonexistent/station.csv"))
    fig = station_map(stations, None, None)
    names = [tr.name for tr in fig.data]
    assert "台風経路" not in names and "台風中心" not in names
    assert names == ["観測地点"]
