"""要素ごとの時系列グラフ（設計書 §3 時系列タブ）。"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from typhoon_app.charts.common import empty_figure
from typhoon_app.config import Variable


def variable_chart(
    df: pd.DataFrame,
    var: Variable,
    period: tuple | None = None,
    station_order: Sequence[str] | None = None,
) -> go.Figure:
    """1 要素ぶんのグラフ。地点で色分け。降水は棒、他は折れ線（欠測は線を切る）。
    period があれば台風接近期間を薄い帯で示す。"""
    title = f"{var.label}（{var.unit}）"
    data = df.assign(station=df["station"].astype(str))
    if var.kind == "bar":
        data = data.dropna(subset=[var.key])
    if data.empty:
        return empty_figure(title)

    orders = {"station": list(station_order)} if station_order else None
    if var.kind == "bar":
        fig = px.bar(data, x="datetime", y=var.key, color="station", barmode="group", category_orders=orders)
    else:
        fig = px.line(data, x="datetime", y=var.key, color="station", category_orders=orders)
        fig.update_traces(connectgaps=False)

    if period is not None:
        x0, x1 = period
        fig.add_shape(
            type="rect", x0=x0, x1=x1, y0=0, y1=1, yref="paper",
            fillcolor="rgba(255, 80, 80, 0.08)", line_width=0, layer="below",
        )
        fig.add_annotation(
            x=x0, y=1, yref="paper", text="台風接近期間", showarrow=False,
            xanchor="left", yanchor="bottom", font=dict(color="red", size=11),
        )

    fig.update_layout(
        title=title,
        xaxis_title="日時",
        yaxis_title=f"{var.label}（{var.unit}）",
        legend_title="地点",
        hovermode="x unified",
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig
