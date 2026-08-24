"""地図タブの Figure（設計書 §3）。OpenStreetMap タイルなのでトークン不要。"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from typhoon_app.config import MAP_CENTER, MAP_ZOOM, Station, Variable


def _fmt_time(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{ts.month}/{ts.day} {ts:%H:%M}"


_MIN_ZOOM, _MAX_ZOOM = 3.2, 9.0


def _fit_view(stations: dict[str, Station]) -> tuple[dict, float]:
    """選択地点が収まる center と zoom を返す。地点が無ければ既定値。"""
    if not stations:
        return dict(lat=MAP_CENTER[0], lon=MAP_CENTER[1]), float(MAP_ZOOM)
    lats = [s.lat for s in stations.values()]
    lons = [s.lon for s in stations.values()]
    center = dict(lat=(min(lats) + max(lats)) / 2, lon=(min(lons) + max(lons)) / 2)
    span = max(
        max(lats) - min(lats),
        (max(lons) - min(lons)) * math.cos(math.radians(center["lat"])),
        0.5,  # 1 地点でも寄りすぎない下限
    )
    zoom = math.log2(360.0 / span) - 1.3
    return center, max(_MIN_ZOOM, min(_MAX_ZOOM, zoom))


def station_map(
    stations: dict[str, Station],
    values: pd.DataFrame | None,
    var: Variable | None,
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

    # 2) 観測地点（値があれば色分け、無ければ灰色）
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

    # 3) 台風中心（この時刻の位置）
    if typhoon_pos is not None and not any(math.isnan(v) for v in typhoon_pos):
        fig.add_trace(go.Scattermap(
            lat=[typhoon_pos[0]], lon=[typhoon_pos[1]], mode="markers", name="台風中心",
            marker=dict(size=22, color="orange", opacity=0.8), hovertext=["台風中心"], hoverinfo="text",
        ))

    center, zoom = _fit_view(stations)
    fig.update_layout(
        title=title,
        map=dict(style="open-street-map", center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=40, b=0),
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.7)"),
    )
    return fig
