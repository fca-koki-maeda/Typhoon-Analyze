"""台風ヘッダ（設計書 §3）。"""
from __future__ import annotations

import math

import streamlit as st

from typhoon_app.data.typhoon import TyphoonEvent


def _fmt(v: float, unit: str, digits: int = 0) -> str:
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{digits}f} {unit}"


def render_header(event: TyphoonEvent, nearest_name: str) -> None:
    st.title(f"🌀 台風 第{event.number}号（{event.year}年）")
    times = [f"{t.month}/{t.day} {t:%H:%M}" for t in event.reference_times]
    headline = times[0] if len(times) == 1 else f"{times[0]} 〜 {times[-1]}"
    c1, c2, c3 = st.columns(3)
    c1.metric("上陸/接近時刻", headline)
    if len(times) > 1:
        c1.caption("記録された時刻: " + "、".join(times))
    c1.caption(f"{nearest_name}付近（北緯 {event.landfall_lat:.1f}°・東経 {event.landfall_lon:.1f}°）")
    c2.metric("中心気圧（接近時）", _fmt(event.center_pressure, "hPa"))
    c3.metric("最大風速（接近時）", _fmt(event.max_wind_kt, "kt"))
