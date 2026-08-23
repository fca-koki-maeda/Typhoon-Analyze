"""概要タブ: 地点別サマリ表とランキング（設計書 §3 / §6）。"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from typhoon_app.charts.ranking import ranking_chart

# 要素 → サマリ表に出す列
_COLUMNS_BY_VARIABLE = {
    "pressure": ["min_pressure", "min_pressure_time"],
    "wind_speed": ["max_wind_speed", "max_wind_speed_time", "max_wind_direction"],
    "precipitation": ["total_precipitation", "max_precipitation", "max_precipitation_time"],
    "temperature": ["max_temperature", "min_temperature"],
}
_LABELS = {
    "station": "地点",
    "min_pressure": "最低気圧 (hPa)", "min_pressure_time": "最低気圧の時刻",
    "max_wind_speed": "最大風速 (m/s)", "max_wind_speed_time": "最大風速の時刻", "max_wind_direction": "そのときの風向",
    "total_precipitation": "総降水量 (mm)", "max_precipitation": "最大1時間降水量 (mm)", "max_precipitation_time": "その時刻",
    "max_temperature": "最高気温 (℃)", "min_temperature": "最低気温 (℃)",
    "missing_rate": "欠測率 (%)",
}
# 要素 → ランキング (列, タイトル, 単位, 昇順か)
_RANKINGS = {
    "pressure": ("min_pressure", "最低気圧", "hPa", True),
    "wind_speed": ("max_wind_speed", "最大風速", "m/s", False),
    "precipitation": ("total_precipitation", "総降水量", "mm", False),
    "temperature": ("max_temperature", "最高気温", "℃", False),
}


def _fmt_time(v) -> str:
    if pd.isna(v):
        return "—"
    t = pd.Timestamp(v)
    return f"{t.month}/{t.day} {t:%H:%M}"


def render_overview(summary: pd.DataFrame, variables: Sequence[str]) -> None:
    if summary.empty:
        st.info("表示できるデータがありません。")
        return
    cols = ["station"] + [c for v in variables for c in _COLUMNS_BY_VARIABLE.get(v, [])] + ["missing_rate"]
    table = summary[cols].copy()
    for c in [c for c in cols if c.endswith("_time")]:
        table[c] = table[c].map(_fmt_time)
    table = table.rename(columns=_LABELS)

    st.subheader("地点別サマリ")
    st.dataframe(table, hide_index=True, width="stretch")

    items = [(v, *_RANKINGS[v]) for v in variables if v in _RANKINGS]
    if items:
        st.subheader("ランキング")
        for col, (_, column, title, unit, asc) in zip(st.columns(len(items)), items):
            col.plotly_chart(ranking_chart(summary, column, title, unit, ascending=asc), width="stretch")
