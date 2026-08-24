"""読込系のメモリキャッシュ（ファイルが永続キャッシュ、こちらは再描画の高速化）。"""
from __future__ import annotations

from datetime import date

import streamlit as st

from typhoon_app.data.source import WeatherFetcher
from typhoon_app.data.station import load_stations
from typhoon_app.data.typhoon import load_track
from typhoon_app.data.weather import StationResult, get_station_weather


@st.cache_data(show_spinner=False)
def load_track_cached():
    return load_track()


@st.cache_data(show_spinner=False)
def load_stations_cached():
    return load_stations()


@st.cache_data(show_spinner=False)
def load_station_weather_cached(
    typhoon_id: str, station: str, fetch_window: tuple[date, date], _fetcher: WeatherFetcher | None
) -> StationResult:
    """地点ごとの取得結果をメモ化する（再描画のたびに再取得しない）。
    _fetcher は先頭アンダースコアでハッシュ対象から除外。失敗結果もメモ化され、「再試行」で明示的にクリアする。"""
    return get_station_weather(typhoon_id, station, fetch_window, _fetcher)
