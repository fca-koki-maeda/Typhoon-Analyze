"""サイドバー: 条件の選択とデータ状態の表示（設計書 §3 / §7）。"""
from __future__ import annotations

import streamlit as st

from typhoon_app.config import DEFAULT_VARIABLES, STATION_NAMES, VARIABLES
from typhoon_app.data.typhoon import TyphoonEvent
from typhoon_app.data.weather import StationResult
from typhoon_app.ui.loaders import load_station_weather_cached
from typhoon_app.ui.state import Selection

_STATUS_LABEL = {
    "cached": "● キャッシュ済み",
    "fetched": "● 取得完了",
    "unavailable": "○ 未取得",
    "error": "✕ 取得失敗",
}


def render_sidebar(events: list[TyphoonEvent], station_names: list[str]) -> Selection:
    labels = {e.typhoon_id: e.label for e in events}
    with st.sidebar:
        st.header("表示条件")
        typhoon_id = st.selectbox(
            "台風を選択", options=[e.typhoon_id for e in events], format_func=lambda i: labels[i]
        )
        default = [n for n in STATION_NAMES if n in station_names] or station_names[:8]
        stations = st.multiselect("地点を選択", options=station_names, default=default)
        if len(station_names) > len(default):
            st.caption("全国の気象官署を追加選択できます（既定は九州・沖縄 8 地点）")
        variables = st.multiselect(
            "気象要素",
            options=list(VARIABLES),
            default=list(DEFAULT_VARIABLES),
            format_func=lambda k: VARIABLES[k].label,
        )
    return Selection(typhoon_id, tuple(stations), tuple(variables))


def render_data_status(results: dict[str, StationResult], fetcher_available: bool) -> None:
    with st.sidebar:
        st.divider()
        st.subheader("データ状態")
        if not fetcher_available:
            st.caption("取得関数が見つからないため、キャッシュ専用モードで動作中です")
        for r in results.values():
            st.write(f"{_STATUS_LABEL[r.status]}：{r.station}")
            if r.message:
                st.caption(r.message)
        col1, col2 = st.columns(2)
        if any(r.status == "error" for r in results.values()):
            if col1.button("再試行"):
                load_station_weather_cached.clear()
                st.rerun()
        if col2.button("データを再読込"):
            st.cache_data.clear()
            st.rerun()
