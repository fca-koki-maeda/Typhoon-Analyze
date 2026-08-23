"""読込系のメモリキャッシュ（ファイルが永続キャッシュ、こちらは再描画の高速化）。"""
from __future__ import annotations

import streamlit as st

from typhoon_app.data.station import load_stations
from typhoon_app.data.typhoon import load_landfall, load_track


@st.cache_data(show_spinner=False)
def load_landfall_cached():
    return load_landfall()


@st.cache_data(show_spinner=False)
def load_track_cached():
    return load_track()


@st.cache_data(show_spinner=False)
def load_stations_cached():
    return load_stations()
