import pandas as pd

from typhoon_app.analysis.summary import summarize
from typhoon_app.charts.ranking import ranking_chart
from typhoon_app.charts.timeseries import variable_chart
from typhoon_app.config import VARIABLES
from typhoon_app.data.schema import WEATHER_COLUMNS


def test_variable_chart_line_one_trace_per_station_and_vlines(weather_df):
    fig = variable_chart(weather_df, VARIABLES["pressure"], [pd.Timestamp("2025-08-21 17:00")], ["鹿児島", "福岡"])
    assert len(fig.data) == 2
    assert fig.data[0].type == "scatter"
    assert fig.data[0].name == "鹿児島"        # station_order が効く
    assert len(fig.layout.shapes) == 1
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
