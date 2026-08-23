"""地図タブの Figure（設計書 §3）。OpenStreetMap タイルなのでトークン不要。"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from typhoon_app.config import MAP_CENTER, MAP_ZOOM, Station, Variable


def _fmt_time(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{ts.month}/{ts.day} {ts:%H:%M}"


def station_map(
    stations: dict[str, Station],
    values: pd.DataFrame | None,
    var: Variable | None,
    landfalls: pd.DataFrame,
    track: pd.DataFrame | None = None,
    typhoon_pos: tuple[float, float] | None = None,
    title: str = "",
) -> go.Figure:
    fig = go.Figure()

    # 1) 台風経路（あれば）
    if track is not None and not track.empty:
        fig.add_trace(go.Scattermap(
            lat=track["lat"], lon=track["lon"], mode="lines+markers", name="台風経路",
            line=dict(color="gray", width=2), marker=dict(size=6, color="gray"),
            hovertext=[_fmt_time(t) for t in track["datetime"]], hoverinfo="text",
        ))

    # 2) 上陸/接近地点
    if landfalls is not None and not landfalls.empty:
        fig.add_trace(go.Scattermap(
            lat=landfalls["lat"], lon=landfalls["lon"], mode="markers", name="上陸/接近地点",
            marker=dict(size=12, color="red"),
            hovertext=[f"上陸/接近 {_fmt_time(t)}" for t in landfalls["datetime"]], hoverinfo="text",
        ))

    # 3) 観測地点（値があれば色分け、無ければ灰色）
    names = list(stations)
    value_map: dict[str, float] = {}
    if values is not None and var is not None and not values.empty:
        value_map = {str(s): float(v) for s, v in zip(values["station"], values["value"]) if not pd.isna(v)}
    colored = [n for n in names if n in value_map]
    grey = [n for n in names if n not in value_map]

    if colored:
        marker = dict(size=16, color=[value_map[n] for n in colored], colorscale="Viridis", showscale=True)
        if var is not None:
            marker["colorbar"] = dict(title=f"{var.label}（{var.unit}）")
        unit = var.unit if var is not None else ""
        fig.add_trace(go.Scattermap(
            lat=[stations[n].lat for n in colored], lon=[stations[n].lon for n in colored],
            mode="markers+text", name="観測地点", text=colored, textposition="top right",
            marker=marker,
            hovertext=[f"{n}: {value_map[n]:.1f} {unit}" for n in colored], hoverinfo="text",
        ))
    if grey:
        fig.add_trace(go.Scattermap(
            lat=[stations[n].lat for n in grey], lon=[stations[n].lon for n in grey],
            mode="markers+text", name="観測地点" if not colored else "観測地点（欠測）",
            text=grey, textposition="top right",
            marker=dict(size=14, color="lightgray"),
            hovertext=[f"{n}: データなし" for n in grey], hoverinfo="text",
        ))

    # 4) 台風中心（この時刻の位置）
    if typhoon_pos is not None and not any(math.isnan(v) for v in typhoon_pos):
        fig.add_trace(go.Scattermap(
            lat=[typhoon_pos[0]], lon=[typhoon_pos[1]], mode="markers", name="台風中心",
            marker=dict(size=22, color="orange", opacity=0.8), hovertext=["台風中心"], hoverinfo="text",
        ))

    fig.update_layout(
        title=title,
        map=dict(style="open-street-map", center=dict(lat=MAP_CENTER[0], lon=MAP_CENTER[1]), zoom=MAP_ZOOM),
        margin=dict(l=0, r=0, t=40, b=0),
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.7)"),
    )
    return fig
