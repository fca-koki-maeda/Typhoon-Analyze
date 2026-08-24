"""台風ヘッダ（設計書 §3）。"""
from __future__ import annotations

import math

import streamlit as st

from typhoon_app.data.typhoon import TyphoonEvent


def _fmt(v: float, unit: str, digits: int = 0) -> str:
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{digits}f} {unit}"


def render_header(event: TyphoonEvent) -> None:
    st.title(f"🌀 台風 第{event.number}号（{event.year}年）")
    f, l = event.period
    c1, c2, c3 = st.columns(3)
    c1.metric("対象期間", f"{f.month}/{f.day} {f:%H:%M} 〜 {l.month}/{l.day} {l:%H:%M}")
    c1.caption("台風データが存在する期間（前後1日を表示します）")
    c2.metric("中心気圧（期間中最低）", _fmt(event.center_pressure, "hPa"))
    c3.metric("最大風速（期間中最大）", _fmt(event.max_wind_kt, "kt"))
