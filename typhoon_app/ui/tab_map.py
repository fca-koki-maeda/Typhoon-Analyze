"""地図タブ: 時刻スライダー＋地点マーカー＋台風位置（設計書 §3）。"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from typhoon_app.analysis.timeseries import time_steps, values_at
from typhoon_app.analysis.track import typhoon_position
from typhoon_app.charts.map import station_map
from typhoon_app.config import VARIABLES, Station
from typhoon_app.data.typhoon import TyphoonEvent


def _fmt(t: pd.Timestamp) -> str:
    return f"{t.month}/{t.day} {t:%H:%M}"


def render_map(
    df: pd.DataFrame,
    stations: dict[str, Station],
    event: TyphoonEvent,
    variables: Sequence[str],
    window: tuple[pd.Timestamp, pd.Timestamp],
) -> None:
    steps = list(time_steps(*window))
    if not steps:
        st.info("表示できる時刻がありません。")
        return
    default = min(steps, key=lambda t: abs(t - event.first_time))
    t = st.select_slider("時刻", options=steps, value=default, format_func=_fmt)

    var_key = None
    if variables:
        var_key = st.radio(
            "マーカーの色にする要素", options=list(variables), horizontal=True, format_func=lambda k: VARIABLES[k].label
        )
    values = values_at(df, var_key, t) if (var_key and not df.empty) else None
    var = VARIABLES[var_key] if var_key else None

    fig = station_map(
        stations, values, var, event.landfalls, event.track, typhoon_position(event, t), title=f"{_fmt(t)} の状況"
    )
    st.plotly_chart(fig, width="stretch")
    if event.track is None:
        st.caption("全経路データが無いため、台風は上陸/接近地点のみ表示しています。")
