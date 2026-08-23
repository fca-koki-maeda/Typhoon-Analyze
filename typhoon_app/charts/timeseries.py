"""要素ごとの時系列グラフ（設計書 §3 時系列タブ）。"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from typhoon_app.charts.common import empty_figure
from typhoon_app.config import Variable


def variable_chart(
    df: pd.DataFrame,
    var: Variable,
    reference_times: Iterable = (),
    station_order: Sequence[str] | None = None,
) -> go.Figure:
    """1 要素ぶんのグラフ。地点で色分け。降水は棒、他は折れ線（欠測は線を切る）。
    reference_times の時刻に赤い破線を引く。"""
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

    for t in reference_times:
        fig.add_shape(type="line", x0=t, x1=t, y0=0, y1=1, yref="paper", line=dict(color="red", dash="dash"))
        fig.add_annotation(x=t, y=1, yref="paper", text="上陸/接近", showarrow=False, yanchor="bottom", font=dict(color="red", size=11))

    fig.update_layout(
        title=title,
        xaxis_title="日時",
        yaxis_title=f"{var.label}（{var.unit}）",
        legend_title="地点",
        hovermode="x unified",
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig
